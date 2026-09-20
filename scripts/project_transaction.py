#!/usr/bin/env python3
"""Prepare and commit user-approved project changes through one revision protocol."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

from render_project_views import render as render_project_views
from validate_project import validate as validate_project


OPERATION_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DECISIONS = {"accepted", "accepted-with-modification", "rejected", "deferred"}
AUTHORITATIVE_FILES = (
    "state/project.json",
    "state/task-board.json",
    "records/store.json",
    "sources/registry.json",
)
SUPPORT_FILES = (
    "SKILL.md",
    "agents/openai.yaml",
    "framework/version.json",
    "views/project-map.json",
    "index/manifest.json",
)


class TransactionError(ValueError):
    pass


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TransactionError(f"expected JSON object: {path}")
    return value


def encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".transaction-", delete=False) as temporary:
        temporary.write(data)
        temporary_path = Path(temporary.name)
    try:
        temporary_path.replace(path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def transaction_root(skill_root: Path, operation_id: str) -> Path:
    if not OPERATION_RE.fullmatch(operation_id) or len(operation_id) > 80:
        raise TransactionError("operation ID must be <=80 lowercase letters, digits, and single hyphens")
    return skill_root / "work" / "transactions" / operation_id


def prepare(skill_root: Path, operation_id: str) -> dict:
    errors = validate_project(skill_root)
    if errors:
        raise TransactionError(f"live project is invalid: {'; '.join(errors)}")
    root = transaction_root(skill_root, operation_id)
    if root.exists():
        raise TransactionError(f"transaction already exists: {root}")
    candidate = root / "candidate"
    for relative in AUTHORITATIVE_FILES + SUPPORT_FILES:
        source = skill_root / relative
        destination = candidate / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    project = read_json(skill_root / "state" / "project.json")
    plan = {
        "schema": "ltpm-transaction-plan/v1",
        "operation_id": operation_id,
        "project_id": project["project_id"],
        "base_revision": project["revision"],
        "status": "prepared",
        "prepared_at": now(),
        "candidate": "candidate/",
    }
    write_atomic(root / "plan.json", encoded(plan))
    return {"prepared": str(root), "candidate": str(candidate), "base_revision": project["revision"]}


def load_decisions(path: Path) -> list[dict]:
    value = read_json(path)
    decisions = value.get("decisions")
    if not isinstance(decisions, list) or not decisions:
        raise TransactionError("decision ledger must contain a non-empty decisions list")
    change_ids: set[str] = set()
    accepted = 0
    for item in decisions:
        if not isinstance(item, dict):
            raise TransactionError("every decision must be an object")
        missing = {"change_id", "decision", "operation", "target", "reason"} - set(item)
        if missing:
            raise TransactionError(f"decision is missing fields: {', '.join(sorted(missing))}")
        change_id = item.get("change_id")
        if not isinstance(change_id, str) or not change_id or change_id in change_ids:
            raise TransactionError("decision change_id values must be non-empty and unique")
        change_ids.add(change_id)
        if item.get("decision") not in DECISIONS:
            raise TransactionError(f"invalid decision for {change_id}")
        if item["decision"] in {"accepted", "accepted-with-modification"}:
            accepted += 1
    if accepted == 0:
        raise TransactionError("nothing was accepted; formal state must not be committed")
    return decisions


def empty_index(project_id: str, revision: int) -> dict:
    return {
        "schema": "ltpm-index-manifest/v1",
        "project_id": project_id,
        "status": "stale",
        "generated_from_revision": None,
        "generated_at": None,
        "coverage": {
            "authorized_scope": [
                "state/project.json",
                "state/task-board.json",
                "records/store.json",
                "sources/registry.json metadata",
            ],
            "indexed_record_ids": [],
            "indexed_source_ids": [],
            "indexed_paths": [],
            "exclusions": [
                {"scope": "project revision", "reason": f"index not rebuilt for revision {revision}"},
                {"scope": "registered source contents", "reason": "not indexed or authorized"},
                {"scope": "work/", "reason": "pending material is outside formal knowledge"},
            ],
        },
    }


def objective_change_is_authorized(live: dict, candidate: dict, decisions: list[dict]) -> None:
    old = live.get("objective_contract", {})
    new = candidate.get("objective_contract", {})
    if old.get("objective_id") != new.get("objective_id"):
        raise TransactionError("objective_id is stable; create a related node or a new project instead")
    if old == new:
        return
    authorized = any(
        item["decision"] in {"accepted", "accepted-with-modification"}
        and item["operation"] == "revise-objective"
        and item["target"] == "state/project.json#objective_contract"
        for item in decisions
    )
    if not authorized:
        raise TransactionError("objective contract changed without an accepted revise-objective decision")
    if new.get("objective_revision") != old.get("objective_revision", 0) + 1:
        raise TransactionError("an accepted objective revision must increment objective_revision exactly once")


def commit(skill_root: Path, operation_id: str, decisions_path: Path) -> dict:
    root = transaction_root(skill_root, operation_id)
    plan = read_json(root / "plan.json")
    candidate = root / "candidate"
    receipt_path = skill_root / "packages" / "archive" / "receipts" / f"{operation_id}.json"
    if receipt_path.exists():
        raise TransactionError(f"receipt already exists: {receipt_path}")
    decisions = load_decisions(decisions_path)
    live_project = read_json(skill_root / "state" / "project.json")
    candidate_project = read_json(candidate / "state" / "project.json")
    base_revision = plan.get("base_revision")
    if plan.get("project_id") != live_project.get("project_id") or candidate_project.get("project_id") != live_project.get("project_id"):
        raise TransactionError("transaction project_id does not match the live project")
    if live_project.get("revision") != base_revision:
        raise TransactionError("stale transaction: live revision no longer matches base_revision")
    if candidate_project.get("revision") != base_revision:
        raise TransactionError("candidate revision must remain at base_revision until commit")
    objective_change_is_authorized(live_project, candidate_project, decisions)

    render_project_views(candidate)
    candidate_errors = validate_project(candidate)
    if candidate_errors:
        raise TransactionError(f"candidate is invalid: {'; '.join(candidate_errors)}")

    next_revision = base_revision + 1
    candidate_project["revision"] = next_revision
    write_atomic(candidate / "state" / "project.json", encoded(candidate_project))
    for relative in ("state/task-board.json", "records/store.json", "sources/registry.json"):
        value = read_json(candidate / relative)
        value["project_revision"] = next_revision
        write_atomic(candidate / relative, encoded(value))
    write_atomic(candidate / "index" / "manifest.json", encoded(empty_index(live_project["project_id"], next_revision)))
    render_project_views(candidate)
    candidate_errors = validate_project(candidate)
    if candidate_errors:
        raise TransactionError(f"revisioned candidate is invalid: {'; '.join(candidate_errors)}")

    publish_files = AUTHORITATIVE_FILES + ("views/project-map.json", "index/manifest.json")
    new_bytes = {relative: (candidate / relative).read_bytes() for relative in publish_files}
    old_bytes = {relative: (skill_root / relative).read_bytes() for relative in publish_files}
    receipt = {
        "schema": "ltpm-transaction-receipt/v1",
        "operation_id": operation_id,
        "project_id": live_project["project_id"],
        "base_revision": base_revision,
        "new_revision": next_revision,
        "committed_at": now(),
        "decisions": decisions,
        "files": [
            {"path": relative, "sha256": sha256(new_bytes[relative])}
            for relative in publish_files
        ],
        "validation": "passed",
    }
    try:
        for relative in publish_files:
            write_atomic(skill_root / relative, new_bytes[relative])
        live_errors = validate_project(skill_root)
        if live_errors:
            raise TransactionError(f"published project failed validation: {'; '.join(live_errors)}")
        write_atomic(receipt_path, encoded(receipt))
    except Exception:
        for relative in publish_files:
            write_atomic(skill_root / relative, old_bytes[relative])
        if receipt_path.exists():
            receipt_path.unlink()
        raise
    plan["status"] = "committed"
    plan["new_revision"] = next_revision
    plan["receipt"] = str(receipt_path.relative_to(skill_root))
    write_atomic(root / "plan.json", encoded(plan))
    return {"committed": operation_id, "old_revision": base_revision, "new_revision": next_revision, "receipt": str(receipt_path)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--project-skill", required=True, type=Path)
    prepare_parser.add_argument("--operation-id", required=True)
    commit_parser = subparsers.add_parser("commit")
    commit_parser.add_argument("--project-skill", required=True, type=Path)
    commit_parser.add_argument("--operation-id", required=True)
    commit_parser.add_argument("--decisions", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        skill_root = args.project_skill.expanduser().resolve()
        if args.command == "prepare":
            result = prepare(skill_root, args.operation_id)
        else:
            result = commit(skill_root, args.operation_id, args.decisions.expanduser().resolve())
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

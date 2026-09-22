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

from project_binding import require_binding
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
    "project-instructions.md",
    "framework/instance.json",
    "views/project-map.json",
    "index/manifest.json",
)
CANDIDATE_FILES = AUTHORITATIVE_FILES + (
    "views/project-map.json",
    "index/manifest.json",
)
CLEANUP_PREVIEW_SCHEMA = "ltpm-transaction-cleanup-preview/v1"
CLEANUP_RECEIPT_SCHEMA = "ltpm-transaction-cleanup-receipt/v1"


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


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise TransactionError(f"candidate cleanup refuses symlink: {path.relative_to(root)}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise TransactionError(f"candidate cleanup refuses non-file entry: {path.relative_to(root)}")
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        data = path.read_bytes()
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def transaction_root(skill_root: Path, operation_id: str) -> Path:
    if not OPERATION_RE.fullmatch(operation_id) or len(operation_id) > 80:
        raise TransactionError("operation ID must be <=80 lowercase letters, digits, and single hyphens")
    return skill_root / "work" / "transactions" / operation_id


def prepare(skill_root: Path, operation_id: str) -> dict:
    binding = require_binding(skill_root, write=True)
    errors = validate_project(skill_root)
    if errors:
        raise TransactionError(f"live project is invalid: {'; '.join(errors)}")
    root = transaction_root(skill_root, operation_id)
    if root.exists():
        raise TransactionError(f"transaction already exists: {root}")
    candidate = root / "candidate"
    for relative in CANDIDATE_FILES:
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
    return {
        "prepared": str(root),
        "candidate": str(candidate),
        "project_id": binding["project_id"],
        "base_revision": project["revision"],
    }


def validate_candidate(skill_root: Path, candidate: Path) -> list[str]:
    with tempfile.TemporaryDirectory(prefix="ltpm-transaction-validation-") as temporary_text:
        validation_root = Path(temporary_text) / "candidate"
        for relative in CANDIDATE_FILES:
            source = candidate / relative
            destination = validation_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        for relative in SUPPORT_FILES:
            if relative in CANDIDATE_FILES:
                continue
            source = skill_root / relative
            destination = validation_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        return validate_project(validation_root)


def cleanup_preview(skill_root: Path) -> dict:
    binding = require_binding(skill_root, write=True)
    project = read_json(skill_root / "state" / "project.json")
    transactions = skill_root / "work" / "transactions"
    eligible: list[dict] = []
    excluded: list[dict] = []
    for root in sorted(transactions.iterdir() if transactions.is_dir() else [], key=lambda path: path.name):
        if root.is_symlink() or not root.is_dir() or not OPERATION_RE.fullmatch(root.name):
            excluded.append({"operation_id": root.name, "reason": "unsafe-or-invalid-transaction-root"})
            continue
        candidate = root / "candidate"
        if not candidate.exists():
            continue
        reason: str | None = None
        try:
            plan = read_json(root / "plan.json")
            expected_receipt = Path("packages") / "archive" / "receipts" / f"{root.name}.json"
            if candidate.is_symlink() or not candidate.is_dir():
                reason = "candidate-is-not-a-regular-directory"
            elif plan.get("operation_id") != root.name or plan.get("project_id") != project.get("project_id"):
                reason = "plan-identity-mismatch"
            elif plan.get("status") != "committed":
                reason = "transaction-is-not-committed"
            elif plan.get("receipt") != expected_receipt.as_posix():
                reason = "plan-receipt-path-mismatch"
            else:
                receipt = read_json(skill_root / expected_receipt)
                if (
                    receipt.get("schema") != "ltpm-transaction-receipt/v1"
                    or receipt.get("operation_id") != root.name
                    or receipt.get("project_id") != project.get("project_id")
                    or receipt.get("base_revision") != plan.get("base_revision")
                    or receipt.get("new_revision") != plan.get("new_revision")
                    or receipt.get("validation") != "passed"
                ):
                    reason = "receipt-does-not-prove-committed-candidate"
            if reason is None:
                eligible.append(
                    {
                        "operation_id": root.name,
                        "candidate": candidate.relative_to(skill_root).as_posix(),
                        "candidate_tree_sha256": tree_sha256(candidate),
                        "receipt": expected_receipt.as_posix(),
                    }
                )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            reason = f"invalid-transaction-evidence: {exc}"
        if reason is not None:
            excluded.append({"operation_id": root.name, "reason": reason})
    preview = {
        "schema": CLEANUP_PREVIEW_SCHEMA,
        "project_id": binding["project_id"],
        "project_revision": project["revision"],
        "eligible": eligible,
        "excluded": excluded,
    }
    preview["preview_sha256"] = sha256(canonical(preview))
    return preview


def cleanup_committed(skill_root: Path, approved_preview_sha256: str) -> dict:
    preview = cleanup_preview(skill_root)
    if preview["preview_sha256"] != approved_preview_sha256:
        raise TransactionError("approved cleanup preview does not match current cleanup scope")
    if not preview["eligible"]:
        raise TransactionError("cleanup preview contains no eligible committed candidates")
    receipt_path = (
        skill_root
        / "packages"
        / "archive"
        / "receipts"
        / f"candidate-cleanup-{approved_preview_sha256[:12]}.json"
    )
    if receipt_path.exists():
        raise TransactionError(f"cleanup receipt already exists: {receipt_path}")
    cleaned: list[str] = []
    failed: list[dict[str, str]] = []
    for item in preview["eligible"]:
        candidate = skill_root / item["candidate"]
        try:
            shutil.rmtree(candidate)
            cleaned.append(item["operation_id"])
        except OSError as exc:
            failed.append({"operation_id": item["operation_id"], "error": str(exc)})
            break
    receipt = {
        "schema": CLEANUP_RECEIPT_SCHEMA,
        "project_id": preview["project_id"],
        "project_revision_before": preview["project_revision"],
        "project_revision_after": read_json(skill_root / "state" / "project.json")["revision"],
        "preview_sha256": approved_preview_sha256,
        "cleaned_operations": cleaned,
        "failed": failed,
        "created_at": now(),
        "validation": "passed" if not failed else "partial",
    }
    write_atomic(receipt_path, encoded(receipt))
    if failed:
        raise TransactionError(f"candidate cleanup was partial; see receipt: {receipt_path}")
    return {
        "cleanup": "completed",
        "project_id": preview["project_id"],
        "project_revision": preview["project_revision"],
        "cleaned_operations": cleaned,
        "receipt": str(receipt_path),
    }


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
    binding = require_binding(skill_root, write=True)
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
    candidate_errors = validate_candidate(skill_root, candidate)
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
    candidate_errors = validate_candidate(skill_root, candidate)
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
    try:
        shutil.rmtree(candidate)
        candidate_cleanup = "removed"
    except OSError:
        candidate_cleanup = "retained-nondiscoverable"
    return {
        "committed": operation_id,
        "project_id": binding["project_id"],
        "old_revision": base_revision,
        "new_revision": next_revision,
        "receipt": str(receipt_path),
        "candidate_cleanup": candidate_cleanup,
    }


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
    cleanup_preview_parser = subparsers.add_parser("cleanup-preview")
    cleanup_preview_parser.add_argument("--project-skill", required=True, type=Path)
    cleanup_parser = subparsers.add_parser("cleanup-committed")
    cleanup_parser.add_argument("--project-skill", required=True, type=Path)
    cleanup_parser.add_argument("--approved-preview-sha256", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        skill_root = args.project_skill.expanduser().resolve()
        if args.command == "prepare":
            result = prepare(skill_root, args.operation_id)
        elif args.command == "commit":
            result = commit(skill_root, args.operation_id, args.decisions.expanduser().resolve())
        elif args.command == "cleanup-preview":
            result = cleanup_preview(skill_root)
        else:
            result = cleanup_committed(skill_root, args.approved_preview_sha256)
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

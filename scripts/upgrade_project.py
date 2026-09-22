#!/usr/bin/env python3
"""Propose and apply recoverable thin-adapter upgrades for project child skills."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import uuid
from pathlib import Path

from project_binding import framework_info, inspect_project, make_instance, sha256_file
from validate_project import validate as validate_project


PLAN_SCHEMA = "ltpm-project-upgrade-plan/v1"
RECEIPT_SCHEMA = "ltpm-project-upgrade-receipt/v1"
DECISIONS = {"accepted", "rejected", "deferred"}
OPERATION_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PRESERVED_ROOTS = ("state", "records", "sources", "work", "views", "index")


class UpgradeError(ValueError):
    pass


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def load_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise UpgradeError(f"expected JSON object: {path}")
    return value


def encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".upgrade-", delete=False) as temporary:
        temporary.write(data)
        temporary_path = Path(temporary.name)
    try:
        temporary_path.replace(path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def framework_root() -> Path:
    return Path(__file__).resolve().parents[1]


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    paths: list[Path] = []
    for relative in PRESERVED_ROOTS:
        base = root / relative
        if base.is_dir():
            paths.extend(path for path in base.rglob("*") if path.is_file() and not path.is_symlink())
    for path in sorted(paths, key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256_file(path).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def precondition_hashes(root: Path) -> dict[str, str | None]:
    relatives = (
        "SKILL.md",
        "agents/openai.yaml",
        "project-instructions.md",
        "framework/instance.json",
        "framework/version.json",
    )
    return {
        relative: sha256_file(root / relative) if (root / relative).is_file() else None
        for relative in relatives
    }


def render_template(source: Path, replacements: dict[str, str]) -> str:
    text = source.read_text(encoding="utf-8")
    for key, value in replacements.items():
        text = text.replace(f"@@{key}@@", value)
    if "@@" in text:
        raise UpgradeError(f"unresolved template token in {source}")
    return text


def replacements(root: Path, project: dict) -> dict[str, str]:
    name_match = re.search(
        r"^name: ([a-z0-9]+(?:-[a-z0-9]+)*)$",
        (root / "SKILL.md").read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    child_name = name_match.group(1) if name_match else root.name
    project_name = project["project_name"]
    return {
        "SKILL_NAME": child_name,
        "PROJECT_NAME_HEADING": project_name,
        "PROJECT_NAME_JSON": json.dumps(project_name, ensure_ascii=False),
        "DESCRIPTION_JSON": json.dumps(
            f'Manage the long-running project "{project_name}" through explicit maintainer, explorer, and integration sessions. Invoke explicitly for this project only.',
            ensure_ascii=False,
        ),
        "DEFAULT_PROMPT_JSON": json.dumps(
            f"Use ${child_name} to continue this managed project.", ensure_ascii=False
        ),
        "PROJECT_ID": project["project_id"],
        "GENERATED_AT": now(),
    }


def proposal(root: Path) -> dict:
    binding = inspect_project(root)
    if binding["status"] == "compatible":
        raise UpgradeError("child is already compatible; no adapter upgrade is required")
    if binding["status"] == "migration-required":
        raise UpgradeError("project-data migration is required and must be proposed separately")
    if binding["status"] != "upgrade-required":
        raise UpgradeError(f"child cannot be upgraded safely from status {binding['status']}")
    legacy = not (root / "framework" / "instance.json").is_file()
    validation_errors = validate_project(
        root,
        allow_legacy=legacy,
        allow_managed_mismatch=not legacy,
    )
    if validation_errors:
        raise UpgradeError(f"project fails read-only validation: {'; '.join(validation_errors)}")
    project = load_object(root / "state" / "project.json")
    changes = [
        {
            "change_id": "replace-thin-entry",
            "required": True,
            "operation": "replace-framework-managed-adapter",
            "targets": ["SKILL.md"],
            "reason": "delegate shared protocols to the compatible installed total skill",
        },
        {
            "change_id": "write-instance-contract",
            "required": True,
            "operation": "write-project-instance-contract",
            "targets": ["framework/instance.json", "framework/version.json"],
            "reason": "record immutable identity, protocol compatibility, schemas, ownership, and managed hashes",
        },
    ]
    if not (root / "project-instructions.md").is_file():
        changes.append(
            {
                "change_id": "create-project-instructions",
                "required": True,
                "operation": "create-user-owned-file",
                "targets": ["project-instructions.md"],
                "reason": "separate project-specific instructions from framework-managed adapter files",
            }
        )
    if (root / "framework" / "conditional").is_dir():
        changes.append(
            {
                "change_id": "archive-legacy-conditionals",
                "required": False,
                "operation": "archive-framework-copy",
                "targets": ["framework/conditional/"],
                "reason": "shared protocols now live in the total skill; retain a recoverable archive before removal",
            }
        )
    return {
        "schema": PLAN_SCHEMA,
        "plan_id": f"upgrade-{uuid.uuid4()}",
        "created_at": now(),
        "project_skill_root": str(root),
        "project_id": project["project_id"],
        "base_revision": project["revision"],
        "source_status": binding["status"],
        "source_framework_version": binding.get("legacy_framework_version")
        or binding.get("instance", {}).get("last_adapter_update_with"),
        "target_framework_version": framework_info()["framework_version"],
        "precondition_hashes": precondition_hashes(root),
        "preserved_project_digest": tree_digest(root),
        "changes": changes,
        "data_migration": {
            "required": False,
            "reason": "v0.5.0 retains the v0.4.0 project-data schemas",
        },
    }


def load_decisions(path: Path, plan: dict) -> dict[str, str]:
    value = load_object(path)
    items = value.get("decisions")
    if not isinstance(items, list):
        raise UpgradeError("upgrade decisions must contain a decisions list")
    decisions: dict[str, str] = {}
    for item in items:
        if not isinstance(item, dict):
            raise UpgradeError("each upgrade decision must be an object")
        change_id = item.get("change_id")
        decision = item.get("decision")
        if not isinstance(change_id, str) or change_id in decisions:
            raise UpgradeError("upgrade decision change_id values must be unique strings")
        if decision not in DECISIONS:
            raise UpgradeError(f"unsupported upgrade decision for {change_id}")
        decisions[change_id] = decision
    planned = {item["change_id"]: item for item in plan["changes"]}
    unknown = set(decisions) - set(planned)
    if unknown:
        raise UpgradeError(f"decisions reference unknown changes: {', '.join(sorted(unknown))}")
    missing = set(planned) - set(decisions)
    if missing:
        raise UpgradeError(f"every proposed change needs a decision: {', '.join(sorted(missing))}")
    rejected_required = [
        change_id
        for change_id, item in planned.items()
        if item["required"] and decisions[change_id] != "accepted"
    ]
    if rejected_required:
        raise UpgradeError(
            f"required adapter changes were not accepted: {', '.join(sorted(rejected_required))}"
        )
    return decisions


def copy_backup(candidate: Path, relative: str, backup_root: Path) -> None:
    source = candidate / relative
    if not source.exists():
        return
    destination = backup_root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, destination)
    else:
        shutil.copy2(source, destination)


def apply_upgrade(root: Path, plan_path: Path, decisions_path: Path, operation_id: str) -> dict:
    if not OPERATION_RE.fullmatch(operation_id) or len(operation_id) > 80:
        raise UpgradeError("operation ID must be <=80 lowercase letters, digits, and single hyphens")
    plan = load_object(plan_path)
    if plan.get("schema") != PLAN_SCHEMA:
        raise UpgradeError("unsupported upgrade plan schema")
    resolved_root = root.expanduser().resolve()
    if Path(plan.get("project_skill_root", "")).resolve() != resolved_root:
        raise UpgradeError("upgrade plan targets a different project-skill root")
    project = load_object(resolved_root / "state" / "project.json")
    if project.get("project_id") != plan.get("project_id") or project.get("revision") != plan.get("base_revision"):
        raise UpgradeError("upgrade plan project identity or base revision is stale")
    if precondition_hashes(resolved_root) != plan.get("precondition_hashes"):
        raise UpgradeError("framework adapter files changed after the upgrade proposal")
    if tree_digest(resolved_root) != plan.get("preserved_project_digest"):
        raise UpgradeError("project-owned data changed after the upgrade proposal")
    decisions = load_decisions(decisions_path, plan)
    target_framework_version = framework_info()["framework_version"]
    if plan.get("target_framework_version") != target_framework_version:
        raise UpgradeError("installed framework changed after the upgrade proposal; create a new proposal")

    receipt_relative = Path("packages") / "archive" / "receipts" / f"{operation_id}-framework-upgrade.json"
    if (resolved_root / receipt_relative).exists():
        raise UpgradeError(f"upgrade receipt already exists: {receipt_relative}")

    with tempfile.TemporaryDirectory(prefix=".ltpm-upgrade-", dir=resolved_root.parent) as temporary:
        temporary_root = Path(temporary)
        candidate = temporary_root / "candidate"
        shutil.copytree(resolved_root, candidate)
        archive_root = (
            candidate
            / "packages"
            / "archive"
            / "framework-upgrades"
            / operation_id
            / "previous-adapter"
        )
        for relative in ("SKILL.md", "agents/openai.yaml", "framework/version.json", "framework/instance.json"):
            copy_backup(candidate, relative, archive_root)

        project = load_object(candidate / "state" / "project.json")
        values = replacements(candidate, project)
        template_root = framework_root() / "assets" / "project-skill-template"
        write_atomic(
            candidate / "SKILL.md",
            render_template(template_root / "SKILL.md.tmpl", values).encode("utf-8"),
        )
        if decisions.get("create-project-instructions") == "accepted":
            write_atomic(
                candidate / "project-instructions.md",
                render_template(template_root / "project-instructions.md.tmpl", values).encode("utf-8"),
            )
        if decisions.get("archive-legacy-conditionals") == "accepted":
            copy_backup(candidate, "framework/conditional", archive_root)
            shutil.rmtree(candidate / "framework" / "conditional")
        legacy_version_path = candidate / "framework" / "version.json"
        legacy_version = load_object(legacy_version_path) if legacy_version_path.is_file() else None
        if legacy_version_path.exists():
            legacy_version_path.unlink()

        child_name = values["SKILL_NAME"]
        existing_instance = (
            load_object(candidate / "framework" / "instance.json")
            if (candidate / "framework" / "instance.json").is_file()
            else {}
        )
        created_at = (legacy_version or {}).get("generated_at") or existing_instance.get("created_at") or now()
        created_with = (
            (legacy_version or {}).get("framework_version")
            or plan.get("source_framework_version")
            or target_framework_version
        )
        instance = make_instance(
            candidate,
            project["project_id"],
            child_name,
            target_framework_version,
            created_at,
        )
        instance["created_with"] = created_with
        instance["last_adapter_update_with"] = target_framework_version
        write_atomic(candidate / "framework" / "instance.json", encoded(instance))

        if tree_digest(candidate) != plan["preserved_project_digest"]:
            raise UpgradeError("candidate changed project-owned data")
        candidate_errors = validate_project(candidate)
        if candidate_errors:
            raise UpgradeError(f"upgraded candidate is invalid: {'; '.join(candidate_errors)}")

        receipt = {
            "schema": RECEIPT_SCHEMA,
            "operation_id": operation_id,
            "plan_id": plan["plan_id"],
            "project_id": project["project_id"],
            "project_revision": project["revision"],
            "source_framework_version": plan.get("source_framework_version"),
            "target_framework_version": target_framework_version,
            "committed_at": now(),
            "decisions": [
                {"change_id": item["change_id"], "decision": decisions[item["change_id"]]}
                for item in plan["changes"]
            ],
            "project_data_migrated": False,
            "project_revision_changed": False,
            "preserved_project_digest": plan["preserved_project_digest"],
            "adapter_hashes": precondition_hashes(candidate),
            "validation": "passed",
        }
        write_atomic(candidate / receipt_relative, encoded(receipt))

        live_backup = resolved_root.parent / f".{resolved_root.name}.pre-upgrade-{uuid.uuid4().hex}"
        try:
            os.replace(resolved_root, live_backup)
            os.replace(candidate, resolved_root)
            live_errors = validate_project(resolved_root)
            live_binding = inspect_project(resolved_root)
            if live_errors or live_binding["status"] != "compatible":
                detail = "; ".join(live_errors + live_binding.get("issues", []))
                raise UpgradeError(f"published upgrade failed validation: {detail}")
        except Exception:
            failed = resolved_root.parent / f".{resolved_root.name}.failed-upgrade-{uuid.uuid4().hex}"
            if resolved_root.exists():
                os.replace(resolved_root, failed)
            if live_backup.exists():
                os.replace(live_backup, resolved_root)
            if failed.exists():
                shutil.rmtree(failed)
            raise
        else:
            shutil.rmtree(live_backup)

    return {
        "upgraded": str(resolved_root),
        "project_id": project["project_id"],
        "project_revision": project["revision"],
        "framework_version": target_framework_version,
        "receipt": str(resolved_root / receipt_relative),
        "project_data_migrated": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("inspect", "verify"):
        item = subparsers.add_parser(command)
        item.add_argument("--project-skill", required=True, type=Path)
    propose = subparsers.add_parser("propose")
    propose.add_argument("--project-skill", required=True, type=Path)
    propose.add_argument("--output", required=True, type=Path)
    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("--project-skill", required=True, type=Path)
    apply_parser.add_argument("--plan", required=True, type=Path)
    apply_parser.add_argument("--decisions", required=True, type=Path)
    apply_parser.add_argument("--operation-id", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        root = args.project_skill.expanduser().resolve()
        if args.command == "inspect":
            result = inspect_project(root)
        elif args.command == "verify":
            errors = validate_project(root)
            binding = inspect_project(root)
            if errors or binding["status"] != "compatible":
                raise UpgradeError("; ".join(errors + binding.get("issues", [])))
            result = {"verified": str(root), "binding": binding}
        elif args.command == "propose":
            output = args.output.expanduser().resolve()
            if output.exists():
                raise UpgradeError(f"output already exists: {output}")
            plan = proposal(root)
            write_atomic(output, encoded(plan))
            result = {"proposal": str(output), **plan}
        else:
            result = apply_upgrade(
                root,
                args.plan.expanduser().resolve(),
                args.decisions.expanduser().resolve(),
                args.operation_id,
            )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

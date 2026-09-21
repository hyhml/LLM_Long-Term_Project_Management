#!/usr/bin/env python3
"""Inspect and enforce one-project bindings for project-local child skills."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


INSTANCE_SCHEMA = "ltpm-project-instance/v1"
MANAGER_SKILL = "long-term-project-manager"
ENTRY_PROTOCOL = 1
CURRENT_DATA_SCHEMAS = {
    "project": "ltpm-project-state/v2",
    "task_board": "ltpm-task-board/v1",
    "record_store": "ltpm-record-store/v2",
    "source_registry": "ltpm-source-registry/v1",
    "project_map": "ltpm-project-map-view/v3",
    "index_manifest": "ltpm-index-manifest/v1",
    "handoff": "llm-long-term-project-handoff/v1",
}
DATA_FILES = {
    "project": "state/project.json",
    "task_board": "state/task-board.json",
    "record_store": "records/store.json",
    "source_registry": "sources/registry.json",
    "project_map": "views/project-map.json",
    "index_manifest": "index/manifest.json",
}
READABLE_STATUSES = {"compatible", "upgrade-required", "migration-required"}


class BindingError(ValueError):
    pass


def load_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise BindingError(f"expected JSON object: {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def framework_root() -> Path:
    return Path(__file__).resolve().parents[1]


def framework_info() -> dict:
    value = load_object(framework_root() / "references" / "framework-map.json")
    compatibility = value.get("compatibility", {})
    protocols = compatibility.get("supported_entry_protocols", [ENTRY_PROTOCOL])
    if not isinstance(protocols, list) or any(not isinstance(item, int) for item in protocols):
        raise BindingError("framework map has invalid supported_entry_protocols")
    return {
        "framework_version": value.get("framework_version"),
        "supported_entry_protocols": protocols,
        "supported_data_schemas": compatibility.get("supported_data_schemas", CURRENT_DATA_SCHEMAS),
    }


def skill_name(skill_root: Path) -> str | None:
    path = skill_root / "SKILL.md"
    if not path.is_file():
        return None
    match = re.search(r"^name: ([a-z0-9]+(?:-[a-z0-9]+)*)$", path.read_text(encoding="utf-8"), re.MULTILINE)
    return match.group(1) if match else None


def managed_hashes(skill_root: Path, managed_files: list[str]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for relative in managed_files:
        path = skill_root / relative
        if not path.is_file() or path.is_symlink():
            raise BindingError(f"managed adapter file is missing or not regular: {relative}")
        hashes[relative] = sha256_file(path)
    return hashes


def make_instance(
    skill_root: Path,
    project_id: str,
    child_skill_name: str,
    framework_version: str,
    created_at: str,
) -> dict:
    managed = ["SKILL.md", "agents/openai.yaml"]
    return {
        "schema": INSTANCE_SCHEMA,
        "project_id": project_id,
        "skill_name": child_skill_name,
        "manager_skill": MANAGER_SKILL,
        "entry_protocol": ENTRY_PROTOCOL,
        "created_with": framework_version,
        "last_adapter_update_with": framework_version,
        "created_at": created_at,
        "data_schemas": CURRENT_DATA_SCHEMAS,
        "ownership": {
            "framework_managed": [*managed, "framework/instance.json"],
            "project_owned": [
                "project-instructions.md",
                "state/",
                "records/",
                "sources/",
                "work/",
                "views/",
                "index/",
                "packages/",
            ],
            "managed_hashes": managed_hashes(skill_root, managed),
        },
    }


def sibling_duplicate_roots(skill_root: Path, project_id: str) -> list[str]:
    duplicates: list[str] = []
    parent = skill_root.parent
    if not parent.is_dir():
        return duplicates
    for sibling in parent.iterdir():
        if sibling == skill_root or sibling.name.startswith(".") or not sibling.is_dir() or sibling.is_symlink():
            continue
        candidates = (sibling / "framework" / "instance.json", sibling / "state" / "project.json")
        for candidate in candidates:
            if not candidate.is_file():
                continue
            try:
                if load_object(candidate).get("project_id") == project_id:
                    duplicates.append(str(sibling.resolve()))
                    break
            except (OSError, ValueError, json.JSONDecodeError):
                continue
    return sorted(duplicates)


def inspect_project(
    skill_root: Path,
    expected_project_id: str | None = None,
    *,
    allow_missing_derived: bool = False,
) -> dict:
    root = skill_root.expanduser().resolve()
    result = {
        "schema": "ltpm-project-binding-result/v1",
        "project_skill_root": str(root),
        "status": "invalid",
        "read_allowed": False,
        "write_allowed": False,
        "issues": [],
    }
    issues: list[str] = result["issues"]
    try:
        project = load_object(root / "state" / "project.json")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        issues.append(str(exc))
        return result

    project_id = project.get("project_id")
    revision = project.get("revision")
    result.update(
        {
            "project_id": project_id,
            "project_name": project.get("project_name"),
            "project_revision": revision,
            "skill_name": skill_name(root),
        }
    )
    if not isinstance(project_id, str) or not project_id:
        issues.append("project_id is missing")
        return result
    if expected_project_id is not None and expected_project_id != project_id:
        issues.append(f"expected project_id {expected_project_id}, found {project_id}")
        return result
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 0:
        issues.append("project revision is invalid")
        return result

    for label, relative in DATA_FILES.items():
        if allow_missing_derived and label == "project_map" and not (root / relative).is_file():
            continue
        try:
            value = load_object(root / relative)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            issues.append(str(exc))
            continue
        if value.get("project_id") != project_id:
            issues.append(f"{label} project_id does not match the bound project")
    if issues:
        return result

    duplicates = sibling_duplicate_roots(root, project_id)
    if duplicates:
        result["status"] = "ambiguous"
        result["duplicate_roots"] = duplicates
        issues.append("the same project_id appears in another child under this skills directory")
        return result

    info = framework_info()
    result["manager_framework_version"] = info["framework_version"]
    instance_path = root / "framework" / "instance.json"
    legacy_path = root / "framework" / "version.json"
    if not instance_path.is_file():
        if legacy_path.is_file():
            legacy = load_object(legacy_path)
            if legacy.get("project_id") != project_id:
                issues.append("legacy framework version project_id does not match")
                return result
            result.update(
                {
                    "status": "upgrade-required",
                    "read_allowed": True,
                    "legacy_framework_version": legacy.get("framework_version"),
                }
            )
            issues.append("legacy child requires an accepted thin-adapter upgrade before formal writes")
            return result
        issues.append("framework/instance.json is missing")
        return result

    try:
        instance = load_object(instance_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        issues.append(str(exc))
        return result
    result["instance"] = instance
    if instance.get("schema") != INSTANCE_SCHEMA:
        issues.append("unsupported project instance schema")
        return result
    if instance.get("project_id") != project_id:
        issues.append("instance project_id does not match the bound project")
        return result
    observed_name = result.get("skill_name")
    if instance.get("skill_name") != observed_name or root.name != observed_name:
        issues.append("child skill name, folder name, and instance skill_name must match")
        return result
    if instance.get("manager_skill") != MANAGER_SKILL:
        issues.append("instance manager_skill is unsupported")
        return result

    entry_protocol = instance.get("entry_protocol")
    result["entry_protocol"] = entry_protocol
    if entry_protocol not in info["supported_entry_protocols"]:
        result.update({"status": "upgrade-required", "read_allowed": True})
        issues.append("child entry protocol is not supported by the installed total skill")
        return result

    observed_schemas = {}
    for key, relative in DATA_FILES.items():
        path = root / relative
        if allow_missing_derived and key == "project_map" and not path.is_file():
            observed_schemas[key] = CURRENT_DATA_SCHEMAS[key]
        else:
            observed_schemas[key] = load_object(path).get("schema")
    observed_schemas["handoff"] = CURRENT_DATA_SCHEMAS["handoff"]
    declared_schemas = instance.get("data_schemas")
    supported_schemas = info["supported_data_schemas"]
    if not isinstance(declared_schemas, dict) or any(
        declared_schemas.get(key) != observed_schemas.get(key) for key in CURRENT_DATA_SCHEMAS
    ):
        result.update({"status": "migration-required", "read_allowed": True})
        issues.append("declared project-data schemas do not match the project files")
        return result
    if not isinstance(supported_schemas, dict) or any(
        declared_schemas.get(key) != supported_schemas.get(key) for key in CURRENT_DATA_SCHEMAS
    ):
        result.update({"status": "migration-required", "read_allowed": True})
        issues.append("project-data schemas are not supported by the installed total skill")
        return result

    ownership = instance.get("ownership")
    if not isinstance(ownership, dict):
        issues.append("instance ownership declaration is missing")
        return result
    expected_hashes = ownership.get("managed_hashes")
    if not isinstance(expected_hashes, dict) or not expected_hashes:
        issues.append("instance managed hashes are missing")
        return result
    try:
        actual_hashes = managed_hashes(root, sorted(expected_hashes))
    except BindingError as exc:
        issues.append(str(exc))
        return result
    if actual_hashes != expected_hashes:
        result.update({"status": "upgrade-required", "read_allowed": True})
        result["managed_hashes"] = {"expected": expected_hashes, "actual": actual_hashes}
        issues.append("framework-managed adapter files were modified")
        return result

    result.update({"status": "compatible", "read_allowed": True, "write_allowed": True})
    return result


def require_binding(
    skill_root: Path,
    *,
    write: bool,
    expected_project_id: str | None = None,
    allow_missing_derived: bool = False,
) -> dict:
    result = inspect_project(
        skill_root,
        expected_project_id=expected_project_id,
        allow_missing_derived=allow_missing_derived,
    )
    allowed = result["write_allowed"] if write else result["status"] in READABLE_STATUSES
    if not allowed:
        action = "write" if write else "read"
        detail = "; ".join(result.get("issues", [])) or result["status"]
        raise BindingError(f"project binding blocks {action}: {detail}")
    return result


def session_decision(active_project_id: str | None, requested: dict) -> dict:
    requested_id = requested["project_id"]
    if active_project_id is None:
        action = "bind"
        allowed = True
    elif active_project_id == requested_id:
        action = "continue"
        allowed = True
    else:
        action = "switch-confirmation-required"
        allowed = False
    return {
        "schema": "ltpm-conversation-binding-decision/v1",
        "action": action,
        "active_project_id": active_project_id,
        "requested_project_id": requested_id,
        "requested_project_name": requested.get("project_name"),
        "ordinary_project_work_allowed": allowed,
        "guidance": (
            "Bind this ordinary conversation to the requested project."
            if action == "bind"
            else "Continue within the existing project binding."
            if action == "continue"
            else "Do not switch silently; obtain explicit confirmation or start a new conversation."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("--project-skill", required=True, type=Path)
    inspect_parser.add_argument("--expected-project-id")
    session_parser = subparsers.add_parser("session-check")
    session_parser.add_argument("--project-skill", required=True, type=Path)
    session_parser.add_argument("--active-project-id")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = inspect_project(args.project_skill, getattr(args, "expected_project_id", None))
        if args.command == "session-check":
            if result["status"] not in READABLE_STATUSES:
                raise BindingError("requested project is not unambiguous and readable")
            output = session_decision(args.active_project_id, result)
            print(json.dumps({"ok": True, **output}, ensure_ascii=False, indent=2))
            return 0
        ok = result["status"] in READABLE_STATUSES
        stream = sys.stdout if ok else sys.stderr
        print(json.dumps({"ok": ok, **result}, ensure_ascii=False, indent=2), file=stream)
        return 0 if ok else 1
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate formal records and the deterministic derived view of a project skill."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from render_project_views import build_project_map, load_store


REQUIRED = (
    "SKILL.md",
    "agents/openai.yaml",
    "framework/version.json",
    "records/store.json",
    "views/project-map.json",
)
PRIORITIES = {"high", "low"}
RELATIONS = {
    "contains",
    "depends_on",
    "causes",
    "supports",
    "contradicts",
    "tests",
    "produces",
    "supersedes",
    "blocks",
    "derived_from",
}


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    for relative in REQUIRED:
        if not (root / relative).is_file():
            errors.append(f"missing required file: {relative}")
    if errors:
        return errors

    skill_text = (root / "SKILL.md").read_text(encoding="utf-8")
    if not re.search(r"^name: [a-z0-9]+(?:-[a-z0-9]+)*$", skill_text, re.MULTILINE):
        errors.append("SKILL.md has no valid skill name")
    openai_text = (root / "agents" / "openai.yaml").read_text(encoding="utf-8")
    if "allow_implicit_invocation: false" not in openai_text:
        errors.append("project skill must disable implicit invocation")

    try:
        store = load_store(root / "records" / "store.json")
        view = load_json(root / "views" / "project-map.json")
        version = load_json(root / "framework" / "version.json")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(str(exc))
        return errors

    if store.get("schema") != "ltpm-record-store/v1":
        errors.append("unsupported records/store.json schema")
    project_ids = {store.get("project_id"), view.get("project_id"), version.get("project_id")}
    if None in project_ids or len(project_ids) != 1:
        errors.append("project_id is missing or inconsistent")
    if not isinstance(store.get("revision"), int) or isinstance(store.get("revision"), bool) or store["revision"] < 0:
        errors.append("record store revision must be a non-negative integer")

    records = store.get("records")
    if not isinstance(records, list):
        errors.append("records must be a list")
        records = []
    ids = [record.get("id") for record in records if isinstance(record, dict)]
    if None in ids or len(ids) != len(set(ids)) or len(ids) != len(records):
        errors.append("formal record IDs must be present and unique")
    task_ids: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            errors.append("formal record must be an object")
            continue
        if record.get("confirmation_status") != "accepted":
            errors.append(f"formal record is not accepted: {record.get('id')}")
        if record.get("kind") == "task":
            task_ids.add(record.get("id"))
            if record.get("task_priority") not in PRIORITIES:
                errors.append(f"invalid task priority for {record.get('id')}")

    relations = store.get("relations")
    if not isinstance(relations, list):
        errors.append("relations must be a list")
        relations = []
    relation_ids: list[str | None] = []
    for relation in relations:
        if not isinstance(relation, dict):
            errors.append("relation must be an object")
            continue
        relation_ids.append(relation.get("id"))
        if relation.get("confirmation_status") != "accepted":
            errors.append(f"formal relation is not accepted: {relation.get('id')}")
        if relation.get("from") not in ids or relation.get("to") not in ids:
            errors.append("relation references an unknown formal record")
        if relation.get("type") not in RELATIONS:
            errors.append(f"invalid relation type: {relation.get('type')}")
    if None in relation_ids or len(relation_ids) != len(set(relation_ids)):
        errors.append("formal relation IDs must be present and unique")

    focus = store.get("current_focus")
    if not isinstance(focus, dict):
        errors.append("current_focus must be an object")
    else:
        active_task = focus.get("active_task_id")
        if active_task is not None and active_task not in task_ids:
            errors.append("active_task_id is not a known formal task")

    try:
        expected_view = build_project_map(store)
        if view != expected_view:
            errors.append("views/project-map.json is stale or manually edited; regenerate it from records/store.json")
    except ValueError as exc:
        errors.append(str(exc))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_root", type=Path)
    args = parser.parse_args()
    root = args.skill_root.expanduser().resolve()
    errors = validate(root)
    if errors:
        print(json.dumps({"valid": False, "errors": errors}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"valid": True, "skill_root": str(root)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

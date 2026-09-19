#!/usr/bin/env python3
"""Validate structural invariants of a generated project-local skill."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


REQUIRED = (
    "SKILL.md",
    "agents/openai.yaml",
    "framework/version.json",
    "state/project-map.json",
    "state/current-focus.json",
    "database/index.json",
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
        project_map = load_json(root / "state" / "project-map.json")
        focus = load_json(root / "state" / "current-focus.json")
        database = load_json(root / "database" / "index.json")
        version = load_json(root / "framework" / "version.json")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(str(exc))
        return errors

    project_ids = {project_map.get("project_id"), focus.get("project_id"), database.get("project_id"), version.get("project_id")}
    if None in project_ids or len(project_ids) != 1:
        errors.append("project_id is missing or inconsistent")
    if not isinstance(project_map.get("revision"), int) or project_map["revision"] < 0:
        errors.append("project map revision must be a non-negative integer")
    if focus.get("map_revision") != project_map.get("revision"):
        errors.append("current-focus map_revision does not match project map")

    nodes = project_map.get("nodes")
    if not isinstance(nodes, list):
        errors.append("nodes must be a list")
        nodes = []
    ids = [node.get("id") for node in nodes if isinstance(node, dict)]
    if None in ids or len(ids) != len(set(ids)) or len(ids) != len(nodes):
        errors.append("node IDs must be present and unique")
    task_ids = set()
    task_priorities: dict[str, str] = {}
    for node in nodes:
        if not isinstance(node, dict):
            continue
        if node.get("type") == "task":
            task_ids.add(node.get("id"))
            if node.get("task_priority") not in PRIORITIES:
                errors.append(f"invalid task priority for {node.get('id')}")
            else:
                task_priorities[node["id"]] = node["task_priority"]

    for relation in project_map.get("relations", []):
        if not isinstance(relation, dict):
            errors.append("relation must be an object")
            continue
        if relation.get("from") not in ids or relation.get("to") not in ids:
            errors.append("relation references an unknown node")
        if relation.get("type") not in RELATIONS:
            errors.append(f"invalid relation type: {relation.get('type')}")

    focus_tasks = focus.get("tasks", {})
    if set(focus_tasks) != PRIORITIES:
        errors.append("current-focus tasks must contain exactly high and low")
    else:
        listed_task_ids: list[str] = []
        for priority, values in focus_tasks.items():
            if not isinstance(values, list) or any(value not in task_ids for value in values):
                errors.append(f"current-focus {priority} contains an unknown task")
                continue
            listed_task_ids.extend(values)
            for value in values:
                if task_priorities.get(value) != priority:
                    errors.append(f"current-focus priority does not match project map for {value}")
        if len(listed_task_ids) != len(set(listed_task_ids)) or set(listed_task_ids) != task_ids:
            errors.append("every project-map task must appear exactly once in current-focus")
    active_task = focus.get("active_task_id")
    if active_task is not None and active_task not in task_ids:
        errors.append("active_task_id is not a known task")
    if not isinstance(database.get("records"), list):
        errors.append("database records must be a list")
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

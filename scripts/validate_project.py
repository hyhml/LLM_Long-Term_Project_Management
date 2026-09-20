#!/usr/bin/env python3
"""Validate authoritative project data, derived views, and retrieval coverage metadata."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from render_project_views import build_project_map, load_inputs, load_object


REQUIRED = (
    "SKILL.md",
    "agents/openai.yaml",
    "framework/version.json",
    "state/project.json",
    "state/task-board.json",
    "records/store.json",
    "sources/registry.json",
    "views/project-map.json",
    "index/manifest.json",
)
SCHEMAS = {
    "project": "ltpm-project-state/v1",
    "board": "ltpm-task-board/v1",
    "store": "ltpm-record-store/v2",
    "sources": "ltpm-source-registry/v1",
    "view": "ltpm-project-map-view/v2",
    "index": "ltpm-index-manifest/v1",
}
PRIORITIES = {"high", "low"}
TASK_STATUSES = {"pending", "active", "blocked", "done"}
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
    "evaluates",
    "decides",
    "cites",
}
CORE_KINDS = {"task", "claim", "evidence", "attempt", "review", "decision", "question", "artifact", "risk"}
DISALLOWED_FORMAL_KINDS = {"log", "cache", "raw-output", "temporary"}
FAILED_ATTEMPT_FIELDS = {
    "attempted",
    "failure_reason",
    "failure_conditions",
    "retry_conditions",
    "evidence_or_reproduction",
}


def non_empty(value: object) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return bool(value)
    if isinstance(value, dict):
        return bool(value)
    return value is not None


def valid_extension(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*:[a-z0-9]+(?:-[a-z0-9]+)*", value) is not None


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
        project, board, store, sources = load_inputs(root)
        view = load_object(root / "views" / "project-map.json")
        index = load_object(root / "index" / "manifest.json")
        version = load_object(root / "framework" / "version.json")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(str(exc))
        return errors

    values = {"project": project, "board": board, "store": store, "sources": sources, "view": view, "index": index}
    for name, schema in SCHEMAS.items():
        if values[name].get("schema") != schema:
            errors.append(f"unsupported {name} schema")

    project_id = project.get("project_id")
    project_ids = [board.get("project_id"), store.get("project_id"), sources.get("project_id"), view.get("project_id"), index.get("project_id"), version.get("project_id")]
    if not isinstance(project_id, str) or not project_id or any(value != project_id for value in project_ids):
        errors.append("project_id is missing or inconsistent")
    if not non_empty(project.get("project_name")):
        errors.append("project_name must not be empty")
    revision = project.get("revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 0:
        errors.append("project revision must be a non-negative integer")
    for name, value in (("task board", board), ("record store", store), ("source registry", sources)):
        if value.get("project_revision") != revision:
            errors.append(f"{name} revision does not match project revision")

    contract = project.get("objective_contract")
    contract_ids: set[str] = set()
    if not isinstance(contract, dict):
        errors.append("objective_contract must be an object")
    else:
        objective_id = contract.get("objective_id")
        if not isinstance(objective_id, str) or not objective_id:
            errors.append("objective_contract requires a stable objective_id")
        else:
            contract_ids.add(objective_id)
        if not isinstance(contract.get("objective_revision"), int) or isinstance(contract.get("objective_revision"), bool) or contract.get("objective_revision", -1) < 0:
            errors.append("objective_revision must be a non-negative integer")
        if not non_empty(contract.get("objective")):
            errors.append("objective must not be empty")
        for field in ("scope", "non_goals", "assumptions", "evidence_standard", "completion_standard"):
            if not isinstance(contract.get(field), list) or any(not isinstance(item, str) or not item.strip() for item in contract.get(field, [])):
                errors.append(f"objective_contract {field} must be a list of non-empty strings")
        for required_non_empty in ("scope", "evidence_standard", "completion_standard"):
            if isinstance(contract.get(required_non_empty), list) and not contract[required_non_empty]:
                errors.append(f"objective_contract {required_non_empty} must not be empty")

    records = store.get("records")
    if not isinstance(records, list):
        errors.append("records must be a list")
        records = []
    record_ids: set[str] = set()
    task_ids: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            errors.append("formal record must be an object")
            continue
        record_id = record.get("id")
        if not isinstance(record_id, str) or not record_id or record_id in record_ids:
            errors.append("formal record IDs must be non-empty and unique")
            continue
        record_ids.add(record_id)
        if not non_empty(record.get("title")):
            errors.append(f"formal record title must not be empty: {record_id}")
        if record.get("confirmation_status") != "accepted":
            errors.append(f"formal record is not accepted: {record_id}")
        kind = record.get("kind")
        if kind in DISALLOWED_FORMAL_KINDS:
            errors.append(f"transient material cannot be a formal record: {record_id}")
        elif kind not in CORE_KINDS and not valid_extension(kind):
            errors.append(f"invalid record kind for {record_id}; use a core kind or namespaced extension")
        if kind == "task":
            task_ids.add(record_id)
        content = record.get("content")
        if not isinstance(content, dict):
            errors.append(f"formal record content must be an object: {record_id}")
            continue
        if kind == "attempt" and content.get("outcome") == "failed":
            missing = sorted(field for field in FAILED_ATTEMPT_FIELDS if not non_empty(content.get(field)))
            if missing:
                errors.append(f"failed attempt {record_id} lacks reusable failure context: {', '.join(missing)}")

    board_tasks = board.get("tasks")
    listed_task_ids: list[str] = []
    if not isinstance(board_tasks, dict) or set(board_tasks) != PRIORITIES:
        errors.append("task board must contain exactly high and low task lists")
    else:
        for priority, entries in board_tasks.items():
            if not isinstance(entries, list):
                errors.append(f"task board {priority} must be a list")
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    errors.append(f"task board {priority} entry must be an object")
                    continue
                task_id = entry.get("task_id")
                if not isinstance(task_id, str) or not task_id:
                    errors.append(f"task board {priority} task_id must be a non-empty string")
                    continue
                listed_task_ids.append(task_id)
                if task_id not in task_ids:
                    errors.append(f"task board references an unknown task: {task_id}")
                if entry.get("status") not in TASK_STATUSES:
                    errors.append(f"invalid task status for {task_id}")
        if len(listed_task_ids) != len(set(listed_task_ids)) or set(listed_task_ids) != task_ids:
            errors.append("every formal task must appear exactly once in the task board")

    focus = project.get("current_focus")
    if not isinstance(focus, dict):
        errors.append("current_focus must be an object")
    elif focus.get("active_task_id") is not None and focus.get("active_task_id") not in task_ids:
        errors.append("active_task_id is not a known formal task")

    source_values = sources.get("sources")
    if not isinstance(source_values, list):
        errors.append("sources registry must contain a sources list")
        source_values = []
    source_ids: set[str] = set()
    for source in source_values:
        if not isinstance(source, dict):
            errors.append("registered source must be an object")
            continue
        source_id = source.get("source_id")
        if not isinstance(source_id, str) or not source_id or source_id in source_ids:
            errors.append("source IDs must be non-empty and unique")
            continue
        source_ids.add(source_id)
        if source.get("confirmation_status") != "accepted":
            errors.append(f"registered source is not accepted: {source_id}")
        for field in ("source_type", "title", "access_scope"):
            if not non_empty(source.get(field)):
                errors.append(f"registered source {source_id} requires {field}")

    relations = store.get("relations")
    if not isinstance(relations, list):
        errors.append("relations must be a list")
        relations = []
    endpoints = contract_ids | record_ids | source_ids
    relation_ids: set[str] = set()
    for relation in relations:
        if not isinstance(relation, dict):
            errors.append("relation must be an object")
            continue
        relation_id = relation.get("id")
        if not isinstance(relation_id, str) or not relation_id or relation_id in relation_ids:
            errors.append("formal relation IDs must be non-empty and unique")
            continue
        relation_ids.add(relation_id)
        if relation.get("confirmation_status") != "accepted":
            errors.append(f"formal relation is not accepted: {relation_id}")
        relation_from = relation.get("from")
        relation_to = relation.get("to")
        if not isinstance(relation_from, str) or not isinstance(relation_to, str) or relation_from not in endpoints or relation_to not in endpoints:
            errors.append(f"relation references an unknown endpoint: {relation_id}")
        relation_type = relation.get("type")
        if relation_type not in RELATIONS and not valid_extension(relation_type):
            errors.append(f"invalid relation type: {relation_type}")

    coverage = index.get("coverage")
    if index.get("status") not in {"not-built", "ready", "stale"}:
        errors.append("index status must be not-built, ready, or stale")
    if not isinstance(coverage, dict):
        errors.append("index manifest must report coverage")
    else:
        for field in ("authorized_scope", "indexed_record_ids", "indexed_source_ids", "indexed_paths", "exclusions"):
            if not isinstance(coverage.get(field), list):
                errors.append(f"index coverage {field} must be a list")

    try:
        expected_view = build_project_map(project, board, store, sources)
        if view != expected_view:
            errors.append("views/project-map.json is stale or manually edited; regenerate it from formal data")
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

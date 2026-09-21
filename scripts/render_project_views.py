#!/usr/bin/env python3
"""Deterministically render the directly loaded map from formal project data."""

from __future__ import annotations

import argparse
import json
import tempfile
import sys
from pathlib import Path

from project_binding import require_binding

VIEW_SCHEMA = "ltpm-project-map-view/v3"
PROJECT_SCHEMA = "ltpm-project-state/v2"
TASK_BOARD_SCHEMA = "ltpm-task-board/v1"
STORE_SCHEMA = "ltpm-record-store/v2"
SOURCE_SCHEMA = "ltpm-source-registry/v1"


def load_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def load_inputs(skill_root: Path) -> tuple[dict, dict, dict, dict]:
    return (
        load_object(skill_root / "state" / "project.json"),
        load_object(skill_root / "state" / "task-board.json"),
        load_object(skill_root / "records" / "store.json"),
        load_object(skill_root / "sources" / "registry.json"),
    )


def build_project_map(project: dict, board: dict, store: dict, sources: dict) -> dict:
    """Build navigation without treating pending work or an index as authority."""
    expected_schemas = (
        (project, PROJECT_SCHEMA),
        (board, TASK_BOARD_SCHEMA),
        (store, STORE_SCHEMA),
        (sources, SOURCE_SCHEMA),
    )
    for value, schema in expected_schemas:
        if value.get("schema") != schema:
            raise ValueError(f"unsupported schema: expected {schema}, got {value.get('schema')}")

    revision = project.get("revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 0:
        raise ValueError("project revision must be a non-negative integer")
    for label, value in (("task board", board), ("record store", store), ("source registry", sources)):
        if value.get("project_revision") != revision:
            raise ValueError(f"{label} revision does not match project revision")

    contract = project.get("objective_contract")
    if not isinstance(contract, dict) or not contract.get("objective_id"):
        raise ValueError("project objective contract is missing a stable objective_id")
    records = store.get("records")
    relations = store.get("relations")
    registered_sources = sources.get("sources")
    if not isinstance(records, list) or not isinstance(relations, list) or not isinstance(registered_sources, list):
        raise ValueError("formal records, relations, and sources must be lists")

    record_by_id: dict[str, dict] = {}
    nodes = [
        {
            "id": contract["objective_id"],
            "type": "objective",
            "title": contract.get("objective"),
            "objective_revision": contract.get("objective_revision"),
            "formal_location": "../state/project.json#objective_contract",
        }
    ]
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("every formal record must be an object")
        if record.get("confirmation_status") != "accepted":
            raise ValueError(f"refusing to render unaccepted formal record: {record.get('id')}")
        record_id = record.get("id")
        if not isinstance(record_id, str) or not record_id or record_id in record_by_id:
            raise ValueError("formal record IDs must be non-empty and unique")
        record_by_id[record_id] = record
        nodes.append(
            {
                "id": record_id,
                "type": record.get("kind"),
                "title": record.get("title"),
                "confirmation_status": "accepted",
                "formal_record_id": record_id,
            }
        )

    task_view: dict[str, list[dict]] = {"high": [], "low": []}
    board_tasks = board.get("tasks")
    if not isinstance(board_tasks, dict):
        raise ValueError("task board tasks must be an object")
    task_metadata: dict[str, tuple[str, str]] = {}
    for priority in ("high", "low"):
        entries = board_tasks.get(priority)
        if not isinstance(entries, list):
            raise ValueError(f"task board {priority} must be a list")
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError("task board entries must be objects")
            task_id = entry.get("task_id")
            if not isinstance(task_id, str) or not task_id:
                raise ValueError("task board task_id values must be non-empty strings")
            record = record_by_id.get(task_id)
            if record is None or record.get("kind") != "task":
                raise ValueError(f"task board references an unknown task record: {task_id}")
            if task_id in task_metadata:
                raise ValueError(f"task appears more than once in task board: {task_id}")
            status = entry.get("status")
            task_metadata[task_id] = (priority, status)
            task_view[priority].append(
                {
                    "task_id": task_id,
                    "title": record.get("title"),
                    "status": status,
                    "formal_record_id": task_id,
                }
            )
    for node in nodes:
        if node["type"] == "task" and node["id"] in task_metadata:
            node["task_priority"], node["status"] = task_metadata[node["id"]]

    source_nodes = []
    source_ids: set[str] = set()
    for source in registered_sources:
        if not isinstance(source, dict):
            raise ValueError("every registered source must be an object")
        if source.get("confirmation_status") != "accepted":
            raise ValueError(f"refusing to render unaccepted source: {source.get('source_id')}")
        source_id = source.get("source_id")
        if not isinstance(source_id, str) or not source_id or source_id in source_ids:
            raise ValueError("registered source IDs must be non-empty and unique")
        source_ids.add(source_id)
        source_nodes.append(
            {
                "id": source_id,
                "type": "source",
                "source_type": source.get("source_type"),
                "title": source.get("title"),
                "formal_location": "../sources/registry.json",
            }
        )

    for relation in relations:
        if not isinstance(relation, dict):
            raise ValueError("every formal relation must be an object")
        if relation.get("confirmation_status") != "accepted":
            raise ValueError(f"refusing to render unaccepted formal relation: {relation.get('id')}")

    return {
        "schema": VIEW_SCHEMA,
        "project_id": project.get("project_id"),
        "project_name": project.get("project_name"),
        "source": {
            "project_revision": revision,
            "generator": "render_project_views.py/v3",
            "inputs": [
                "../state/project.json",
                "../state/task-board.json",
                "../records/store.json",
                "../sources/registry.json",
            ],
        },
        "objective_contract": contract,
        "current_focus": project.get("current_focus"),
        "tasks": task_view,
        "nodes": nodes + source_nodes,
        "relations": relations,
        "navigation": {
            "formal_project_state": "../state/",
            "formal_records": "../records/",
            "registered_sources": "../sources/registry.json",
            "pending_work": "../work/",
            "retrieval_index": "../index/",
            "handoffs": "../packages/",
        },
    }


def encoded(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=".view-", delete=False
    ) as temporary:
        temporary.write(text)
        temporary_path = Path(temporary.name)
    try:
        temporary_path.replace(path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def render(skill_root: Path) -> dict:
    view = build_project_map(*load_inputs(skill_root))
    write_atomic(skill_root / "views" / "project-map.json", encoded(view))
    return view


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_root", type=Path)
    args = parser.parse_args()
    root = args.skill_root.expanduser().resolve()
    try:
        binding = require_binding(root, write=True, allow_missing_derived=True)
        view = render(root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "rendered": str(root / "views" / "project-map.json"),
                "project_id": view["project_id"],
                "binding_status": binding["status"],
                "source_revision": view["source"]["project_revision"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

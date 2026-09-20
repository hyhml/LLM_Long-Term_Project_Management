#!/usr/bin/env python3
"""Deterministically render directly loaded views from accepted project records."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path


VIEW_SCHEMA = "ltpm-project-map-view/v1"
STORE_SCHEMA = "ltpm-record-store/v1"


def load_store(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def build_project_map(store: dict) -> dict:
    """Build the compact navigation view; do not add facts absent from the store."""
    if store.get("schema") != STORE_SCHEMA:
        raise ValueError(f"unsupported record store schema: {store.get('schema')}")
    records = store.get("records")
    relations = store.get("relations")
    if not isinstance(records, list) or not isinstance(relations, list):
        raise ValueError("record store must contain records and relations lists")

    nodes = []
    priorities: dict[str, list[str]] = {"high": [], "low": []}
    objective = None
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("every formal record must be an object")
        if record.get("confirmation_status") != "accepted":
            raise ValueError(f"refusing to render unaccepted formal record: {record.get('id')}")
        content = record.get("content", {})
        if not isinstance(content, dict):
            raise ValueError(f"formal record content must be an object: {record.get('id')}")
        node = {
            "id": record.get("id"),
            "type": record.get("kind"),
            "title": record.get("title"),
            "status": record.get("status"),
            "formal_record_id": record.get("id"),
        }
        if record.get("kind") == "task":
            node["task_priority"] = record.get("task_priority")
            priority = record.get("task_priority")
            if priority not in priorities:
                raise ValueError(f"invalid task priority for {record.get('id')}")
            priorities[priority].append(record.get("id"))
        if record.get("detail_record_ids"):
            node["detail_record_ids"] = record["detail_record_ids"]
        nodes.append(node)
        if record.get("kind") == "goal" and objective is None:
            objective = {
                "record_id": record.get("id"),
                "title": record.get("title"),
                "non_goals": content.get("non_goals", []),
                "completion_criteria": content.get("completion_criteria", []),
            }

    for relation in relations:
        if not isinstance(relation, dict):
            raise ValueError("every formal relation must be an object")
        if relation.get("confirmation_status") != "accepted":
            raise ValueError(f"refusing to render unaccepted formal relation: {relation.get('id')}")

    return {
        "schema": VIEW_SCHEMA,
        "project_id": store.get("project_id"),
        "project_name": store.get("project_name"),
        "source": {
            "path": "../records/store.json",
            "revision": store.get("revision"),
            "generator": "render_project_views.py/v1",
        },
        "objective": objective,
        "current_focus": store.get("current_focus"),
        "tasks": priorities,
        "nodes": nodes,
        "relations": relations,
        "navigation": {
            "formal_records": "../records/store.json",
            "accepted_materials": "../records/materials/",
            "pending_work": "../work/",
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
    store_path = skill_root / "records" / "store.json"
    output_path = skill_root / "views" / "project-map.json"
    view = build_project_map(load_store(store_path))
    write_atomic(output_path, encoded(view))
    return view


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_root", type=Path)
    args = parser.parse_args()
    root = args.skill_root.expanduser().resolve()
    view = render(root)
    print(
        json.dumps(
            {
                "rendered": str(root / "views" / "project-map.json"),
                "project_id": view["project_id"],
                "source_revision": view["source"]["revision"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Read compact maps from an explicit set of projects without merging authority."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from project_binding import READABLE_STATUSES, inspect_project, load_object


class CoordinationError(ValueError):
    pass


def coordinate(project_roots: list[Path]) -> dict:
    if len(project_roots) < 2:
        raise CoordinationError("cross-project coordination requires at least two explicit project skills")
    participants = []
    seen_ids: set[str] = set()
    for supplied in project_roots:
        root = supplied.expanduser().resolve()
        binding = inspect_project(root)
        if binding["status"] not in READABLE_STATUSES:
            raise CoordinationError(
                f"project is not unambiguous and readable: {root}: {'; '.join(binding.get('issues', []))}"
            )
        project_id = binding["project_id"]
        if project_id in seen_ids:
            raise CoordinationError(f"duplicate project_id in coordination set: {project_id}")
        seen_ids.add(project_id)
        view = load_object(root / "views" / "project-map.json")
        participants.append(
            {
                "project_id": project_id,
                "project_name": binding.get("project_name"),
                "project_skill_root": str(root),
                "project_revision": binding.get("project_revision"),
                "binding_status": binding["status"],
                "summary": {
                    "objective_contract": view.get("objective_contract"),
                    "current_focus": view.get("current_focus"),
                    "tasks": view.get("tasks"),
                    "node_count": len(view.get("nodes", [])),
                    "relation_count": len(view.get("relations", [])),
                },
                "coverage": {
                    "searched": ["views/project-map.json"],
                    "not_searched": [
                        "record bodies not present in the compact map",
                        "registered source bodies",
                        "work/ pending material",
                        "project artifacts outside the child skill",
                    ],
                },
            }
        )
    return {
        "schema": "ltpm-cross-project-coordination/v1",
        "mode": "explicit-read-mostly",
        "participants": participants,
        "authority": {
            "merged": False,
            "writes_permitted": False,
            "proposal_rule": "Produce separate proposal sets identified by destination project_id.",
            "commit_rule": "Commit only from each separately bound project context.",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-skill", action="append", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = coordinate(args.project_skill)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

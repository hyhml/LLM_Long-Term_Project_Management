#!/usr/bin/env python3
"""Create a project-local skill from the framework's versioned template."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import sys
import uuid
from pathlib import Path

from render_project_views import render as render_project_views


SKILL_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def render(source: Path, destination: Path, replacements: dict[str, str]) -> None:
    text = source.read_text(encoding="utf-8")
    for key, value in replacements.items():
        text = text.replace(f"@@{key}@@", value)
    if "@@" in text:
        raise ValueError(f"unresolved template token in {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--skill-name", required=True)
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--goal", required=True)
    parser.add_argument("--scope", action="append", required=True)
    parser.add_argument("--non-goal", action="append", default=[])
    parser.add_argument("--assumption", action="append", default=[])
    parser.add_argument("--evidence-standard", action="append", required=True)
    parser.add_argument("--criterion", action="append", required=True)
    parser.add_argument("--high-task", action="append", default=[])
    parser.add_argument("--low-task", action="append", default=[])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.project_root.expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"project root is not a directory: {root}")
    if not SKILL_RE.fullmatch(args.skill_name) or len(args.skill_name) > 63:
        raise SystemExit("skill name must be <=63 chars of lowercase letters, digits, and single hyphens")
    if not args.project_name.strip() or "\n" in args.project_name:
        raise SystemExit("project name must be a non-empty single line")

    skill_root = root / ".agents" / "skills" / args.skill_name
    if skill_root.exists():
        raise SystemExit(f"destination already exists: {skill_root}")

    framework_root = Path(__file__).resolve().parents[1]
    template_root = framework_root / "assets" / "project-skill-template"
    framework_map = json.loads((framework_root / "references" / "framework-map.json").read_text(encoding="utf-8"))
    framework_version = framework_map["framework_version"]
    generated_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    project_id = f"proj-{uuid.uuid4()}"

    replacements = {
        "SKILL_NAME": args.skill_name,
        "PROJECT_NAME_HEADING": args.project_name,
        "PROJECT_NAME_JSON": json.dumps(args.project_name, ensure_ascii=False),
        "DESCRIPTION_JSON": json.dumps(
            f'Manage the long-running project "{args.project_name}" through explicit maintainer, explorer, and integration sessions. Invoke explicitly for this project only.',
            ensure_ascii=False,
        ),
        "DEFAULT_PROMPT_JSON": json.dumps(
            f"Use ${args.skill_name} to continue this managed project.", ensure_ascii=False
        ),
        "FRAMEWORK_VERSION": framework_version,
        "GENERATED_AT": generated_at,
        "PROJECT_ID": project_id,
    }

    try:
        render(template_root / "SKILL.md.tmpl", skill_root / "SKILL.md", replacements)
        render(
            template_root / "agents" / "openai.yaml.tmpl",
            skill_root / "agents" / "openai.yaml",
            replacements,
        )
        render(
            template_root / "framework" / "version.json.tmpl",
            skill_root / "framework" / "version.json",
            replacements,
        )
        shutil.copytree(
            template_root / "framework" / "conditional",
            skill_root / "framework" / "conditional",
        )

        records = []
        task_ids: dict[str, list[str]] = {"high": [], "low": []}
        task_board: dict[str, list[dict[str, str]]] = {"high": [], "low": []}
        task_number = 1
        for priority, titles in (("high", args.high_task), ("low", args.low_task)):
            for title in titles:
                task_id = f"task-{task_number:03d}"
                task_number += 1
                task_ids[priority].append(task_id)
                records.append(
                    {
                        "id": task_id,
                        "kind": "task",
                        "title": title,
                        "confirmation_status": "accepted",
                        "content": {},
                    }
                )
                task_board[priority].append({"task_id": task_id, "status": "pending"})

        relations = [
            {
                "id": f"relation-{index:03d}",
                "from": "objective-001",
                "type": "contains",
                "to": task_id,
                "confirmation_status": "accepted",
            }
            for index, task_id in enumerate(task_ids["high"] + task_ids["low"], start=1)
        ]
        project_state = {
            "schema": "ltpm-project-state/v2",
            "project_id": project_id,
            "project_name": args.project_name,
            "revision": 0,
            "objective_contract": {
                "objective_id": "objective-001",
                "objective_revision": 0,
                "objective": args.goal,
                "scope": args.scope,
                "non_goals": args.non_goal,
                "assumptions": args.assumption,
                "evidence_standard": args.evidence_standard,
                "completion_standard": args.criterion,
            },
            "current_focus": {
                "active_task_id": (task_ids["high"] + task_ids["low"] + [None])[0],
                "task_contract": None,
            },
        }
        board = {
            "schema": "ltpm-task-board/v1",
            "project_id": project_id,
            "project_revision": 0,
            "tasks": task_board,
        }
        record_store = {
            "schema": "ltpm-record-store/v2",
            "project_id": project_id,
            "project_revision": 0,
            "records": records,
            "relations": relations,
        }
        source_registry = {
            "schema": "ltpm-source-registry/v1",
            "project_id": project_id,
            "project_revision": 0,
            "sources": [],
        }
        index_manifest = {
            "schema": "ltpm-index-manifest/v1",
            "project_id": project_id,
            "status": "not-built",
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
                    {
                        "scope": "registered source contents",
                        "reason": "no retrieval index has been built or authorized",
                    },
                    {
                        "scope": "work/",
                        "reason": "pending material is not formal project knowledge",
                    },
                ],
            },
        }
        write_json(skill_root / "state" / "project.json", project_state)
        write_json(skill_root / "state" / "task-board.json", board)
        write_json(skill_root / "records" / "store.json", record_store)
        write_json(skill_root / "sources" / "registry.json", source_registry)
        write_json(skill_root / "index" / "manifest.json", index_manifest)
        for relative in (
            "records/materials",
            "work/explorations",
            "work/candidate-tools",
            "work/transactions",
            "packages/inbox",
            "packages/outbox",
            "packages/archive",
            "packages/archive/receipts",
        ):
            (skill_root / relative).mkdir(parents=True, exist_ok=True)
        render_project_views(skill_root)
    except Exception:
        if skill_root.exists():
            shutil.rmtree(skill_root)
        raise

    print(json.dumps({"created": str(skill_root), "project_id": project_id, "revision": 0}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

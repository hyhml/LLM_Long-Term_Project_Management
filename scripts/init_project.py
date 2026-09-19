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
    parser.add_argument("--non-goal", action="append", default=[])
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

        nodes = [
            {
                "id": "goal-001",
                "type": "goal",
                "title": args.goal,
                "status": "confirmed",
                "database_record_ids": [],
            }
        ]
        task_ids: dict[str, list[str]] = {"high": [], "low": []}
        task_number = 1
        for priority, titles in (("high", args.high_task), ("low", args.low_task)):
            for title in titles:
                task_id = f"task-{task_number:03d}"
                task_number += 1
                task_ids[priority].append(task_id)
                nodes.append(
                    {
                        "id": task_id,
                        "type": "task",
                        "title": title,
                        "task_priority": priority,
                        "status": "pending",
                        "confirmed": True,
                        "database_record_ids": [],
                    }
                )

        skill_rel = f".agents/skills/{args.skill_name}"
        project_map = {
            "schema_version": 1,
            "project_id": project_id,
            "project_name": args.project_name,
            "revision": 0,
            "goal": args.goal,
            "non_goals": args.non_goal,
            "completion_criteria": args.criterion,
            "nodes": nodes,
            "relations": [
                {"from": "goal-001", "type": "contains", "to": task_id}
                for task_id in task_ids["high"] + task_ids["low"]
            ],
            "files": [
                {
                    "path": f"{skill_rel}/SKILL.md",
                    "role": "project skill entry and high-load framework rules",
                    "load": "always",
                },
                {
                    "path": f"{skill_rel}/state/project-map.json",
                    "role": "authoritative project relationship map",
                    "load": "always",
                },
                {
                    "path": f"{skill_rel}/state/current-focus.json",
                    "role": "confirmed priorities and current task contract",
                    "load": "always",
                },
                {
                    "path": f"{skill_rel}/database/index.json",
                    "role": "index of detailed discussion records",
                    "load": "conditional",
                },
                {
                    "path": f"{skill_rel}/database/records/",
                    "role": "detailed ideas, attempts, evidence, and decisions",
                    "load": "only referenced records",
                },
            ],
        }
        write_json(skill_root / "state" / "project-map.json", project_map)
        write_json(
            skill_root / "state" / "current-focus.json",
            {
                "schema_version": 1,
                "project_id": project_id,
                "map_revision": 0,
                "active_task_id": (task_ids["high"] + task_ids["low"] + [None])[0],
                "tasks": task_ids,
                "task_contract": None,
            },
        )
        write_json(
            skill_root / "database" / "index.json",
            {"schema_version": 1, "project_id": project_id, "records": []},
        )
        for relative in (
            "database/records",
            "packages/inbox",
            "packages/outbox",
            "packages/archive",
            "workbench/candidate-tools",
        ):
            (skill_root / relative).mkdir(parents=True, exist_ok=True)
    except Exception:
        if skill_root.exists():
            shutil.rmtree(skill_root)
        raise

    print(json.dumps({"created": str(skill_root), "project_id": project_id, "revision": 0}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

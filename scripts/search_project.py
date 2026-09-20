#!/usr/bin/env python3
"""Search authorized formal project metadata and always report retrieval coverage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def search(skill_root: Path, query: str) -> dict:
    project = load(skill_root / "state" / "project.json")
    store = load(skill_root / "records" / "store.json")
    registry = load(skill_root / "sources" / "registry.json")
    manifest = load(skill_root / "index" / "manifest.json")
    needle = query.casefold()
    results = []
    for record in store.get("records", []):
        if needle in text(record).casefold():
            results.append(
                {
                    "kind": "formal-record",
                    "id": record.get("id"),
                    "record_kind": record.get("kind"),
                    "title": record.get("title"),
                    "location": "records/store.json",
                }
            )
    for source in registry.get("sources", []):
        if needle in text(source).casefold():
            results.append(
                {
                    "kind": "source-registry-metadata",
                    "id": source.get("source_id"),
                    "source_type": source.get("source_type"),
                    "title": source.get("title"),
                    "location": "sources/registry.json",
                }
            )
    searched = [
        {
            "scope": "accepted formal record metadata and content stored in records/store.json",
            "record_ids": [record.get("id") for record in store.get("records", [])],
        },
        {
            "scope": "accepted source registry metadata; registered source bodies were not opened",
            "source_ids": [source.get("source_id") for source in registry.get("sources", [])],
        },
    ]
    not_searched = list(manifest.get("coverage", {}).get("exclusions", []))
    statement = (
        f"Found {len(results)} match(es) within the searched and authorized scope."
        if results
        else "No matches were found within the explicitly reported searched and authorized scope; index status and unsearched sources are reported below, and this does not establish absence from the project."
    )
    return {
        "query": query,
        "project_id": project.get("project_id"),
        "project_revision": project.get("revision"),
        "results": results,
        "coverage": {
            "index_status": manifest.get("status"),
            "index_generated_from_revision": manifest.get("generated_from_revision"),
            "searched": searched,
            "not_searched": not_searched,
            "statement": statement,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-skill", required=True, type=Path)
    parser.add_argument("--query", required=True)
    args = parser.parse_args()
    result = search(args.project_skill.expanduser().resolve(), args.query)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

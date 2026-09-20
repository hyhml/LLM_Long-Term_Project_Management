# Retrieval and coverage

Treat `index/` as disposable acceleration state, never as project authority. Exact accepted meaning comes from `state/`, `records/`, and `sources/`.

For lightweight metadata search, run:

```bash
python scripts/search_project.py \
  --project-skill /absolute/project/.agents/skills/example-project \
  --query "search text"
```

Every search response must state:

- project revision and index revision/status;
- the records, sources, paths, or collections actually searched;
- authorized material that was not searched;
- exclusions, truncation, stale-index state, and other coverage gaps.

Do not infer global absence from an empty result. Say only that no match was found in the currently searched, indexed, and authorized scope. Opening registered source bodies requires their own authorization and suitable tool; registry metadata search does not imply source-content coverage.

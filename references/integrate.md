# Verify, propose, and integrate

Never execute imported code during unpacking or review.

## Verify and unpack

```bash
python scripts/handoff.py verify /absolute/path/task.llmpack
python scripts/handoff.py unpack /absolute/path/task.llmpack --output-dir /new/empty/directory
```

The unpacker verifies safe relative paths, the exact manifest member set, sizes, and SHA-256 hashes before writing output.

Check that `project_id` matches. Compare `base_revision` with `records/store.json` revision. Version mismatch or a stale base revision is a conflict: continue reviewing, but do not commit any item as an automatic merge.

## Proposal phase

Read the handoff and only the formal records needed to understand its references. Present every `proposed_changes` entry separately, preserving its `change_id`.

For each item let the user:

- accept exactly as proposed;
- accept with an explicit modification;
- reject;
- defer for more analysis.

Also present candidate tools separately with their purpose, validation, dependencies, risks, and expected reuse.

## Commit phase

Before writing, summarize the exact accepted operations. Apply only accepted items to `records/`, increment `records/store.json` revision once for the batch, run `scripts/render_project_views.py`, and validate the project structure. Never edit `views/project-map.json` as the source of a change. Record rejected or deferred ideas formally only if the user separately accepts that archival change; otherwise leave them in `work/` or the package.

Archive the original `.llmpack` plus an integration receipt containing the package ID, old and new revisions, each change decision, and the user's tool-retention decisions.

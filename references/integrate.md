# Verify, propose, and integrate

Never execute imported code during unpacking or review.

## Verify and unpack

```bash
python scripts/handoff.py verify /absolute/path/task.llmpack
python scripts/handoff.py unpack /absolute/path/task.llmpack --output-dir /new/empty/directory
```

The unpacker verifies safe relative paths, the exact manifest member set, sizes, and SHA-256 hashes before writing output.

Check that `project_id` matches. Compare `base_revision` with `state/project.json` revision. Version mismatch or a stale base revision is a conflict: continue reviewing, but do not commit any item as an automatic merge.

## Proposal phase

Read the handoff and only the formal records needed to understand its references. Present every `proposed_changes` entry separately, preserving its `change_id`.

For each item let the user:

- accept exactly as proposed;
- accept with an explicit modification;
- reject;
- defer for more analysis.

Also present candidate tools separately with their purpose, validation, dependencies, risks, and expected reuse.

## Commit phase

Before writing, summarize the exact accepted operations. Then follow `references/commit.md`: edit only the prepared candidate, commit one accepted batch through the transaction tool, and preserve its receipt. Never edit `views/project-map.json` or `index/` as the source of a change. Record rejected or deferred ideas formally only if the user separately accepts that archival change; otherwise leave them in `work/` or the package.

Archive the original `.llmpack` plus an integration receipt containing the package ID, old and new revisions, each change decision, and the user's tool-retention decisions.

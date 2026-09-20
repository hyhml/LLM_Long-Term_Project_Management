# Explore and package

## Start exploration

Read the generated project's `SKILL.md` and directly loaded `views/project-map.json`. Select a confirmed high-priority task unless the user explicitly chooses otherwise. Read only the formal records referenced by the selected node when more detail is needed. Confirm or reuse its task contract before acting.

Do not change `state/`, `records/`, `sources/`, `views/`, `index/`, or `packages/archive/`. Keep pending exploration notes under `work/explorations/`; put reusable candidate tools under `work/candidate-tools/`. Work on ordinary project artifacts only when the contract permits it.

Record:

- tools and skills inspected;
- why an existing tool was reused, adapted, or not useful;
- candidate tools created and how they were tested;
- findings and supporting evidence;
- failed attempts and conditions under which they failed;
- open questions and possible next tasks.

A failed direction is worth proposing as a formal `attempt` only when it records what was tried, why it failed, failure conditions, retry conditions, and minimal reproduction or key evidence. Leave ordinary logs, caches, duplicate output, and meaningless intermediate files out of formal proposals.

Package when the user requests handoff, when material progress changes the next decision, or before remaining context becomes unsafe for a complete handoff.

## Create a handoff draft

Use the schema in `references/handoff-schema.json`. `proposed_changes` are proposals only. Every proposal needs a stable `change_id`, an operation, a target, a reason, and the proposed value.

Export a single file:

```bash
python scripts/handoff.py export \
  --project-skill /absolute/project/.agents/skills/example-project \
  --handoff /absolute/path/handoff-draft.json \
  --output /absolute/path/task-name.llmpack
```

Add artifacts with repeated `--artifact SOURCE=artifacts/RELATIVE_PATH` arguments. Symlinks and non-regular files are rejected. Do not include the private machine profile or credentials.

The current package schema limits each entry to 256 MiB, the total uncompressed payload to 512 MiB, and the payload to 1,000 entries. Split larger evidence outside the package and include an accepted reference instead.

Run `verify` on the completed package and report its path, package ID, base revision, and SHA-256 digest. The package provides integrity, not sender authenticity.

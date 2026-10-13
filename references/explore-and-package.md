# Explore and package

## Start exploration

Read the generated project's `SKILL.md` and directly loaded `views/project-map.json`. Select a confirmed high-priority task unless the user explicitly chooses otherwise. Read only the formal records referenced by the selected node when more detail is needed. Confirm or reuse its task contract before acting.

If this project has an accepted research content tree, follow the task's reference to its tree artifact and relevant node IDs; read only those nodes and authorized evidence or source metadata needed for the task. Check their dependencies, evidence gaps, and outstanding questions. The tree informs exploration and later task proposals but never creates or reprioritizes a task by itself. A project without a research tree follows the ordinary task route.

When choosing **future** research work, begin with the accepted tree's unresolved nodes and evidence gaps, then derive candidate tasks. The current task map identifies already confirmed work; it does not determine the research structure. User acceptance is the boundary between a candidate from the tree and a task on the board/map.

Do not change `state/`, `records/`, `sources/`, `views/`, `index/`, or `packages/archive/`. Keep pending exploration notes under `work/explorations/`; put reusable candidate tools under `work/candidate-tools/`. Work on ordinary project artifacts only when the contract permits it.

Record:

- tools and skills inspected;
- why an existing tool was reused, adapted, or not useful;
- candidate tools created and how they were tested;
- findings and supporting evidence;
- failed attempts and conditions under which they failed;
- open questions and possible next tasks.

For a project using a research tree, also record proposed tree-node additions or revisions, evidence and counter-evidence references, changed gaps, and the reason for each change. Keep them pending in `work/`. For each possible next task, identify the tree artifact and node IDs it would advance, the specific gap and dependencies, the expected verifiable output or acceptance evidence, and how the tree should be reviewed after the task. One task may address several nodes, and one gap may yield several task candidates. Do not equate a completed task with a resolved research question.

A failed direction is worth proposing as a formal `attempt` only when it records what was tried, why it failed, failure conditions, retry conditions, and minimal reproduction or key evidence. Leave ordinary logs, caches, duplicate output, and meaningless intermediate files out of formal proposals.

Package when the user requests handoff, when material progress changes the next decision, or before remaining context becomes unsafe for a complete handoff.

## Create a handoff draft

Use the schema in `references/handoff-schema.json`. `proposed_changes` are proposals only. Every proposal needs a stable `change_id`, an operation, a target, a reason, and the proposed value.

Prepare a preview first:

```bash
python scripts/handoff.py preview \
  --project-skill /absolute/project/.agents/skills/example-project \
  --handoff /absolute/path/handoff-draft.json \
  --output /absolute/path/task-name.llmpack
```

Add artifacts with repeated `--artifact SOURCE=artifacts/RELATIVE_PATH` arguments. The preview shows the bound project, task, revision, destination, source and archive paths, sizes, hashes, exclusions, and no-upload boundary. It does not create the final package.

Show the concise preview to the user. After one approval of that exact preview, run the same arguments with `export` and add the returned preview hash:

```bash
python scripts/handoff.py export \
  --project-skill /absolute/project/.agents/skills/example-project \
  --handoff /absolute/path/handoff-draft.json \
  --output /absolute/path/task-name.llmpack \
  --approved-preview-sha256 <preview_sha256>
```

The exporter refuses a missing or stale approval hash. Symlinks and non-regular files are rejected. Do not include the private machine profile or credentials. Package approval authorizes local creation only; it does not accept any proposed change during later integration.

The current package schema limits each entry to 256 MiB, the total uncompressed payload to 512 MiB, and the payload to 1,000 entries. Split larger evidence outside the package and include an accepted reference instead.

Run `verify` on the completed package and report its path, package ID, base revision, and SHA-256 digest. The package provides integrity, not sender authenticity.

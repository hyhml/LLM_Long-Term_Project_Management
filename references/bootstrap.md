# Project bootstrap

Use this procedure only when creating a new project-local skill.

## Gather a proposal

Resolve the project root first. Do not write files until the user accepts the proposal.

Gather and show:

- project name and a lowercase, hyphenated skill name;
- project goal and explicit non-goals;
- project-level completion criteria;
- initial formal records and typed relations from which the project map will be generated;
- initial high- and low-priority tasks;
- whether existing project files should be represented in the map;
- the proposed destination: `<project-root>/.agents/skills/<skill-name>/`.

Use stable IDs. Prefer `goal-*`, `task-*`, `decision-*`, `idea-*`, `attempt-*`, `evidence-*`, `artifact-*`, `question-*`, and `risk-*` prefixes. Supported relation types are `contains`, `depends_on`, `causes`, `supports`, `contradicts`, `tests`, `produces`, `supersedes`, `blocks`, and `derived_from`.

## Create after confirmation

Run:

```bash
python scripts/init_project.py \
  --project-root /absolute/project/path \
  --skill-name example-project \
  --project-name "Example project" \
  --goal "Confirmed project goal" \
  --criterion "First confirmed completion criterion" \
  --high-task "First high-priority task" \
  --low-task "First low-priority task"
```

Repeat `--criterion`, `--high-task`, and `--low-task` as needed. The initializer refuses an existing destination; do not bypass that refusal without a separate user-approved migration plan.

Then run:

```bash
python scripts/validate_project.py /absolute/project/path/.agents/skills/example-project
```

The generated layout separates authority and pending work:

```text
records/   accepted records and typed relations; formal authority
work/      explorations and candidate tools; not yet accepted
views/     generated, directly loaded navigation
packages/  handoffs and integration receipts
```

`views/project-map.json` is generated from `records/store.json`. Do not edit it to change project state. Report the created path, validation result, initial revision, and the explicit invocation name. Do not claim that the project is initialized if validation fails.

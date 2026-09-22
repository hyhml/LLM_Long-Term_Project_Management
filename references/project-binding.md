# Project binding and conversation isolation

Use this protocol whenever a child project is invoked or a tool resolves a project root.

## Inspect the instance

```bash
python scripts/project_binding.py inspect \
  --project-skill /absolute/project/.agents/skills/example-project
```

The result binds the canonical child root, immutable `project_id`, project revision, entry protocol, data schemas, and framework-managed adapter hashes. `compatible` permits ordinary formal work. `upgrade-required` and `migration-required` permit read-only inspection; `ambiguous` and `invalid` fail closed.

All project tools receive an explicit `--project-skill` or project-root argument. A current directory, display name, or conversation subject is not write authority. Never persist a global authoritative current-project selector.

## Bind the conversation

For the first child in an ordinary conversation:

```bash
python scripts/project_binding.py session-check \
  --project-skill /absolute/project/.agents/skills/example-project
```

For a later invocation, pass the already active identity:

```bash
python scripts/project_binding.py session-check \
  --active-project-id proj-existing-id \
  --project-skill /absolute/other/.agents/skills/other-project
```

`switch-confirmation-required` blocks ordinary project work until the user explicitly switches. Prefer a new conversation because an authority switch cannot erase earlier model context. Before formal writes, handoff export, integration, or migration, state the bound project name and ID.

Keep unrelated projects under separate project roots when practical. Multiple children under one `.agents/skills/` directory are supported only when identities and invocation are unambiguous; duplicate project IDs fail closed.

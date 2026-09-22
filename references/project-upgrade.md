# Child adapter compatibility and upgrade

Framework adapter updates and project-data migrations are separate authorities. Never rewrite project records, sources, tasks, work, packages, artifacts, or `project-instructions.md` as an incidental effect of updating the total skill.

## Inspect and propose

```bash
python scripts/upgrade_project.py inspect \
  --project-skill /absolute/project/.agents/skills/example-project

python scripts/upgrade_project.py propose \
  --project-skill /absolute/project/.agents/skills/example-project \
  --output /outside/the/project/upgrade-plan.json
```

Keep the proposal outside the child while it is pending so it does not change the plan's preserved-project digest. Present every `changes` item and obtain one `accepted`, `rejected`, or `deferred` decision. Required adapter changes must all be accepted before application.

## Apply and verify

```bash
python scripts/upgrade_project.py apply \
  --project-skill /absolute/project/.agents/skills/example-project \
  --plan /outside/the/project/upgrade-plan.json \
  --decisions /outside/the/project/upgrade-decisions.json \
  --operation-id thin-adapter-upgrade

python scripts/upgrade_project.py verify \
  --project-skill /absolute/project/.agents/skills/example-project
```

The upgrader rejects stale identity, revision, framework, adapter-hash, or project-data preconditions. It builds and validates a complete candidate, archives the previous adapter, swaps the candidate into place, restores the old child on an in-process validation failure, and writes a framework-upgrade receipt without advancing the project revision.

The v0.5.0 adapter upgrade retains v0.4.0 project-data schemas, so no data migration occurs. If inspection reports `migration-required`, stop and create a separate itemized data-migration proposal. Do not use the adapter upgrader to bypass that boundary.

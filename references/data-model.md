# Formal project data model

Use the existing generated files as the concrete schema examples. Keep the same `project_id` and project revision across all formal components.

## Project instance and ownership

`framework/instance.json` uses `ltpm-project-instance/v1`. It binds the immutable project ID and child skill name to the manager skill, entry protocol, framework release lineage, supported project-data schemas, and hashes of framework-managed adapter files.

`SKILL.md`, `agents/openai.yaml`, and `framework/instance.json` are framework-managed adapter files. `project-instructions.md` and all project data directories are project-owned. Adapter refreshes must preserve project-owned files and do not advance the project revision. A future project-data schema migration is a separate accepted transaction.

## Project and tasks

`state/project.json` owns the canonical revision, stable objective contract, and current focus. Its objective contract contains `objective_id`, `objective_revision`, `objective`, `scope`, `non_goals`, `assumptions`, `evidence_standard`, and `completion_standard`.

A non-null `current_focus.task_contract` uses `ltpm-task-contract/v1`. Besides expected result, scope, non-goals, acceptance evidence, allowed side effects, and stop condition, it contains:

- `classification`: `layer: data`, `data_subtype: project`, and the audience;
- `control_plan`: write authority, allowed storage targets, validation route, version route, and release boundary.

Framework or external regression/evaluation work is not stored as a project task contract; route it to its own authority boundary.

`state/task-board.json` owns task scheduling priority and lifecycle status. It has exactly `high` and `low` lists: high is foreground/current scheduling and low is background/later scheduling. Each entry contains a `task_id` pointing to a formal task record and a status of `pending`, `active`, `blocked`, or `done`. This is separate from framework load priority and from objective/milestone/task relations. A required later milestone does not become low priority merely because it is temporally distant.

## Records and relations

`records/store.json` contains accepted record objects and typed relations. A record requires:

```json
{
  "id": "claim-001",
  "kind": "claim",
  "title": "Short navigation title",
  "confirmation_status": "accepted",
  "content": {}
}
```

Universal kinds are `task`, `claim`, `evidence`, `attempt`, `review`, `decision`, `question`, `artifact`, and `risk`. Domain extensions use `namespace:kind`; do not redefine a universal kind.

A failed attempt has `content.outcome: "failed"` and non-empty `attempted`, `failure_reason`, `failure_conditions`, `retry_conditions`, and `evidence_or_reproduction` fields.

A relation requires stable `id`, `from`, `type`, `to`, and `confirmation_status: "accepted"`. Its endpoints may be the objective, a formal record, or a registered source. Generic types are `contains`, `depends_on`, `causes`, `supports`, `contradicts`, `tests`, `produces`, `supersedes`, `blocks`, `derived_from`, `evaluates`, `decides`, and `cites`; domain extensions use `namespace:type`.

## Sources

`sources/registry.json` records accepted source metadata, not necessarily source bodies. Each source needs `source_id`, `source_type`, `title`, `access_scope`, and `confirmation_status: "accepted"`. Add location, provenance, version/retrieval time, content hash, and coverage details when available and appropriate. Never place credentials in the registry.

## Derived data

`views/project-map.json` is generated from the formal files. `index/manifest.json` reports index status and coverage. Edit neither as project authority.

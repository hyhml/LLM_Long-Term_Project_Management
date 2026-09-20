# Formal project data model

Use the existing generated files as the concrete schema examples. Keep the same `project_id` and project revision across all formal components.

## Project and tasks

`state/project.json` owns the canonical revision, stable objective contract, and current focus. Its objective contract contains `objective_id`, `objective_revision`, `objective`, `scope`, `non_goals`, `assumptions`, `evidence_standard`, and `completion_standard`.

`state/task-board.json` owns task priority and lifecycle status. It has exactly `high` and `low` lists; each entry contains a `task_id` pointing to a formal task record and a status of `pending`, `active`, `blocked`, or `done`.

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

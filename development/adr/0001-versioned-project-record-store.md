# ADR-0001: Versioned project record store and derived project map

- Status: Proposed
- Date: 2026-09-20
- Scope: Framework data storage and cross-conversation project continuity
- Distribution: Development branch only; not part of the runtime skill on `main`
- Runtime effect: None until this ADR is accepted and implemented

## Relationship to ADR-0002

ADR-0002 separately accepts and implements two narrower decisions: formal records are authoritative while the project map is derived, and pending work is separated from accepted records. It uses one mutable, revisioned `records/store.json` suitable for projects with tens of nodes. The content-addressed objects, immutable snapshots, atomic `HEAD`, migration protocol, and parallel conflict model described below remain proposed.

## Context

The current v0.1 project template stores authoritative mutable state in `state/project-map.json` and `state/current-focus.json`. That is sufficient for an initial single-maintainer workflow, but it combines several concerns:

- durable project facts;
- current task selection;
- relationships among ideas, attempts, decisions, files, and tasks;
- a compact view loaded by the model;
- a merge target for imported handoff proposals.

This coupling makes historical reconstruction, conflict detection, parallel exploration, rollback, and schema migration harder. A map optimized for model orientation is also not necessarily the best canonical storage format.

The framework must remain lightweight and domain-neutral. A project may concern mathematics, politics, chemistry, engineering, writing, or another subject. Different domains use different evidence standards, but they share the need to preserve user intent, attempted directions, accepted decisions, sources, tools, and cross-conversation continuity.

## Decision under consideration

Adopt a lightweight revisioned record store as the authoritative project state. Treat the project map, task board, indexes, summaries, and human-readable navigation as derived views of one immutable project snapshot.

The logical flow becomes:

```text
pending work
  -> itemized proposal
  -> user decisions
  -> immutable record/relation revisions
  -> immutable project snapshot
  -> atomic HEAD update
  -> derived project map and indexes
  -> commit receipt
```

This is a proposed data contract, not an instruction to migrate the current implementation yet.

## High-priority invariants

These invariants are candidates for the framework's directly loaded rules if the ADR is accepted.

1. Formal records and relations are authoritative; maps and indexes are derived.
2. Pending exploration material stays outside the formal store until the user accepts it.
3. A stable identity and a content revision are different things.
4. Every formal commit binds one exact base snapshot and produces one new snapshot.
5. `HEAD` changes only after all accepted objects and the candidate snapshot validate.
6. Handoff packages contain proposals and evidence, not authority to change project state.
7. Imported reviews, summaries, and claims retain their provenance and do not become trusted merely because package integrity succeeds.
8. Task priority, ownership authority, evidence status, lifecycle status, and freshness are separate dimensions.
9. Private machine profiles never enter the project store or handoff packages.
10. Existing bytes and user-confirmed history are preserved during migration; missing meaning is not invented.

## Version identifiers

Do not use one number for every kind of change.

| Identifier | Meaning | Changes when |
|---|---|---|
| `framework_version` | Version of the framework code and protocols | Framework behavior is released |
| `schema_version` | Shape and interpretation of a stored object | A storage schema changes incompatibly |
| `record_revision` | SHA-256 identity of one canonical record or relation revision | Its canonical content changes |
| `snapshot_id` | SHA-256 identity of one canonical project snapshot | The selected formal project state changes |
| `project_revision` | Monotonic human-facing commit counter | A formal project commit succeeds |
| `package_schema_version` | Format of a `.llmpack` handoff | Package compatibility changes |

`project_revision` is convenient for people but is not a concurrency token. `snapshot_id` is the exact base for conflict detection.

## Authority dimensions

A single global priority would conflate unrelated questions. Store these dimensions independently:

- `task_priority`: `high` or `low`;
- `ownership_authority`: who may decide the content, such as `user`, `external-source`, `tool`, or `ai`;
- `confirmation_status`: `proposed`, `accepted`, `rejected`, `deferred`, or `withdrawn`;
- `evidence_status`: a domain-neutral baseline such as `unverified`, `reported`, `supported`, `verified`, `disputed`, or `refuted`;
- `freshness`: the exact source revision, retrieval time, or coverage statement from which a derived view was produced.

User-confirmed notes are authoritative for the user's intent and project decisions. That does not automatically make them the strongest evidence for an external factual claim. Domain-specific child skills may refine evidence statuses, but must not silently redefine ownership or confirmation.

## Formal objects

### Record revision

A record represents one durable project item. Candidate baseline kinds are:

```text
objective, task, idea, question, attempt, finding,
decision, source, evidence, artifact, risk, correction
```

The proposed canonical shape is:

```json
{
  "schema": "ltpm-record/v1",
  "project_id": "proj-...",
  "record_id": "task-001",
  "kind": "task",
  "previous": null,
  "title": "Example",
  "content": {},
  "ownership_authority": "user",
  "confirmation_status": "accepted",
  "evidence_status": "unverified",
  "sources": [],
  "created_at": "RFC-3339 timestamp"
}
```

The canonical JSON bytes do not contain their own `record_revision`; their SHA-256 becomes the revision and storage address. Updating an item creates another revision with `previous` pointing to the prior revision. It does not overwrite the old bytes.

Task priority and status live in the task record's `content`. Changing either creates a new task revision after user confirmation.

### Relation revision

Relations are formal objects rather than lines maintained only in a visualization.

```json
{
  "schema": "ltpm-relation/v1",
  "project_id": "proj-...",
  "relation_id": "relation-001",
  "previous": null,
  "from": {"record_id": "attempt-001", "revision": "sha256-or-null"},
  "to": {"record_id": "idea-001", "revision": "sha256-or-null"},
  "binding": "identity",
  "type": "tests",
  "reason": "What this attempt was intended to test",
  "ownership_authority": "user",
  "confirmation_status": "accepted"
}
```

`binding: identity` follows the selected revision of a stable item. `binding: revision` requires exact endpoint revisions and is appropriate when the relationship would become false after either item's content changed.

Candidate generic relation types remain:

```text
contains, depends_on, causes, supports, contradicts,
tests, produces, supersedes, blocks, derived_from,
extends, corrects
```

Domain-specific relation vocabularies require an explicit schema extension rather than an unrecorded synonym.

### Project snapshot

A snapshot selects the complete formal state without duplicating record bodies:

```json
{
  "schema": "ltpm-snapshot/v1",
  "project_id": "proj-...",
  "project_revision": 12,
  "parent": "prior-snapshot-sha256",
  "objective": {"record_id": "objective-001", "revision": "sha256"},
  "selected_records": {"task-001": "sha256"},
  "selected_relations": {"relation-001": "sha256"},
  "operation_id": "operation-...",
  "created_at": "RFC-3339 timestamp"
}
```

The canonical snapshot bytes produce `snapshot_id`. `HEAD` contains only the current snapshot ID plus a newline and is replaced atomically.

Branches created by future parallel exploration may use more than one parent in a later snapshot schema. Version 1 keeps one parent and detects stale bases without attempting automatic merges.

## Physical project layout

The proposed logical layout is:

```text
.agents/skills/<project-skill>/
├── SKILL.md
├── framework/
├── data/
│   ├── project.json
│   ├── HEAD
│   ├── objects/sha256/
│   ├── snapshots/
│   ├── operations/
│   └── receipts/
├── work/
│   ├── explorations/
│   └── candidate-tools/
├── views/
│   ├── project-map.json
│   └── current-focus.json
├── index/
└── packages/
    ├── inbox/
    ├── outbox/
    └── archive/
```

Responsibilities:

- `data/` is formal authority and is changed only by validated commit operations.
- `work/` contains pending material and may be edited during exploration.
- `views/` is regenerated from one stated snapshot and can be rebuilt.
- `index/` is disposable acceleration state and can be rebuilt.
- `packages/` stores transport artifacts and integration receipts; package presence does not make its contents formal project state.

Whether `objects/` uses two-character hash fan-out and whether snapshots also live in the object store are physical implementation details to settle before acceptance.

## Commit protocol

An accepted batch follows this sequence:

1. Read and retain the current `snapshot_id` as `base_snapshot_id`.
2. Build itemized proposals without modifying formal state.
3. Record the user's decision for every proposal.
4. Freeze accepted canonical record and relation bytes.
5. Acquire the project write lock.
6. Verify that `HEAD` still equals `base_snapshot_id`.
7. Write missing immutable objects without replacing existing objects.
8. Write and validate the candidate snapshot.
9. Atomically replace `HEAD` with the candidate `snapshot_id`.
10. Generate derived views and a receipt containing the old and new snapshot IDs, accepted/rejected/deferred items, validation outcome, and tool-retention decisions.

If the process stops before step 9, formal state remains at the old `HEAD`; created unreferenced objects may be recovered or garbage-collected later. If it stops after step 9, the commit is authoritative even if view generation or response delivery failed. Recovery inspects the operation ID and `HEAD` before retrying.

## Handoff and conflict behavior

Every `.llmpack` binds:

- `project_id`;
- `base_snapshot_id`;
- `base_project_revision` for display;
- framework and package schema versions;
- proposed records, relations, tasks, and artifacts;
- per-entry hashes.

Import verifies bytes and compatibility, then creates itemized proposals. It never installs formal records directly.

If current `HEAD` differs from `base_snapshot_id`, the package is stale. Version 1 must display the conflict and require user-reviewed rebasing. It must not guess that different record IDs are independent. This creates the data boundary needed for later parallel exploration without claiming that parallel merging is implemented.

## Derived project map

`views/project-map.json` is a compact, directly loaded view of one `snapshot_id`. It contains:

- project identity and objective summary;
- current high- and low-priority tasks;
- selected node summaries;
- selected typed relations;
- pointers to exact records and source entries;
- unresolved conflicts and coverage gaps;
- the source snapshot and generation version.

The view must never contain a node, relation, or status that cannot be traced to the selected formal objects. Deleting it does not delete project history; regenerating it from the same snapshot must be deterministic apart from explicitly excluded presentation timestamps.

## Index and retrieval boundary

An index accelerates discovery but does not own project meaning. Search results must report:

- index snapshot;
- indexed scope and known exclusions;
- matched record IDs and revisions;
- truncation or coverage gaps.

An empty result means only “not found in the declared indexed scope.” Exact content and current status come from the selected formal record revision, not from a stale index copy.

Version 1 may use a small generated JSON index or direct bounded scanning. SQLite, embeddings, and remote indexing are not required for projects with tens of nodes.

## Migration from v0.1

No migration occurs while this ADR is proposed.

If accepted, migration must:

1. freeze and hash the original `project-map.json`, `current-focus.json`, database index, and referenced records;
2. produce a preview mapping every existing node, relation, task, and database reference to proposed formal objects;
3. mark ambiguities instead of inventing missing provenance or evidence status;
4. require user acceptance of the mapping;
5. create an initial immutable snapshot and migration receipt;
6. retain the original files as referenced migration evidence until the user separately authorizes cleanup;
7. prove that task priorities, completion criteria, relationships, and record pointers remain represented.

The migration must be idempotent by operation ID and must not modify a project whose current state changed after preview.

## Consequences

### Benefits

- Cross-conversation recovery no longer depends on one mutable summary file.
- History, corrections, and failed directions remain addressable.
- Exact snapshot IDs provide a clean future boundary for parallel exploration.
- Maps and indexes can evolve without rewriting project history.
- Imports, retries, and crashes have explicit recovery semantics.
- The same storage core can serve different subject domains.

### Costs

- More files and concepts than a mutable JSON map.
- A commit and recovery tool becomes mandatory for formal-state changes.
- Human inspection needs generated views because hashes are not friendly navigation.
- Garbage collection, migration, and schema compatibility need explicit policies.
- Domain-neutral evidence statuses may be too weak for specialized projects and require controlled extensions.

## Alternatives considered

### Keep `project-map.json` authoritative

Simplest for the first prototype, but weak for exact history, conflict detection, rollback, and parallel work. Acceptable only while the project remains small and single-writer.

### Use one mutable SQLite database

Provides transactions and queries, but is less transparent in version control and portable handoff. It also risks making the index and authority store the same thing. SQLite may still be used as a derived index.

### Use an append-only event log

Provides a complete audit trail, but every view depends on replay semantics and event-version migration. Debugging long histories is harder. Immutable selected revisions plus snapshots give a simpler read model for this scale.

### Copy the complete MRS content-addressed architecture

Strong but too heavy for the intended lightweight, domain-neutral framework. This proposal borrows the authority, snapshot, provenance, and recovery principles without its mathematical review system, complete exchange machinery, or large-project conformity audits.

## Acceptance questions for the next discussion

Before changing status to Accepted, decide:

1. Which record kinds and relation types belong to the universal core, and which are domain extensions?
2. Should `ownership_authority` and `evidence_status` use fixed enums, namespaced extensions, or both?
3. Are content-addressed individual objects justified for projects with only tens of nodes, or should the first physical implementation use an append-only JSONL store with snapshot hashes?
4. Which information must always be included in the directly loaded map?
5. How should a user revise the project objective without silently replacing the project?
6. What constitutes an accepted review outside mathematics?
7. How much of the commit protocol must be enforced by scripts rather than instructions?
8. Which v0.1 projects, if any, need a migration path before the new format becomes default?

## Acceptance tests if implemented

- Regenerating the map twice from one snapshot produces identical semantic content.
- A stale `base_snapshot_id` cannot update `HEAD`.
- A crash before `HEAD` replacement leaves the prior project readable.
- A crash after `HEAD` replacement is recognized as committed and is not repeated.
- Pending work never appears in formal views without an accepted commit.
- A tampered object, snapshot, package, or receipt is rejected.
- A v0.1 migration preview accounts for every node, relation, task, and referenced database record.
- Imported claims retain provenance and do not silently acquire user-confirmed or verified status.

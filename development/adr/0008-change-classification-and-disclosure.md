# ADR-0008: Two-axis change classification and dialogue disclosure

- Status: Accepted
- Date: 2026-09-20
- Implemented in: `0.3.0-dev.2`

## Context

The framework manages both concrete project state and its own reusable behavior. It also contains material for runtime users and separate material for framework developers. Without explicit classification, a conversation can accidentally treat a schema proposal as project data, modify framework files during ordinary project work, claim a development-only ADR is installed behavior, or imply that a new template migrated existing child projects.

The subject of a change is not a reliable classifier. A change about “data storage” can be a framework schema change; use of a framework script can still produce only project-data changes.

## Decision

Classify every substantive managed request on two independent axes before work begins.

### Change layer

- `project-data`: changes one concrete project's data, pending work, candidate tools, or authorized artifacts;
- `framework`: changes reusable rules, schemas, templates, scripts, protocols, ADRs, backlog, or framework version;
- `mixed`: changes both and must be split into separately governed parts;
- `none/read-only`: changes neither authority.

Classification follows the authority actually changed, not the topic, file format, or tool used.

### Audience

- `runtime-user`: consumed by released-skill users or a concrete project's users;
- `developer`: development-only ADRs, tests, diagnostics, migration design, and maintainer material;
- `both`: has distinct runtime and developer effects that must be reported separately.

Audience follows who consumes the result and how it is distributed, not the filename.

## Dialogue behavior

At the first substantive progress update, disclose:

1. change layer;
2. audience;
3. write and release boundary, such as project revision, `development`, `main`, or no write.

Keep the disclosure compact for obvious cases. Explain and split mixed or ambiguous work. If classification changes during execution, disclose the new boundary before crossing it.

The final handoff repeats the classification for material changes and says where each part was written, versioned, and released.

## Boundary consequences

- Project-data writes use the project proposal/transaction/revision protocol and never edit framework rules.
- Framework writes require explicit development mode, framework versioning, ADR/version notes when material, and framework validation; they never silently mutate accepted project data.
- Developer-only files are excluded from runtime claims and distribution.
- Runtime framework changes affect newly generated or explicitly migrated child skills; they do not imply existing child projects were migrated.

## Enforcement and limits

The classification requirement is directly loaded in the total skill, framework map, and generated child-skill template. Detailed examples are conditionally loaded only for mixed or ambiguous cases.

Classification is a reasoning and dialogue gate, not a deterministic content classifier. The framework can validate locations and versions after the decision, but the model and user remain responsible for correcting a mistaken classification.

## Subsequent refinement

ADR-0009 retains these independent layer and audience axes, adds data subtypes, and replaces the opening-only gate with a continuous control loop. Classification now determines authority, storage, validation, versioning, and release handling throughout the work rather than serving only as dialogue disclosure.

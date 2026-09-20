# ADR-0009: Classification-driven continuous control

- Status: Accepted
- Date: 2026-09-20
- Implemented in: `0.4.0-dev.1`

## Context

ADR-0008 required classification before substantive work, but a single opening label cannot control a request that later branches, creates a tool, introduces a data source, changes its audience, or crosses a persistence or release boundary. It also grouped all data changes together even though project facts, regression cases, evaluation gold data, machine information, and private user material have different authorities and storage rules.

The assistant, rather than the user, should notice and decompose these changes. Requiring the user to repeatedly classify their own request would move the framework's control responsibility onto the user.

## Decision

Treat classification as a continuously maintained control input for every material work item.

Each item has:

- a layer: `framework`, `data`, `mixed`, or `none/read-only`;
- for data, a subtype: `project`, `regression`, `evaluation`, `environment`, or `private-user`;
- an audience: `runtime-user`, `developer`, or `both`.

From that classification, derive a control plan containing:

- write authority;
- permitted storage targets;
- validation route;
- version route;
- release boundary.

Re-evaluate the classification when work branches or before persistence, packaging, publication, release, and final handoff. Split mixed work into separately governed items before writing. Ask the user only when ambiguity would materially change authority, persistence, or release.

A non-null formal project task contract records a `data:project` classification and its control plan. Project validation rejects another layer or subtype in this location. Framework development, real regression cases, evaluation data, machine profiles, and private material use their own authority and storage boundaries rather than being embedded in project task state.

## Dialogue behavior

At the first substantive update, report the active work classes and their write/release boundaries compactly. Later updates report only material reclassifications. The final handoff reconciles planned and actual storage, validation, version, and release handling.

## Consequences

Classification becomes project control rather than an introductory label. The task-contract schema and generated map schema advance because the project view can now carry the operational classification and control plan. Existing child projects are not automatically migrated.

The framework still cannot deterministically infer semantic classification. The assistant owns the initial reasoning, the user can correct it, and validators enforce only the parts represented in structured state.

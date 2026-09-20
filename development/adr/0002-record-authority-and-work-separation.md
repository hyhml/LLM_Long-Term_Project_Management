# ADR-0002: Formal records as authority and separation of pending work

- Status: Accepted
- Date: 2026-09-20
- Scope: Lightweight project-local storage for projects with tens of nodes
- Distribution: Development branch only; not part of the runtime skill on `main`
- Implemented in: `0.2.0-dev.1`

## Context

The v0.1 design made `state/project-map.json` authoritative. That gave every conversation one convenient file, but mixed durable facts with a navigation format. A future change to map layout, filtering, or visualization could then look like a change to project truth.

Exploration output also needs a clear trust boundary. Findings, candidate tools, and attempted directions are useful before confirmation, but must not silently enter the project's accepted memory. The framework already requires two-phase integration—proposal followed by user-confirmed commit—so the directory model should enforce the same boundary.

## Decision

For the lightweight implementation, use this project-local layout:

```text
.agents/skills/<project-skill>/
├── records/
│   ├── store.json
│   └── materials/
├── work/
│   ├── explorations/
│   └── candidate-tools/
├── views/
│   └── project-map.json
└── packages/
    ├── inbox/
    ├── outbox/
    └── archive/
```

The rules are:

1. `records/store.json` contains the accepted records, typed relations, current focus, and monotonic project revision. It is the formal authority.
2. `records/materials/` contains accepted detailed material addressed from formal records.
3. `views/project-map.json` is a compact, directly loaded navigation view generated deterministically from `records/store.json`. It may point to formal records but cannot create or override them.
4. `work/explorations/` contains current exploration, attempts, and unconfirmed findings. `work/candidate-tools/` contains reusable tools awaiting a retention decision. Neither directory is formal project state.
5. `packages/` contains transport files and integration receipts. A valid package proves payload integrity, not acceptance or authority.
6. Explorer sessions may write authorized project artifacts and `work/`, but never `records/`, `views/`, or archived decisions.
7. Maintainer/integrator sessions present itemized proposals. Only accepted items are written to `records/`; one accepted batch increments the revision once, regenerates the map, and passes validation.
8. A user may revise accepted records later through another proposal and commit. “Authoritative” means the current accepted state, not immutable or infallible truth.

## Version design

This decision introduces three distinct identifiers:

- framework version `0.2.0-dev.1`: behavior and project template changed;
- record-store schema `ltpm-record-store/v1`: authoritative store structure;
- map-view schema `ltpm-project-map-view/v1`: derived navigation structure.

The existing `.llmpack` schema remains version 1. Its `base_revision` now refers to `records/store.json.revision`.

Existing v0.1 child skills are not modified automatically. A migration design must preserve their confirmed facts and is outside this decision.

## Enforcement

- `scripts/init_project.py` creates the separated layout and formal store.
- `scripts/render_project_views.py` is the only framework generator for the map view.
- `scripts/validate_project.py` rebuilds the expected view and rejects stale or manually edited maps.
- `scripts/handoff.py` binds exports to the formal store's project ID and revision.
- The total skill and generated child skill both state the explorer and integrator write boundaries.

## Consequences

Benefits:

- map presentation can evolve without redefining project facts;
- unconfirmed exploration has an explicit home and cannot enter the loaded map through normal generation;
- proposal and commit correspond to a real storage boundary;
- the format stays inspectable and small enough for the intended project scale.

Costs:

- every formal change must regenerate and validate the view;
- the single mutable store does not yet provide immutable history or exact snapshot conflict tokens;
- older generated child skills need an explicit migration before adopting the new layout.

## Deliberate non-decisions

This ADR does not accept the content-addressed object store, immutable snapshots, atomic `HEAD`, automatic migration, parallel merge, or package signatures proposed in ADR-0001. Those remain separate future decisions.

## Acceptance tests

- A new child skill contains `records/`, `work/`, `views/`, and `packages/`, not the v0.1 state/database layout.
- Rendering the same formal store twice produces identical map bytes.
- Manually changing the derived map causes project validation to fail.
- Pending material in `work/` does not appear in the generated map.
- Handoff export uses the formal store's project ID and revision.

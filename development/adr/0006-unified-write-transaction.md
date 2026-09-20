# ADR-0006: Unified accepted-write transaction

- Status: Accepted
- Date: 2026-09-20
- Implemented in: `0.3.0-dev.1`

## Context

Task updates, exploration archival, package integration, tool decisions, relation changes, and source registration previously risked developing separate write rules. They all cross the same boundary from proposal to accepted project state.

## Decision

Every important project-management write uses one workflow transaction:

```text
read current revision
→ create stable itemized proposals
→ record every user decision
→ apply accepted items to an isolated candidate
→ validate the candidate
→ increment the project revision once
→ regenerate and validate derived state
→ publish
→ generate a receipt
```

The project revision lives in `state/project.json`; the task board, record store, and source registry declare the same revision. A commit receipt records the operation, old and new revisions, decisions, validation, and hashes of published management files.

## Enforcement

`scripts/project_transaction.py prepare` creates the candidate under `work/transactions/`. `commit` rejects stale bases, validates before and after the revision advance, marks the index stale, publishes the candidate, and writes a receipt. The tool validates the decision ledger but cannot semantically prove that every candidate edit implements one accepted proposal; the maintainer/integrator remains responsible for that review boundary.

The tool provides in-process rollback if publication fails. It is not crash-atomic and does not implement immutable snapshots or atomic `HEAD`; those stronger guarantees remain proposed in ADR-0001.

## Consequences

All management changes share one reviewable path and revision boundary. The cost is an explicit candidate and decision ledger for writes that were previously direct edits.

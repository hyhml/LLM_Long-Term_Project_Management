# ADR-0003: Stable project objective contract

- Status: Accepted
- Date: 2026-09-20
- Implemented in: `0.3.0-dev.1`

## Context

Long conversations can gradually replace the original problem without making that change visible. A mutable goal sentence is not enough to distinguish clarification from project substitution.

## Decision

Every project has a formal contract in `state/project.json` containing:

- stable `objective_id`;
- `objective` and `objective_revision`;
- `scope` and `non_goals`;
- explicit `assumptions`;
- domain-appropriate `evidence_standard`;
- observable `completion_standard`.

The objective may be clarified only through an itemized, accepted `revise-objective` transaction. Its identity remains unchanged and its objective revision increments exactly once. A materially different direction becomes a related formal node; if it requires a different contract, it becomes a new project.

## Enforcement and consequences

The initializer requires scope, evidence standard, and completion standard. Validation requires the complete contract. The transaction tool rejects objective-ID replacement and unapproved contract changes.

This prevents silent drift but requires users to make major scope changes explicit. It does not determine whether two goals are philosophically identical; that judgment remains with the user.

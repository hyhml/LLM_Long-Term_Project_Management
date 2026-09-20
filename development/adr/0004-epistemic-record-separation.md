# ADR-0004: Separate content, evidence, evaluation, and decision

- Status: Accepted
- Date: 2026-09-20
- Implemented in: `0.3.0-dev.1`

## Context

An AI-generated finding, successful command, cited source, review, and user decision answer different questions. Combining them in one generic “knowledge” entry makes unsupported conclusions appear accepted.

## Decision

The universal record core distinguishes at least:

- `claim`: an assertion or discovered possibility;
- `evidence`: material offered in support or contradiction;
- `attempt`: an action and observed outcome;
- `review`: an evaluation by a user, expert, model, or tool;
- `decision`: a user-accepted project choice.

Other core kinds include tasks, questions, artifacts, and risks. Domains may add namespaced kinds without redefining the universal meanings. Typed relations connect records, for example `supports`, `contradicts`, `tests`, `evaluates`, `decides`, and `cites`.

Tool execution success proves only that an operation completed under reported conditions. Package hashes prove only byte integrity. Neither establishes the truth, evidential strength, or user acceptance of a claim.

## Consequences

Formal records become more explicit and auditable, at the cost of several linked records where one vague note previously sufficed. Domain-specific evidence judgment remains governed by the project's `evidence_standard`.

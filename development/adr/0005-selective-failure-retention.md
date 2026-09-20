# ADR-0005: Selective retention of failed attempts

- Status: Accepted
- Date: 2026-09-20
- Implemented in: `0.3.0-dev.1`

## Context

Discarding every failure causes repeated work, while preserving all logs and intermediate output overwhelms retrieval and obscures useful knowledge.

## Decision

A failed `attempt` may enter formal records only when it preserves reusable information:

1. what was attempted;
2. why it failed;
3. the conditions under which it failed;
4. conditions that would justify retrying;
5. minimal reproduction or key evidence.

Routine logs, caches, duplicate output, raw tool chatter, and meaningless intermediate files remain in temporary or pending work and do not become formal records merely because they exist.

## Enforcement and consequences

The validator rejects formal failed attempts missing any required failure-context field and rejects transient record kinds such as `log`, `cache`, `raw-output`, and `temporary`.

This preserves negative knowledge without turning the project store into a dump. Borderline retention decisions remain itemized user choices.

# ADR-0017: Shared Markdown checks and authorized local repair reminders

- Status: Accepted
- Date: 2026-10-16
- Implemented in: `0.9.0-dev.1`
- Requirements: `TASK-005`, `TASK-006`, `ISOL-005`, `QUAL-005`

## Decision

User-approved shared runtime tools support Markdown math formatting, local file references, and review after three verified repair failures. Child skills call one installed copy; they do not fork the tools. Automated delimiter/path checks do not prove reader rendering, click behavior, scientific correctness, or full task acceptance.

For repair tracking, explicit user authorization permits local operator issue summaries under `private/problem-reminder/` in the installed total skill. This is a narrow exception to global statelessness: the store is not project knowledge, a task board, an active-project selector, a feedback package, or export permission. Fresh distributions contain no store and do not seed historical cases. No chat monitoring, network submission, or automatic tool creation is introduced.

Issue identity includes an acceptance criterion and relevant environment. Pending verification is not success; failure increments the current round; complete acceptance closes it; recurrence starts another round. Stable observation IDs prevent duplicate and concurrent retry counts. Three failures require diagnosis before further trial changes, not mandatory tool creation. Shell success and reminders are separate from acceptance.

Only generic tools, rules and safe synthetic tests enter development. Private records, real documents, conversations and machine profiles stay excluded from `main` and archives. Existing child entry protocol and project schemas are unchanged. The issue CLI currently requires Linux/WSL `fcntl`; the Markdown tools use Python standard libraries and do not operate a GUI.

## Validation

Feature tests cover read-only defaults, bounded/idempotent fixes, code-example exclusion, invalid-input nonmutation, repair lifecycle, isolation between issue identities, concurrent deduplication and malformed-store rejection. Existing core and exact-allowlist release gates remain binding. Distribution tests place only synthetic sentinel data in an excluded private directory and prove that no store is shipped. User-side GUI verification remains outside these deterministic gates.

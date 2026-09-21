# ADR-0012: Developer product requirements map

- Status: Accepted
- Date: 2026-09-21
- Runtime effect: None; developer governance only

## Context

The product's intent was distributed across conversation history, runtime rules, ADRs, backlog entries, and implementation files. Those artifacts answer different questions. A script can show that part of a workflow exists, while failing to show that the complete user-visible capability remains incomplete.

This caused child-skill generation to be treated as present because an initializer and template existed, while complete project-specification generation and post-framework-update child synchronization were not kept visible as separate primary requirements.

## Decision

Maintain `development/product-map.md` as the mandatory developer view of product intent, requirement classification, relationships, priority, status, evidence, gaps, and unresolved design questions.

The map is development-only and excluded from user releases. Developer `AGENTS.md` requires reading it before framework planning. Material framework work identifies affected requirement IDs. A user change to product intent, priority, scope, or acceptance conditions updates the map in the same development change.

The map distinguishes requirement status from implementation artifacts:

- a requirement says what outcome is expected;
- an ADR records an accepted design choice;
- implementation provides mechanisms;
- tests provide bounded evidence;
- releases record delivered runtime behavior.

No artifact alone proves an end-to-end requirement complete. Latest explicit user direction remains authoritative, and open mechanisms remain open questions rather than implicit decisions.

## Consequences

Framework development gains a directly loaded map comparable to the project maps generated for users. It adds maintenance work, but makes omissions, partial implementations, dependencies, and audience boundaries visible before changes begin. The runtime remains unchanged and does not pay a download or context cost.

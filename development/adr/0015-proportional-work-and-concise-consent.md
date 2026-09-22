# ADR-0015: Proportional framework work and concise consent

- Status: Accepted
- Date: 2026-09-22
- Target: `0.6.1`
- Runtime effect: Not yet implemented

## Context

Framework changes differ greatly in size and risk. Treating every design edit like an implementation or release adds duplicate documents and validation without improving the decision. Separately, v0.6.0 makes environment discovery and ordinary feedback authorization more cumbersome than the user needs.

## Decision

Use three work weights:

- **Design-only:** record the requirement and the smallest necessary decision; run static and boundary checks.
- **Runtime implementation:** add the smallest behavioral tests, implement, then run affected and core tests.
- **Release:** run the complete build, distribution, and remote publication gates.

Choose weight from side effects and risk, not from the `framework` label alone. Privacy, compatibility, migration, destructive actions, or changed public formats may escalate a task. Do not create a separate design document when the ADR and version plan already carry the decision.

For v0.6.1, preserve these user-visible rules:

1. Explain that environment discovery selects usable tools; after one permission, inspect the bounded tool/skill/model scope and privately save the result.
2. For `.llmpack`, a user request or automatic trigger may prepare a concise preview. One approval of that preview authorizes local package creation.
3. For `.ltpm-feedback`, authorized conversation context needs one final preview approval. Reading new private or external material first requires one additional bounded permission.
4. Package approval never accepts unpacked content into project authority; integration remains itemized.
5. The two package types retain different receivers and authority. Neither approval authorizes upload.
6. Framework load priority, task scheduling priority, and goal hierarchy remain separate concepts.

Keep existing project data, compatible children, `.llmpack` v1, and feedback v1 compatible. The implementation may choose the smallest reliable way to bind approval to previewed content; this ADR does not prescribe a CLI, intermediate schema, or file layout.

## Validation boundary

This design-only change needs JSON, document, and developer/runtime-boundary checks. Runtime tests are added when the behavior is implemented; full release gates run only when publishing.

## Consequences

The design remains auditable without repeating it across multiple specifications. Ordinary users normally make one meaningful packaging decision, while new private reads still require explicit authority. ADR-0015 supersedes only ADR-0014's rule that every feedback package requires two conversational consent gates.

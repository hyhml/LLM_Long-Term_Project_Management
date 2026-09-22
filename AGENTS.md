# Framework development

This file exists only on the development branch and must not enter a runtime release.

- Treat framework work as continuously classified control: separate runtime, developer, project, regression/evaluation, environment, and private-user authority before writing.
- Before planning any framework change, read `development/product-map.md`. Identify the affected requirement IDs, their relationships, current status, and user/developer boundary. Do not infer product completion from the presence of one script or template.
- Before changing framework behavior, read `development/adr/index.json` and the ADRs relevant to the change. Proposed ADRs are context, not accepted runtime rules.
- Scale the workflow to the change: design-only work uses the smallest decision records and static checks; runtime implementation adds affected tests and the core suite; release work uses the full release gate. Escalate when privacy, data migration, compatibility, or destructive effects justify it, not merely because the layer is `framework`.
- When the user adds, changes, reprioritizes, or rejects a product requirement, update the product map in the same development change. Preserve unresolved choices as open questions rather than silently selecting an implementation.
- For test changes, follow `development/policies/regression-testing.md`.
- For user distribution or `main` updates, follow `development/policies/runtime-release.md`; build from the exact runtime allowlist and never merge the development tree wholesale into `main`.
- Keep real regression cases, evaluation corpora, standard answers, project data, and private machine data outside this repository unless a separately accepted external-data design says otherwise.

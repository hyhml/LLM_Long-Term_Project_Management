# Framework development

This file exists only on the development branch and must not enter a runtime release.

- Treat framework work as continuously classified control: separate runtime, developer, project, regression/evaluation, environment, and private-user authority before writing.
- Before changing framework behavior, read `development/adr/index.json` and the ADRs relevant to the change. Proposed ADRs are context, not accepted runtime rules.
- For test changes, follow `development/policies/regression-testing.md`.
- For user distribution or `main` updates, follow `development/policies/runtime-release.md`; build from the exact runtime allowlist and never merge the development tree wholesale into `main`.
- Keep real regression cases, evaluation corpora, standard answers, project data, and private machine data outside this repository unless a separately accepted external-data design says otherwise.

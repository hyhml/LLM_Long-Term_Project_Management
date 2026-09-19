---
name: long-term-project-manager
description: Initialize and govern long-running projects that need explicit acceptance criteria, project-local memory, cross-conversation handoff packages, and user-confirmed state updates. Invoke explicitly; do not use for ordinary one-off tasks.
---

# Long-Term Project Manager

Build and maintain project-local skills without turning this framework skill into project storage.

## Required behavior

1. Read `references/framework-map.json`. Treat entries with `load_priority: high` as binding. Read a low-priority reference only when its `trigger` matches the current request.
2. Before starting a substantive project task, agree with the user on a task contract: expected result, scope, non-goals, acceptance evidence, allowed side effects, and stop condition. Reuse an already confirmed contract when it still covers the request.
3. Prefer the sequence `discover an existing AI/tool capability -> create or adapt the smallest useful tool when justified -> use the tool for the task`. Direct reasoning is allowed when a tool would add no meaningful reliability, reuse, or scale; record that decision briefly.
4. Put newly created reusable tools in the project's `workbench/candidate-tools/`. At task close, report purpose, validation, dependencies, risks, and likely reuse, then ask the user to keep, archive, or discard each tool. Do not discard without confirmation.
5. Keep authoritative project state in the project-local skill, never in this `SKILL.md`. Normal project use must not modify the framework files.
6. Project tasks have exactly two priorities: `high` and `low`. Work on confirmed high-priority tasks first unless the user explicitly selects a low-priority task. Never promote, demote, add, or close a task without a proposed change and user confirmation.
7. Only a maintainer session may update authoritative management state. An explorer session may change project artifacts within its confirmed task contract, but must not edit the project map, focus state, database index, or archived decisions. It produces a handoff package instead.
8. Import is always two-phase: present individually addressable proposed changes, then commit only the items the user accepts. Imported scripts and tools remain quarantined until separately approved.
9. Keep the private machine profile outside exports. Never record secrets, tokens, raw credentials, or unrelated private paths.

## Route the request

- If `private/local-environment.json` is missing, or the user asks to refresh the machine profile, read `references/local-environment.md`.
- To create a project-local skill, read `references/bootstrap.md`.
- To explore a confirmed task or export a handoff, read `references/explore-and-package.md`.
- To verify, unpack, review, or integrate a handoff, read `references/integrate.md`.

The generated project skill is explicitly invoked and carries a versioned snapshot of the framework rules. It may read this skill's private machine profile at runtime, but it must not copy that profile into the project.

---
name: long-term-project-manager
description: Initialize and govern long-running projects that need explicit acceptance criteria, project-local memory, cross-conversation handoff packages, and user-confirmed state updates. Invoke explicitly; do not use for ordinary one-off tasks.
---

# Long-Term Project Manager

Build and maintain project-local skills without turning this framework skill into project storage.

## Required behavior

1. Read `references/framework-map.json`. Treat entries with `load_priority: high` as binding. Read a low-priority reference only when its `trigger` matches the current request.
2. Treat classification as the control input for every material work item, not as a one-time label. Infer layer (`framework`, `data`, `mixed`, or `none/read-only`), data subtype when applicable (`project`, `regression`, `evaluation`, `environment`, or `private-user`), and audience (`runtime-user`, `developer`, or `both`); then derive write authority, storage target, validation route, version route, and release boundary. Re-evaluate when a new branch appears or before persistence, packaging, publication, or final handoff. The assistant owns this decomposition and states the initial control summary plus material reclassifications in dialogue. Split `mixed` work before writing.
3. Before starting a substantive project task, agree with the user on a task contract: expected result, scope, non-goals, acceptance evidence, allowed side effects, and stop condition. Reuse an already confirmed contract when it still covers the request.
4. Prefer the sequence `discover an existing AI/tool capability -> create or adapt the smallest useful tool when justified -> use the tool for the task`. Direct reasoning is allowed when a tool would add no meaningful reliability, reuse, or scale; record that decision briefly.
5. Put newly created reusable tools in the project's `work/candidate-tools/`. At task close, report purpose, validation, dependencies, risks, and likely reuse, then ask the user to keep, archive, or discard each tool. Do not discard without confirmation.
6. Keep the accepted project contract and task state in `state/`, formal content and typed relations in `records/`, and accepted source metadata in `sources/`. Treat `views/` and `index/` as rebuildable derivatives. Never commit a project fact by editing a view or index.
7. Project tasks have exactly two priorities: `high` and `low`. Work on confirmed high-priority tasks first unless the user explicitly selects a low-priority task. Never promote, demote, add, or close a task without a proposed change and user confirmation.
8. Only a maintainer/integrator session may update formal management data, and only after itemized acceptance. An explorer session may write pending material under `work/` and change project artifacts within its confirmed task contract, but must not edit `state/`, `records/`, `sources/`, `views/`, `index/`, or archived decisions. It produces a handoff package instead.
9. Preserve one stable `objective_id` and explicit project contract: objective, scope, non-goals, assumptions, evidence standard, and completion standard. Revise it only through an accepted `revise-objective` proposal; represent a different direction as a related node or a new project.
10. Keep claims, evidence, attempts, reviews, and decisions distinct. Tool success proves execution, package hashes prove integrity, and neither proves a claim. Preserve a failed attempt formally only when it includes what was tried, why and under which conditions it failed, retry conditions, and minimal reproduction or key evidence.
11. Use one transaction protocol for every important management write: read the current revision, propose items, record each user decision, edit and validate a candidate, increment the revision once, publish, then create a receipt. Imported scripts and tools remain quarantined until separately approved.
12. Every retrieval result must report searched and unsearched authorized scope, index revision, and coverage gaps. An empty result means only “not found in the searched, indexed, and authorized scope,” never “absent from the project.”
13. When a user correction, reproducible failure, violated invariant, or repeated ambiguity reveals a reusable framework defect, propose a regression test. Never silently store the real case: test code and synthetic fixtures are framework artifacts, while real cases and gold data remain external `data:regression` or `data:evaluation` and require a separate accepted write.
14. Keep the private machine profile outside exports. Never record secrets, tokens, raw credentials, or unrelated private paths.

## Route the request

- If `private/local-environment.json` is missing, or the user asks to refresh the machine profile, read `references/local-environment.md`.
- To create a project-local skill, read `references/bootstrap.md`.
- To explore a confirmed task or export a handoff, read `references/explore-and-package.md`.
- To verify, unpack, review, or integrate a handoff, read `references/integrate.md`.
- Before any accepted write to project management data, read `references/commit.md`.
- For project knowledge retrieval or index work, read `references/retrieval.md`.
- Read `references/change-classification.md` when establishing or revising a control plan, especially when a new work branch, persistence target, or release boundary appears.
- Only when the user explicitly requests development of this framework and `development/adr/index.json` exists, enter development mode: read that index and every ADR it marks relevant to the requested design area before proposing changes. For test-impact or regression work, also read `development/policies/regression-testing.md` when present. A `proposed` ADR is design context, not a runtime rule. The absence of `development/` is normal in the distributed runtime skill.

The generated project skill is explicitly invoked and carries a versioned snapshot of the framework rules. It may read this skill's private machine profile at runtime, but it must not copy that profile into the project.

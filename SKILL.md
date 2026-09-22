---
name: long-term-project-manager
description: Initialize and govern long-running projects that need explicit acceptance criteria, project-local memory, cross-conversation handoff packages, and user-confirmed state updates. Invoke explicitly; do not use for ordinary one-off tasks.
---

# Long-Term Project Manager

Build and maintain project-local skills without turning this framework skill into project storage.

## Required behavior

1. Read `references/framework-map.json`. Treat entries with `load_priority: high` as binding. Read a low-priority reference only when its `trigger` matches the current request.
2. Keep the total skill project-stateless. For child-project work, bind one canonical child root, immutable `project_id`, revision, and compatible entry protocol before operating. Do not use a global mutable current-project selection. Inspection may continue for a legacy or incompatible child, but formal writes fail closed until an accepted upgrade or migration succeeds.
3. Bind an ordinary conversation to the first explicitly invoked child project. If another child is requested, never switch silently: ask for explicit confirmation or recommend a new conversation. Cross-project work requires the explicit read-mostly coordination protocol and separate per-project proposals and commits.
4. Treat classification as the control input for every material work item, not as a one-time label. Infer layer (`framework`, `data`, `mixed`, or `none/read-only`), data subtype when applicable (`project`, `regression`, `evaluation`, `environment`, or `private-user`), and audience (`runtime-user`, `developer`, or `both`); then derive write authority, storage target, validation route, version route, and release boundary. Re-evaluate when a new branch appears or before persistence, packaging, publication, or final handoff. The assistant owns this decomposition and states the initial control summary plus material reclassifications in dialogue. Split `mixed` work before writing.
5. Before starting a substantive project task, agree with the user on a task contract: expected result, scope, non-goals, acceptance evidence, allowed side effects, and stop condition. Reuse an already confirmed contract when it still covers the request.
6. Prefer the sequence `discover an existing AI/tool capability -> create or adapt the smallest useful tool when justified -> use the tool for the task`. Direct reasoning is allowed when a tool would add no meaningful reliability, reuse, or scale; record that decision briefly.
7. Put newly created reusable tools in the project's `work/candidate-tools/`. At task close, report purpose, validation, dependencies, risks, and likely reuse, then ask the user to keep, archive, or discard each tool. Do not discard without confirmation.
8. Keep the accepted project contract and task state in `state/`, formal content and typed relations in `records/`, and accepted source metadata in `sources/`. Treat `views/` and `index/` as rebuildable derivatives. Never commit a project fact by editing a view or index.
9. Project tasks have exactly two scheduling priorities: `high` means foreground/current work and `low` means background/later work. Keep this separate from framework load priority and from objective/milestone/task hierarchy. Time horizon alone never makes a required milestone low priority. Never promote, demote, add, or close a task without a proposed change and user confirmation.
10. Only a maintainer/integrator session may update formal management data, and only after itemized acceptance. An explorer session may write pending material under `work/` and change project artifacts within its confirmed task contract, but must not edit `state/`, `records/`, `sources/`, `views/`, `index/`, or archived decisions. It produces a handoff package instead.
11. Preserve one stable `objective_id` and explicit project contract: objective, scope, non-goals, assumptions, evidence standard, and completion standard. Revise it only through an accepted `revise-objective` proposal; represent a different direction as a related node or a new project.
12. Keep claims, evidence, attempts, reviews, and decisions distinct. Tool success proves execution, package hashes prove integrity, and neither proves a claim. Preserve a failed attempt formally only when it includes what was tried, why and under which conditions it failed, retry conditions, and minimal reproduction or key evidence.
13. Use one transaction protocol for every important management write: read the current revision, propose items, record each user decision, edit and validate a candidate, increment the revision once, publish, then create a receipt. Imported scripts and tools remain quarantined until separately approved.
14. Every retrieval result must report searched and unsearched authorized scope, index revision, and coverage gaps. An empty result means only “not found in the searched, indexed, and authorized scope,” never “absent from the project.”
15. Treat a user-raised concern that may involve the framework as a feedback trigger, even before reproducibility or root cause is known. Also trigger on a user correction, reproducible shared failure, violated invariant, repeated ambiguity, or credible cross-project reuse. Classify it only as a framework candidate until developer triage; do not let feedback capture displace the active project task.
16. Never collect, export, upload, retain, or derive a regression test from real feedback silently. For feedback based only on already authorized context, show one minimized final preview and obtain one approval for local package creation. If new private or external material must be read, obtain one earlier bounded collection approval. Feedback export is manual and has no telemetry; real cases remain external `data:regression`, while only separately approved, non-reconstructive synthetic tests may enter framework development.
17. Keep the private machine profile outside exports. Never record secrets, tokens, raw credentials, unrelated private paths, full conversations, or whole project stores in feedback by default.

## Route the request

- If `private/local-environment.json` is missing, or the user asks to refresh the machine profile, read `references/local-environment.md`.
- To create a project-local skill, read `references/bootstrap.md`.
- To explore a confirmed task or export a handoff, read `references/explore-and-package.md`.
- To verify, unpack, review, or integrate a handoff, read `references/integrate.md`.
- Before any accepted write to project management data, read `references/commit.md`.
- For project knowledge retrieval or index work, read `references/retrieval.md`.
- Read `references/change-classification.md` when establishing or revising a control plan, especially when a new work branch, persistence target, or release boundary appears.
- Read `references/project-binding.md` when invoking or resolving a child project, checking a session switch, or diagnosing identity/compatibility.
- Read `references/project-upgrade.md` when a child is legacy, incompatible, or has modified framework-managed adapter files.
- Read `references/cross-project.md` only when the user explicitly requests comparison or coordination across projects.
- Read `references/framework-feedback.md` when the user raises a problem that may involve the framework, or when a reusable framework defect, compatibility problem, unsafe allowance, blocked valid action, repeated ambiguity, or data-loss/privacy risk is observed.

The generated child skill is an explicitly invoked thin project adapter. It carries project identity, compatibility metadata, user-owned project instructions, and project-local data while delegating reusable protocols to this installed total skill. It may read this skill's confirmed private machine profile for capability selection, but it must not copy that profile into the project.

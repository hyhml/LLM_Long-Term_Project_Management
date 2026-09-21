# ADR-0013: Project-bound child skills and explicit conversation isolation

- Status: Accepted
- Date: 2026-09-21
- Implemented in: `0.5.0-rc.1`

## Context

The total skill is intended to serve many unrelated projects. A user may maintain, for example, one project about LLM cross-conversation collaboration and another about harness design. Both projects should benefit from the same framework implementation and future framework updates without sharing accepted facts, tasks, searches, packages, or implicit working context.

Sharing framework code is not the same as sharing project state. The main risks are:

1. **storage contamination**: a read, search, write, package, or migration operates on the wrong project directory;
2. **conversation contamination**: one conversation loads more than one project's context and then treats the active project as implicit;
3. **upgrade contamination**: a framework update rewrites project-owned content or treats a data migration as an ordinary framework refresh;
4. **intentional cross-project work becoming an implicit merge**: comparison or coordination silently changes both projects.

Filesystem separation can deterministically control the first and third risks. It cannot make an LLM forget text already present in one conversation, so conversation authority must also be explicit.

## Decision

### 1. Share the framework, not project context

The installed total skill is project-stateless. It may own reusable protocols, scripts, schemas, compatibility logic, and the separately governed private machine profile, but it does not own concrete project records or a mutable global “current project.”

Each child skill represents exactly one project. It is the project's identity, namespace, thin framework adapter, and project-local storage boundary. Its formal and pending data travel with that project.

The target child shape is:

```text
<project-root>/.agents/skills/<project-skill>/
├── SKILL.md                     # thin, explicitly invoked project entry
├── agents/openai.yaml
├── framework/instance.json      # identity, protocol, compatibility metadata
├── project-instructions.md      # project-specific, user-owned instructions
├── state/
├── records/
├── sources/
├── work/
├── views/
├── index/
└── packages/
```

Shared conditional protocols belong to the total skill rather than being independently copied and allowed to diverge in every child. Project-specific instructions and data remain in the child.

### 2. Bind every operation to one project instance

Every project operation is resolved from an explicit binding containing, at minimum:

```text
framework/entry protocol + canonical project-skill root + project_id + project revision
```

The `project_id` is unique and immutable. Tools take an explicit project-skill root, load the identity from that root, and reject missing, inconsistent, ambiguous, or cross-project identifiers. No global registry or process-wide “current project” is authoritative for writes.

Search, validation, transactions, packaging, import, rendering, and migrations default to the bound project only. A package whose `project_id` does not match the destination is reviewable as an external artifact but cannot be committed there as a normal same-project handoff.

### 3. Bind an ordinary conversation to one active project

The first explicitly invoked child skill establishes the active project for ordinary project work in that conversation. Each material result and receipt identifies the bound project.

If another child is invoked in the same conversation, the framework does not silently switch. It asks for an explicit switch or recommends a new conversation. A new conversation is the preferred boundary because switching authority does not remove already loaded model context.

This is an authority and routing guarantee, not a claim that prior conversation text can be erased.

### 4. Make cross-project coordination an explicit mode

Cross-project comparison or coordination requires an explicit user request and declared project set. It may read the minimum necessary derived maps or selected records from those projects and must report the participating project IDs and coverage.

Coordination does not create a merged authority domain. Formal changes are proposed, confirmed, validated, versioned, and receipted separately for each destination project. One transaction never silently commits to multiple projects.

### 5. Keep architecture updates separate from project-data migration

A compatible total-skill update may change shared framework behavior without copying or rewriting project content. A thin-entry protocol change and a project-data schema migration are separate operations:

- framework/entry updates affect only framework-owned adapter metadata or files;
- project-data migrations require an itemized proposal, user decisions, validation, revision handling, and a receipt;
- incompatibility permits inspection but blocks unsafe formal writes until resolved.

The next-version implementation plan defines the initial compatibility and migration mechanics and remains subject to separate approval.

## Consequences

- Two child skills can use one installed framework without sharing data.
- Project locality, explicit invocation, immutable identity, and root validation form the primary isolation boundary.
- Keeping unrelated projects in separate project roots gives the strongest discovery and context boundary. Multiple child skills under one repository remain possible only when invocation and binding are unambiguous.
- A conversation that has already loaded two projects can still contain semantic cross-contamination; the framework limits authority and recommends a fresh conversation instead of claiming perfect memory isolation.
- Deliberate cross-project relationships can be represented later by explicit project identifiers and locators, but never by copying one project's records into another without proposal and acceptance.
- The child becomes closer to an application document or database instance, while the total skill remains the shared application/runtime.

## Required regression coverage

The implementation must demonstrate at least these reusable invariants:

1. searching project A cannot return project B data by default;
2. a project-A root combined with project-B identity fails closed;
3. a project-A handoff cannot be committed as a project-B handoff;
4. framework updates do not modify project-owned records, tasks, sources, work, or instructions;
5. an ambiguous or incompatible child is read-only for formal operations;
6. cross-project mode is explicit and produces separate per-project proposals and commits;
7. the global total skill stores no concrete project state or mutable authoritative current-project selection.

## Alternatives rejected

- **Copy the complete total skill into every project.** This isolates files initially but creates independently diverging framework copies and makes updates unsafe and expensive.
- **Use one global mutable current-project setting.** Concurrent conversations or accidental switches can redirect operations without a local identity check.
- **Infer the project only from conversation subject or current directory.** Both are convenient hints but insufficient authority for formal reads and writes.
- **Allow one transaction to update several projects.** This hides separate revisions and user decisions and complicates recovery.

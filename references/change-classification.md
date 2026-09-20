# Classification-driven control loop

Classification is a continuing control decision for each material work item. It determines authority, storage, validation, versioning, and release behavior; the dialogue label is only its visible summary.

## Classify the work item

Layer:

- `framework`: reusable rules, schemas, templates, scripts, protocols, ADRs, framework tests, or framework version;
- `data`: persisted content governed by a framework;
- `mixed`: more than one authority boundary; split before writing;
- `none/read-only`: no authority changes.

For `data`, add one subtype:

- `project`: one concrete project's contract, tasks, records, relations, sources, work, tools, or authorized artifacts;
- `regression`: real incidents and reproductions retained to prevent a known defect from returning;
- `evaluation`: benchmark prompts, expected answers, scoring rules, and comparison results;
- `environment`: local models, tools, paths, capabilities, and compatibility facts;
- `private-user`: user material requiring stricter access and export boundaries.

Audience is independent: `runtime-user`, `developer`, or `both`.

Classify by the authority changed, not by topic or tool. Using a framework tool to update a project is `data:project`. Changing a generic data schema is `framework`. Creating a child project with an unchanged initializer creates `data:project`; it does not modify the framework.

## Derive the control plan

For each material item, derive:

- `write_authority`: who or which confirmed workflow may write;
- `storage_targets`: allowed live, candidate, development, or external locations;
- `validation_route`: invariant, schema, workflow, evaluation, or human review required;
- `version_route`: project revision, objective revision, framework version, dataset version, or none;
- `release_boundary`: project-local, development-only, runtime release, external dataset, or no release.

A label without these consequences is incomplete classification. A formal project task contract stores its classification and control plan. Framework development records the same reasoning in dialogue, ADR/version material, and the development branch rather than in project state.

## Re-evaluate continuously

Re-run classification when:

- the user introduces a new objective, subtask, data source, test, or audience;
- analysis produces a reusable framework proposal or a real regression case;
- work is about to move from discussion or `work/` into formal storage;
- a tool, package, or external source is about to be retained;
- a revision, migration, export, merge, or release is proposed;
- the final handoff reconciles what actually changed.

The assistant performs the decomposition proactively. Ask the user only when ambiguity would materially change authority, persistence, or release. Do not require the user to supply the classification.

## Dialogue behavior

At the first substantive update, summarize the active work items and their control boundary. Keep obvious cases short. Report new or changed classifications when they affect authority, storage, validation, version, or release; do not repeat unchanged labels on every message.

Before final handoff, reconcile planned and actual classifications. State where each material part was written, versioned, validated, and released. Never describe developer-only artifacts as installed runtime behavior, external evaluation data as project knowledge, or a framework template change as migration of existing projects.

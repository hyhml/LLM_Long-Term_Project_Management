# LLM Long-Term Project Management: Product Map

- Scope: development-only product intent and coverage map
- Authority: user-confirmed requirements, organized for framework development
- Updated: 2026-09-22
- Runtime distribution: excluded from `main` and user release archives

## How to use this map

Read this file before planning or changing the framework. It answers **what the product must do and how the requirements relate**. It does not replace:

- ADRs, which record why a design choice was made;
- `references/framework-map.json`, which contains rules loaded by the user runtime;
- tests, which provide implementation evidence;
- version notes and release receipts, which record what was delivered.

The latest explicit user decision overrides this map. When that happens, update this map in the same development change. Do not silently convert an implementation proposal into a confirmed requirement.

Status meanings:

- `implemented`: the end-to-end behavior exists and has relevant validation;
- `partial`: some mechanism exists, but the user-visible capability is incomplete;
- `planned`: confirmed requirement with no complete implementation;
- `deferred`: confirmed requirement intentionally postponed;
- `open-design`: the outcome is required but the mechanism still needs user discussion;
- `out-of-scope`: explicitly excluded from the current product.

Priorities are exactly `high` and `low`. `deferred` describes timing, not importance: a high-priority item can be deferred while prerequisites are built.

## 1. Product definition

This product is a lightweight, domain-neutral framework for LLM cross-conversation collaboration and long-term project management. It must support projects in mathematics, politics, chemistry, engineering, writing, and other subjects without embedding one domain's ontology as the universal core.

The framework turns a user's confirmed description of one topic or project into a project-local child skill. That child skill carries the project's identity, accepted knowledge, pending work, task priorities, relationships, retrieval boundary, and cross-conversation handoff state. Separate conversations can then maintain the project or explore one task and return a verifiable package.

The product is deliberately smaller than a complete personal knowledge-management system. Project-local knowledge accumulates gradually; a global personal knowledge base is not a prerequisite for useful project work.

## 2. Product layers and modes

```text
developer mode
  framework source + product map + ADRs + policies + tests + release tools
                              |
                              | whitelist build and stable release
                              v
user mode: global total skill
  project-stateless shared runtime + generator + compatibility/migration service
                              |
                              | confirmed project specification
                              v
project-local child skill
  thin project adapter + immutable identity + project contract/data/map/work/packages
```

### Developer mode

Developer mode designs, tests, versions, and releases the reusable framework. Developer material must not appear in the user bundle. Development decisions distinguish framework versus data changes and developer versus runtime audiences.

### User mode

User mode is the installed global total skill. It is explicitly invoked. It discusses the user's project, establishes acceptance criteria, generates a child skill, supplies shared deterministic tools, detects child compatibility, and proposes upgrades when the total skill changes. It does not store concrete project knowledge in the global skill.

### Project-local child skill

A child skill is one managed project instance and isolation boundary, not an independent fork of the total skill. It binds one immutable project identity to one project-local root, while delegating reusable behavior to a compatible installed total skill. Project instructions and data travel with the project. The child must remain identifiable, validatable, and upgradeable without silently changing accepted project facts or reading another child's state.

An ordinary conversation is bound to one active child project. Switching projects is explicit, and starting a new conversation is preferred because changing write authority cannot erase context already loaded by the model. Intentional cross-project coordination is a separate explicit mode; it never creates an implicit shared transaction or merged project authority.

## 3. End-to-end lifecycle

The required user journey is:

```text
install and explicitly invoke total skill
-> explain tool discovery, obtain permission once, then detect and privately save available tools
-> discuss one project's stable contract and completion standard
-> discuss initial records, relations, sources, files, and high/low tasks
-> present an itemized child-skill creation proposal
-> user accepts
-> generate and validate the project-local child skill
-> bind each ordinary project conversation to that child's root and project_id
-> maintain or explore the project across conversations
-> prepare a package preview, obtain one approval, then create one verified handoff file
-> unpack, propose, receive itemized user decisions, and commit one revision
-> detect later total-skill updates
-> propose and validate child architecture upgrade
-> migrate project data separately when a schema change requires it
-> generate upgrade and migration receipts
-> when a user raises a possible framework problem, classify it provisionally
-> preview and export minimal feedback with one approval; ask once more only if new private material must be read
-> let the user manually submit one verified feedback file to developer intake
-> triage externally, derive only approved synthetic tests, fix, and return a resolution receipt
```

Generation and upgrade are both part of the primary product capability. Implementing initialization without a supported upgrade path does not complete the child-skill lifecycle.

## 4. Requirement registry

### A. Product boundary and architecture

| ID | Priority | Requirement | Status | Evidence or gap |
|---|---|---|---|---|
| `PROD-001` | high | Provide domain-neutral cross-conversation and long-term project management. | partial | Core storage, handoff, retrieval, and transactions exist; sustained real-project validation remains limited. |
| `PROD-002` | high | Separate reusable total-framework behavior from concrete project-local state. | implemented | Global runtime and project-local generated layout are separate. |
| `PROD-003` | high | Separate developer mode from user mode. | implemented | Development-only harness plus whitelist-built `main`/release. |
| `PROD-004` | high | Keep the installed global user skill thin and free of project data. | implemented | Runtime release has only framework files; private/project data are excluded. |
| `PROD-005` | high | Project data and its child skill travel with the project. | implemented | Project-local data, portable identity/compatibility metadata, handoffs, and explicit adapter upgrade support cross-machine use with a compatible installed total skill. |
| `PROD-006` | high | Treat the child skill as a managed project instance rather than an independently diverging framework fork. | implemented | Thin adapter, instance contract, ownership hashes, compatibility inspection, and accepted upgrade path. |
| `PROD-007` | high | Design for projects with tens of map nodes before optimizing for large-scale storage. | implemented | Current JSON structures and bounded scanning target this scale. |
| `PROD-008` | high | Divide framework rules into high- and low-load priorities; load the binding core directly and conditional detail only when triggered. | implemented | Runtime framework map and total-skill references provide progressive disclosure; thin children no longer copy conditional modules. |
| `PROD-009` | high | Share one project-stateless total framework across independently isolated project-local child skills. | implemented | ADR-0013 runtime rules, thin children, binding checks, and isolation tests. |

### B. Child-skill creation and evolution

| ID | Priority | Requirement | Status | Evidence or gap |
|---|---|---|---|---|
| `CHILD-001` | high | After discussion and user confirmation, automatically generate one explicitly invoked child skill for the topic/project. | partial | `init_project.py` renders a child skill, but the creation contract is not a complete structured proposal. |
| `CHILD-002` | high | Creation must represent the complete confirmed project specification: objective, scope, non-goals, assumptions, evidence and completion standards, initial records, typed relations, sources, existing project-file references, and high/low tasks. | partial | Objective and tasks are supported; arbitrary initial records, relations, sources, and file mappings are not fully accepted by the initializer. |
| `CHILD-003` | high | Generate the child only after an itemized proposal and user acceptance; validate it and produce an initialization receipt. | partial | Discussion and validation are instructed; a structured creation plan and receipt are missing. |
| `CHILD-004` | high | Record the total-framework release, child-template version, storage schemas, compatibility range, and managed-file hashes in the child. | implemented | `ltpm-project-instance/v1` records release lineage, entry protocol, schemas, ownership, and managed hashes. |
| `CHILD-005` | high | When the total skill updates, detect each opened child's version and supported compatibility before allowing formal writes. | implemented | Shared binding inspector returns compatible, upgrade, migration, ambiguous, or invalid status. |
| `CHILD-006` | high | Provide a supported child-architecture synchronization path after total-skill updates. | implemented | Compatible shared behavior requires no child rewrite; adapter changes use inspect/propose/apply/verify. |
| `CHILD-007` | high | Upgrade framework-managed child files without overwriting project data or unrecognized user modifications. | implemented | Managed hashes, itemized acceptance, staged candidate, prior-adapter archive, validation, swap, rollback, and receipt. |
| `CHILD-008` | high | Split child architecture upgrades (`framework`) from project-data schema migrations (`data:project`); use proposal, validation, revision, and receipts for each boundary. | partial | v0.5.0 adapter upgrades preserve v0.4.0 data schemas and refuse migration-required projects; a future schema migration engine remains unimplemented. |
| `CHILD-009` | high | Permit read-only inspection when compatibility is uncertain; block unsafe formal writes rather than guessing. | implemented | Binding gate permits legacy/incompatible reads and blocks transactions, rendering, and package export. |
| `CHILD-010` | low | Discover and report multiple local projects that could be upgraded, without silently modifying them. | planned | No local project registry or discovery command exists. |
| `CHILD-011` | high | Keep project-specific user instructions outside framework-managed adapter files so framework updates preserve them. | implemented | New and upgraded children use a user-owned `project-instructions.md`; rollback/preservation tests cover it. |

### C. Project identity, map, and knowledge

| ID | Priority | Requirement | Status | Evidence or gap |
|---|---|---|---|---|
| `DATA-001` | high | Give every project a stable contract: objective, scope, non-goals, assumptions, evidence standard, and completion standard. | implemented | `state/project.json` and validation enforce it. |
| `DATA-002` | high | Preserve stable project identity; do not silently replace one project with another direction. | implemented | Objective ID and explicit revision transaction are enforced. |
| `DATA-003` | high | Make accepted records and typed relations authoritative; make the project map a directly loaded derived navigation view. | implemented | `records/`, `state/`, `sources/`, renderer, and validation. |
| `DATA-004` | high | Separate accepted records from current exploration and unconfirmed discoveries. | implemented | `records/` versus `work/`. |
| `DATA-005` | high | Separate claims, evidence, attempts, reviews, decisions, tasks, risks, questions, and artifacts. | implemented | Typed record model and validation. |
| `DATA-006` | high | Preserve useful failed directions with conditions and reproduction, but exclude routine logs, caches, duplicates, and meaningless intermediates. | implemented | Failed-attempt validation and retention rule. |
| `DATA-007` | high | Maintain exactly high- and low-priority project tasks; user confirmation controls additions, closure, and reprioritization. | implemented | Task board and child rules. |
| `DATA-008` | high | Use typed relations for containment, dependency, causation, support, contradiction, testing, production, supersession, blocking, and derivation. | implemented | Record-store relation validation. |
| `DATA-009` | high | Keep index data disposable and report retrieval coverage, authorization, exclusions, and freshness. | implemented | Index manifest and coverage-reporting search. |
| `DATA-010` | low | Grow a broader personal knowledge base gradually without making it a prerequisite for project initialization. | planned | Current knowledge is project-local only. |
| `DATA-011` | high | Directly load the compact project map, then read detailed records, source metadata, and materials only when the current node or task requires them. | implemented | Child entry loads `views/project-map.json` and routes selective formal-detail reads. |
| `DATA-012` | high | Keep framework load priority, task scheduling priority, and objective/milestone/task hierarchy distinct; time horizon alone does not make a required milestone low priority. | implemented | Structured runtime semantics, direct rules, data-model guidance, and tests; no data-schema change. |

### D. Cross-conversation workflow

| ID | Priority | Requirement | Status | Evidence or gap |
|---|---|---|---|---|
| `FLOW-001` | high | Separate maintainer, explorer, and integrator authority. | implemented | Total and child skill rules. |
| `FLOW-002` | high | Explorer sessions start from a confirmed task and task contract, write pending work only, and package before context loss or after decision-changing progress. | implemented | Explorer protocol and handoff exporter. |
| `FLOW-003` | high | Transport cross-conversation work as one file with complete manifest and integrity validation. | implemented | `.llmpack` exporter/verifier/unpacker. |
| `FLOW-004` | high | Unpacking produces itemized proposals; every item can be accepted, modified, rejected, or deferred before commit. | implemented | Integration and transaction protocols; semantic proposal-to-edit mapping still requires the integrator. |
| `FLOW-005` | high | Important accepted writes share one base-revision transaction, validation, single revision increment, and receipt. | implemented | `project_transaction.py`. |
| `FLOW-006` | high | Package hashes prove integrity only, not truth, trust, acceptance, or sender identity. | implemented | Runtime rules and tests. |
| `FLOW-007` | high | Permit future parallel exploration while preventing stale packages from silently overwriting newer state. | deferred | Stale revision rejection exists; parallel merge is intentionally not implemented. |
| `FLOW-008` | low | Add package authenticity signatures in addition to integrity hashes. | deferred | Backlog item. |
| `FLOW-009` | high | Whether requested by the user or triggered by the framework, prepare a concise `.llmpack` preview and create the final package only after one approval; integration still requires itemized decisions. | implemented | Preview hash binds project, revision, inputs, destination, and exclusions; package v1 is unchanged. |

### E. Task handling and tool lifecycle

| ID | Priority | Requirement | Status | Evidence or gap |
|---|---|---|---|---|
| `TASK-001` | high | Agree on observable completion criteria before substantive project work. | implemented | Task-contract rule and validator. |
| `TASK-002` | high | Prefer discover existing AI/tool capability, then create/adapt the smallest justified tool, then use the tool. | partial | Behavioral practice is instructed; broader usage evaluation remains future evidence. |
| `TASK-003` | high | Keep reusable created tools as candidates and ask whether to retain, archive, or discard them at task close. | partial | Candidate-tool workspace and lifecycle protocol exist; sustained usage evidence is limited. |
| `TASK-004` | high | Never silently convert an idea, finding, or possible next task into an accepted task. | implemented | Child rules and transaction boundary. |

### F. Classification and governance

| ID | Priority | Requirement | Status | Evidence or gap |
|---|---|---|---|---|
| `GOV-001` | high | Treat classification as continuous project control, not an opening label. | implemented | Layer, subtype, audience, and control-plan rules. |
| `GOV-002` | high | Distinguish framework, data, mixed, and read-only work; split mixed work before writing. | implemented | Runtime rule and ADR-0009. |
| `GOV-003` | high | Distinguish project, regression, evaluation, environment, and private-user data. | implemented | Classification reference and task-contract enforcement. |
| `GOV-004` | high | Distinguish runtime-user, developer, and both audiences, and report actual release boundaries. | implemented | Runtime and developer governance. |
| `GOV-005` | high | Make the assistant proactively classify and decompose work; ask the user only when ambiguity changes authority, persistence, or release. | partial | Classification control loop is specified and structurally enforced for task contracts; broader behavioral evidence is limited. |
| `GOV-006` | high | Use this product map as the development-level authority for product intent and coverage. | implemented | ADR-0012 and developer `AGENTS.md`. |
| `GOV-007` | high | Update this map when a user changes a requirement, priority, scope, or acceptance condition. | implemented | Developer `AGENTS.md`; ongoing compliance is required for every development change. |
| `GOV-008` | high | Scale framework work by side effect and risk: design-only, runtime implementation, and release use progressively stronger records and validation. | implemented | Developer `AGENTS.md`, this control loop, and ADR-0015. |

### G. Testing, release, and data boundaries

| ID | Priority | Requirement | Status | Evidence or gap |
|---|---|---|---|---|
| `QUAL-001` | high | Protect the original six core invariants: cross-conversation loop, authority boundary, decision/revision transaction, project identity, rebuildability, and information boundary. | implemented | 23 original core tests remain passing. |
| `QUAL-002` | high | Add regression tests only for reusable defects under an itemized proposal; keep real cases and gold data external. | implemented | ADR-0010 and regression policy. |
| `QUAL-003` | high | Keep developer tests, ADRs, policies, and release tooling out of user distributions. | implemented | Exact runtime allowlist and release tests. |
| `QUAL-004` | high | Build `main` and release archives from a whitelist, fail on unclassified files, and validate the generated runtime and child skill. | implemented | ADR-0011, deterministic builder, release tests, and `v0.4.0`/`v0.5.0`/`v0.6.0` receipts. |
| `QUAL-005` | high | Do not store project data, real regression/evaluation data, secrets, or unrelated private paths in framework releases. | implemented | Release allowlist, private ignore, and policies. |
| `QUAL-006` | low | Domain-specific educational safety and adversarial test suites. | out-of-scope | May belong to a future educational child skill, not the generic framework core. |
| `QUAL-007` | high | Add a multi-project isolation invariant group covering root/identity mismatch, retrieval and package boundaries, framework-update preservation, conversation switching, and explicit coordination. | implemented | Five synthetic tests cover separate search, explicit coordination, mismatch/ambiguity, session switch, handoff rejection, upgrade preservation, and rollback. |

### H. Environment, portability, and platform scope

| ID | Priority | Requirement | Status | Evidence or gap |
|---|---|---|---|---|
| `ENV-001` | high | Support Codex CLI as the initial runtime environment. | implemented | Current skill layout and scripts target Codex CLI. |
| `ENV-002` | low | Adapt the framework for ChatGPT web. | deferred | Backlog item; no implementation. |
| `ENV-003` | high | Explain that discovery is for selecting usable tools, obtain permission once, then search the bounded tool/skill/model scope and privately save the result. | implemented | Approved `initialize` performs bounded discovery and one private atomic save; legacy diagnostics remain available. |
| `ENV-004` | low | Detect and propose machine-profile updates automatically. | deferred | Backlog item. |
| `ENV-005` | high | Do not export or copy the private machine profile into a project or handoff. | implemented | Runtime rule and release/package boundaries. |
| `ENV-006` | high | Support project transfer between systems without assuming shared state; use portable project data and single-file handoffs with integrity checking. | implemented | Portable child instance metadata, compatibility inspection, thin-adapter upgrade, and verified handoffs require only a compatible installed total skill. |
| `ENV-007` | high | On first use on a machine, let a child read the confirmed profile from the installed total skill for capability selection without copying it into the project. | partial | Child rule exists; deterministic total-skill discovery and compatibility handling remain incomplete. |

### I. Multi-project isolation

| ID | Priority | Requirement | Status | Evidence or gap |
|---|---|---|---|---|
| `ISOL-001` | high | Bind every project operation to one canonical project-skill root, immutable `project_id`, project revision, and compatible framework/entry protocol. | implemented | `project_binding.py` and `ltpm-project-instance/v1`. |
| `ISOL-002` | high | Scope retrieval, validation, transactions, packages, imports, views, indexes, and migrations to the bound project by default and fail closed on identity mismatch or ambiguity. | implemented | Shared binding gate, destination check, explicit roots, and isolation tests. |
| `ISOL-003` | high | Bind an ordinary conversation to one active project; never switch implicitly, and prefer a new conversation when another project is requested. | implemented | High-priority runtime rule plus deterministic session decision and regression coverage. |
| `ISOL-004` | high | Require explicit cross-project coordination, declare participating project IDs and retrieval coverage, and keep proposals, decisions, revisions, and receipts separate per project. | implemented | Read-mostly coordinator reports participants/coverage and forbids merged writes. |
| `ISOL-005` | high | Keep the total skill free of concrete project state and any mutable authoritative global current-project selection. | implemented | Runtime invariant, no selector storage, project-local initializer output, and release/isolation tests. |
| `ISOL-006` | high | Detect ambiguous child resolution, duplicate identity, or incompatible framework binding and allow inspection while blocking unsafe formal writes. | implemented | Binding statuses, sibling duplicate detection, managed hashes, schema checks, and fail-closed tools. |

### J. Consent-based framework feedback

| ID | Priority | Requirement | Status | Evidence or gap |
|---|---|---|---|---|
| `FEED-001` | high | Trigger provisional feedback classification whenever the user actively raises a problem that may involve the framework, as well as for observed reusable failures, invariant violations, repeated ambiguity, unsafe allowances, blocked valid actions, or data-loss/privacy risk. | implemented | Total-skill high-priority rule, framework map trigger, conditional protocol, and thin-child route. |
| `FEED-002` | high | Distinguish provisional cause classification from remediation scope; do not claim a framework defect before developer triage. | implemented | Versioned issue schema separates category, confidence, reasoning, suspected component, and remediation scope. |
| `FEED-003` | high | Use one approval for an ordinary feedback preview built from authorized context; require one earlier bounded permission only when new private or external material must be read. | implemented | Runtime protocol maps one ordinary approval event into feedback v1 audit fields; existing intake remains compatible. |
| `FEED-004` | high | Export one integrity-checked feedback file without telemetry or automatic upload, and keep it distinct from project handoffs and project authority. | implemented | `.ltpm-feedback` protocol and deterministic exporter/verifier; user performs transport manually. |
| `FEED-005` | high | Minimize and redact feedback; exclude secrets, private machine profiles, full conversations, whole project stores, and unrelated private paths by default while reporting coverage gaps. | implemented | Feedback protocol, schema, redaction report, package inspection, and synthetic tests. |
| `FEED-006` | high | Keep real feedback external to the repository and runtime distribution; developer intake verifies, inspects, and quarantines it without executing attachments. | implemented | Developer-only intake refuses repository quarantine and release allowlist excludes the harness. |
| `FEED-007` | high | Derive repository regression tests only from separately authorized, non-reconstructive synthetic cases under itemized triage. | implemented | Consent field, external triage template, ADR-0010 policy integration, and ADR-0014. |
| `FEED-008` | high | Return a non-mutating resolution receipt that links feedback identity, final classification, affected/fixed versions, and required child action. | implemented | Developer resolution command emits `ltpm-feedback-resolution/v1`. |

## 5. Typed requirement relationships

| From | Relation | To | Meaning |
|---|---|---|---|
| `PROD-001` | contains | `CHILD-001`, `FLOW-001`, `DATA-003` | The overall product depends on project instantiation, governed collaboration, and durable knowledge. |
| `PROD-003` | depends_on | `QUAL-003`, `QUAL-004` | Developer/user separation requires a verified release boundary. |
| `PROD-005` | depends_on | `CHILD-004`, `ENV-006` | A portable long-term project needs explicit framework compatibility metadata. |
| `PROD-006` | depends_on | `CHILD-004`, `CHILD-007` | A managed instance requires ownership and managed-file tracking. |
| `PROD-009` | depends_on | `ISOL-001`, `ISOL-002`, `ISOL-005` | Sharing the framework is safe only when identity, operations, and global state remain project-bound. |
| `CHILD-001` | depends_on | `CHILD-002`, `CHILD-003` | A skeleton alone does not complete project-specific generation. |
| `CHILD-005` | depends_on | `CHILD-004` | Compatibility detection requires recorded versions and schemas. |
| `CHILD-006` | depends_on | `CHILD-005`, `CHILD-007`, `CHILD-008` | Synchronization requires detection, safe managed-file updates, and separate data migration. |
| `CHILD-007` | constrained_by | `DATA-001`, `DATA-002`, `QUAL-005` | Architecture refresh must preserve project identity, facts, and privacy. |
| `CHILD-008` | uses | `FLOW-005`, `GOV-002` | Upgrade and data migration must be split and transactionally governed. |
| `CHILD-011` | constrained_by | `CHILD-007`, `ISOL-005` | User-owned instructions must survive framework refreshes without becoming global framework state. |
| `FLOW-002` | produces | `FLOW-003` | Exploration produces the portable handoff. |
| `FLOW-003` | precedes | `FLOW-004`, `FLOW-005` | Package transport precedes proposal and accepted commit. |
| `DATA-003` | depends_on | `DATA-004`, `DATA-008` | A trustworthy map depends on accepted records and typed relations. |
| `DATA-011` | depends_on | `DATA-003`, `PROD-008` | Selective loading depends on a reliable derived map and framework load priorities. |
| `DATA-012` | constrained_by | `DATA-007`, `PROD-008` | Scheduling priority remains separate from loading priority and goal hierarchy. |
| `DATA-009` | constrained_by | `FLOW-006` | Retrieval coverage and package integrity must not become truth claims. |
| `QUAL-001` | tests | `FLOW-001`, `DATA-002`, `DATA-003`, `FLOW-005` | Core tests protect cross-cutting product invariants. |
| `QUAL-007` | tests | `ISOL-001`, `ISOL-002`, `ISOL-003`, `ISOL-004`, `ISOL-005`, `ISOL-006` | Isolation tests must exercise both deterministic storage boundaries and conversation-routing behavior. |
| `QUAL-004` | releases | `PROD-003`, `PROD-004` | Whitelist release realizes the user/developer and thin-runtime boundary. |
| `ENV-007` | constrained_by | `ENV-005`, `CHILD-005` | Machine capability reuse must preserve privacy and framework compatibility. |
| `ISOL-001` | uses | `DATA-002`, `CHILD-004` | Operation binding depends on stable project identity and explicit compatibility metadata. |
| `ISOL-002` | constrains | `DATA-009`, `FLOW-003`, `FLOW-005` | Search, handoff, and commit must never infer a different project boundary. |
| `ISOL-003` | constrains | `FLOW-001`, `TASK-001` | Role and task contracts operate within one explicitly active project conversation. |
| `ISOL-004` | constrained_by | `FLOW-005`, `DATA-009` | Cross-project coordination retains separate transactions and reports retrieval coverage. |
| `FLOW-009` | constrained_by | `FLOW-003`, `FLOW-004`, `QUAL-005` | Package approval authorizes creation, not later acceptance into project authority. |
| `FEED-001` | uses | `GOV-001`, `GOV-005` | Runtime feedback begins with continuous, assistant-owned provisional classification. |
| `FEED-003` | constrained_by | `QUAL-005`, `ENV-005` | Consent and minimization preserve private, project, and machine-data boundaries. |
| `FEED-004` | constrained_by | `FLOW-006`, `ISOL-005` | Feedback integrity is not truth or identity, and the total skill remains project-stateless. |
| `FEED-006` | depends_on | `PROD-003`, `QUAL-003`, `QUAL-005` | Safe intake depends on the developer/runtime boundary and external real-case storage. |
| `FEED-007` | uses | `QUAL-002` | Test derivation follows the accepted regression policy rather than importing a real incident. |
| `GOV-008` | constrains | `QUAL-001`, `QUAL-004` | Full implementation and release gates are used at their own stages rather than for every design edit. |

## 6. Current high-priority gaps

The following gaps must remain visible in every framework planning session:

1. **Complete child generation (`CHILD-001`–`CHILD-003`)**: the current initializer creates a valid skeleton but cannot yet consume the complete discussed project graph or create a formal initialization proposal/receipt.
2. **Future project-data schema migration (`CHILD-008`)**: v0.5.0 intentionally keeps existing data schemas and refuses unsupported schemas; a future release must design and test the first real migration before claiming general migration support.
3. **Parallel exploration (`FLOW-007`)**: high priority but intentionally deferred; stale transactions are rejected, while parallel rebase/merge is not implemented.

Release isolation is no longer an open gap: `QUAL-003` and `QUAL-004` were completed by `v0.4.0` and reused successfully through the stable `v0.6.1` release.

## 7. Open design questions requiring user discussion

These are not permission to choose silently:

1. How many historical framework versions, if any, should the total skill support side by side after the v0.4.0 adapter path?
2. Should local project discovery use an optional private registry, explicit roots, or both?
3. What transaction and rollback model should govern the first real project-data schema migration?

ADR-0013 and the released v0.5.0 plan resolve the dependency, thin-entry, user-instruction, adapter rollback, and read-mostly coordination choices. ADR-0014 and released v0.6.0 add the consent-based external feedback loop without changing project-data schemas.
ADR-0015 scales development work by risk and defines the minimal v0.6.1 interaction changes without freezing implementation details.

## 8. Development control loop

For every framework task:

1. read this map;
2. identify affected requirement IDs and relationships;
3. classify framework/data and runtime/developer effects;
4. choose design-only, implementation, or release weight from actual side effects and risk;
5. state the acceptance evidence and current gap;
6. read relevant ADRs and policies;
7. update the product map if the user's requirement, priority, scope, or status changed;
8. validate only to the selected weight unless a concrete risk requires escalation;
9. reconcile requirement status with actual evidence before release.

A script, template, rule, or test is evidence for a requirement, not proof that the full user-visible capability exists. Completion is assessed end to end.

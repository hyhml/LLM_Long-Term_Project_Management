# ADR-0015: Concise, purpose-bound consent for discovery and package creation

- Status: Accepted
- Date: 2026-09-22
- Target: `0.6.1`
- Implemented in: Not yet implemented

## Context

The framework needs explicit authority before inspecting private machine capabilities or creating transport files, but v0.6.0 makes ordinary feedback follow two mandatory consent gates and exposes field-level approval mechanics to the user. The environment procedure has the opposite problem: it detects machine information before asking and then requests confirmation only before save. Cross-conversation handoff export has no mandatory final package-preview approval.

The user has clarified that authorization should be simple and aligned with the actual operation:

- tool discovery needs one explanation and one approval covering detection plus private local save;
- a final package needs one approval of a concise complete preview;
- a second approval is needed only when preparing that preview requires a new read of external or private material;
- package creation approval is not the same as accepting unpacked content into project authority.

The same discussion also confirmed that framework load order, task scheduling, and goal hierarchy are independent concepts. A future mandatory milestone must not become a low-priority task merely because it is temporally distant.

## Decision

### 1. Use one-operation/one-approval as the default

An approval covers one clearly described operation and its declared side effects. Do not split one operation into field-by-field prompts merely because the internal schema stores several consent fields.

Use a preliminary approval only when the system must read material outside the already authorized conversation, task contract, or user-supplied inputs. The final creation approval remains required after that material has been minimized and summarized.

### 2. Make environment initialization one approved operation

Before discovery, state in one concise prompt:

- purpose: select tools the skill can use;
- default scope: command availability, installed skills, local model runtimes/names, and minimal platform compatibility facts;
- exclusions: credentials, secret or environment-variable values, file contents, unrelated paths, and recursive home-directory inspection;
- side effect: save the observed result in the total skill's private machine profile, never in a child project or export.

After approval, discover and save in one operation, then report the result. Do not ask for a second save confirmation. Mark availability as observed rather than proven usable; later successful use may upgrade a capability to verified. CPU, memory, accelerator, or broader resource inspection is optional and needs a stated tool-selection reason or explicit user request.

Existing profiles remain readable. The legacy `detect` and explicit `save` path may remain for diagnostics and user-directed edits, but it is not the ordinary first-run interaction.

### 3. Approve `.llmpack` creation as a whole

A user request or automatic trigger may prepare a draft and deterministic preview within the already accepted task contract. Before the final `.llmpack` file is created, show one concise preview containing:

- package type, reason, bound project/task, base revision, and destination;
- counts or summaries of included sections;
- every attachment path and relevant size/hash metadata;
- explicit privacy exclusions;
- confirmation that creation is local and does not authorize upload or sharing.

One user approval authorizes final creation of exactly that preview. The exporter binds approval to a canonical preview hash and fails without the approval hash or if the handoff draft, attachment set, destination, project identity, or base revision changes. Preview preparation does not itself create a final package.

Unpacking remains different: package presence and creation approval do not accept any claim or proposed change. The integrator still presents itemized decisions and commits only accepted items.

### 4. Make ordinary feedback one approval, with a conditional second gate

When feedback uses only the current authorized conversation and user-supplied problem description, prepare the minimized issue and redaction preview, then request one whole-preview approval. Do not ask for a separate local-collection confirmation.

If preparing feedback requires reading new files, logs, environment information, or another private source, first ask permission for that bounded collection. After collection and redaction, request the normal whole-preview approval. Thus ordinary feedback has one approval and extended feedback has two.

Keep `ltpm-framework-feedback/v1` package compatibility for v0.6.1. A single final approval may populate the existing collection and export audit fields with one approval event when no new collection was required; the collection scope records that only already authorized context was used. When extra collection occurred, retain its earlier approval record. The user approves the package preview as a whole rather than answering separately for the eight internal content sections.

Developer intake continues to accept v0.6.0 packages. Retention and permission to propose a non-reconstructive synthetic derivative remain visible choices in the final preview, not additional mandatory conversational rounds.

### 5. Clarify priority semantics without data migration

Retain `load_priority: high/low` for framework loading and task-board `high/low` for scheduling compatibility. Runtime guidance must explain task priority as foreground/background scheduling. Objective, milestone, dependency, and task relationships represent goal hierarchy and time order; neither is inferred from task priority alone.

No project-data schema migration or child adapter update is required for these wording and shared-runtime changes.

## Compatibility and versioning

- Keep entry protocol 1 and all v0.6.0 project data schemas.
- Keep `.llmpack` format v1; approval is an exporter-side preview contract, not receiver authority.
- Keep `ltpm-framework-feedback/v1` readable and writable; simplify how the runtime produces its existing consent audit fields.
- Preserve old private machine profiles and treat legacy `user-confirmed` observations as usable but not proof that each capability was successfully invoked.
- Existing compatible children inherit v0.6.1 through the total skill without adapter or project-data migration.

## Required validation contract

Implementation must demonstrate with synthetic fixtures:

1. environment initialization performs no detection or save before approval, then detects and saves after one approval without a second prompt;
2. default discovery excludes secret values, file contents, unrelated paths, and broad resource scanning;
3. discovered and verified capability states are not conflated;
4. handoff preview creates no `.llmpack`, and export without a matching approved preview hash fails without side effects;
5. changes to destination, project/revision, handoff content, or attachments invalidate approval;
6. one matching approval creates a valid v1 `.llmpack`, while integration still requires itemized decisions;
7. ordinary feedback exports after one whole-preview approval and records that no new collection was needed;
8. feedback requiring new private/external reads refuses collection without the preliminary bounded approval;
9. v0.6.0 feedback packages remain verifiable and acceptable to developer intake;
10. no discovery or package workflow implies upload, sharing, truth, authenticity, or formal acceptance.

These are new feature-contract tests derived from the user's accepted framework requirement. They do not retain or reconstruct any real feedback package.

## Consequences

- User interaction becomes shorter without weakening the boundary around new private reads or final file creation.
- Internal consent records remain detailed, but the user normally sees one meaningful decision rather than schema mechanics.
- Tool-level preview hashing prevents approved content from drifting before export, although it is not cryptographic proof of human identity.
- Automatic package triggers can preserve progress by preparing a draft, but they cannot silently create the final transport file.
- ADR-0015 supersedes ADR-0014's requirement that every feedback use two separate consent gates and narrows its corresponding validation requirement. All other ADR-0014 privacy, external-data, manual-transport, and developer-intake decisions remain in force.

## Alternatives rejected

- **No approval for local package creation.** Local writes and attachment copies are still material side effects.
- **Always require two approvals.** Current authorized context does not need to be re-authorized as a separate collection operation.
- **Approve every schema field separately.** This exposes implementation details without improving the user's understanding of the operation.
- **Treat the initial request “package this” as final approval.** The user has not yet seen the actual contents, destination, and exclusions.
- **Use package approval as integration acceptance.** Transport authority and formal project authority remain distinct.
- **Create new package schema versions solely for prompt simplification.** Existing formats can express the required audit facts and should remain compatible.

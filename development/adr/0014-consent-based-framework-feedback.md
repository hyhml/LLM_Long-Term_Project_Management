# ADR-0014: Consent-based runtime-to-developer framework feedback

- Status: Accepted
- Date: 2026-09-22
- Implemented in: `0.6.0-dev.1`

## Context

Real project use can expose reusable framework problems that synthetic development tests did not predict. A child skill needs a way to recognize and describe such a problem, while the developer needs a reproducible intake path. Automatically uploading conversations, copying project stores, or treating every reported symptom as a confirmed framework defect would violate the product's authority, privacy, and external-regression-data boundaries.

The trigger must also include a user's own suspicion. A user may notice framework-related behavior before it is reproducible or before the model identifies an invariant violation. Ignoring that signal would make the feedback channel too narrow.

## Decision

Add a separate runtime-to-developer feedback protocol with these boundaries:

1. A user-raised problem that may involve the framework always triggers provisional classification. Observed reusable failures, invariant violations, repeated ambiguities, unsafe allowances, blocked valid actions, and credible data-loss/privacy risks also trigger it.
2. Runtime classification is explicitly provisional. Cause categories are separate from remediation scope because a shared-runtime fix, child-adapter upgrade, project-data migration, documentation change, or environment action may be required independently of the initial symptom.
3. Local evidence collection and final export are two separate consent gates. The export gate covers each included field and attachment after a redaction report. Refusing feedback never blocks safe project work.
4. The runtime creates one `.ltpm-feedback` file with a manifest, issue, redaction report, optional individually approved attachments, and SHA-256 integrity. It does not upload, transmit, authenticate, accept, or execute anything.
5. Feedback transport is distinct from `.llmpack`. It does not enter project authority or the project's cross-conversation integration workflow. Drafts and final feedback use a user-selected external location by default.
6. Developer intake treats the package and all attachments as untrusted data. It verifies and summarizes without execution, quarantines only outside the repository, reclassifies through itemized triage, and honors the authorized retention scope.
7. Real packages and triage data remain external `data:regression`. Permission to propose a synthetic derivative is separate from permission to read or retain the original. Only an accepted, non-identifying, non-reconstructive synthetic reproduction may enter repository tests.
8. The developer may return a versioned, non-mutating resolution receipt linked by `feedback_id`. It records final disposition, classification, affected and fixed versions, fix reference, and child action.

## Consequences

- Existing compatible thin children inherit most behavior through the total skill; newly generated children also contain a short discovery route. A child adapter upgrade is not required solely to receive the shared feedback protocol.
- The runtime release gains the protocol, issue schema, and exporter/verifier. Developer intake, ADRs, tests, and real feedback stores remain outside the user bundle.
- Integrity does not establish sender identity, truth, developer acceptance, or root cause. Package signatures remain a separate deferred feature.
- No central server, account, telemetry, or automatic GitHub issue creation is introduced. The user controls transport.
- Limited evidence must be reported as limited coverage rather than used to rule out a framework cause.

## Required validation

Synthetic tests must demonstrate absent-consent rejection, exact attachment approval, integrity and archive-path safety, safe inspection, external-only quarantine, no attachment execution, release-boundary correctness, and non-mutating resolution receipts.

## Alternatives rejected

- **Reuse `.llmpack`.** Project integration and framework feedback have different receivers, authority, retention, and privacy boundaries.
- **Automatically upload diagnostics.** This removes meaningful review of the exact exported scope and creates an undeclared telemetry channel.
- **Store all feedback in the project.** Framework incidents are not accepted project facts and may expose project/private material through unrelated lifecycle operations.
- **Accept the runtime classification as final.** The report observes symptoms under limited coverage; developer triage must determine disposition independently.

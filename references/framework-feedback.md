# Consent-based framework feedback

Use this protocol when a user raises a problem that may involve the framework, or when the child or total skill observes a potentially reusable framework failure. This channel reports candidates for developer triage; it does not decide root cause and does not update project authority.

## Trigger and classify

Trigger this protocol when any of the following occurs:

- the user actively raises a problem that may be related to the framework during use;
- a generator, validator, retrieval, transaction, package, binding, or upgrade operation fails in a potentially reusable way;
- a documented invariant is violated or narrowly avoided;
- a valid action is blocked, an unsafe action is allowed, or project isolation, privacy, revision, or data-loss risk appears;
- the same ambiguity or failure pattern recurs;
- the user explicitly asks to prepare feedback for the framework developer.

First give a provisional classification with uncertainty and relevant alternatives:

- `framework-defect-candidate`
- `child-adapter-defect`
- `project-data`
- `project-specific`
- `environment`
- `external-tool`
- `usage-or-documentation`
- `unknown`

Separately propose a remediation scope: `shared-runtime-fix`, `child-adapter-upgrade`, `project-data-migration`, `documentation-only`, `environment-only`, or `unknown`. A framework candidate may later be reclassified by the developer. Tool success, package integrity, or the user's report does not prove root cause.

Ordinary reasoning mistakes, project-specific facts, and one-off external outages do not automatically become framework defects. They may still enter provisional classification when the user believes the framework may be involved.

## Preserve the active task

Feedback is an optional side path. Report the suspected risk and ask whether to continue the project task, pause an unsafe operation, or prepare feedback. Refusal to provide feedback does not block safe project work. Stop only the unsafe action when continuing it risks unauthorized writes, privacy leakage, project mixing, or data loss.

Do not put framework-feedback evidence in `records/`, `state/`, `sources/`, `views/`, or the project index. Do not treat a feedback export as a project handoff. Use a user-selected external temporary location for drafts and the final package. Store a project-local pointer or note only through the ordinary project proposal and commit process when it has project value.

## Two consent gates

1. Before inspecting or copying diagnostic material, propose the minimum collection scope. State what will and will not be inspected. Collect only after the user approves that local scope.
2. Before export, show every field and attachment proposed for inclusion plus the redaction report. Let the user accept, modify, or exclude each item. Export only after explicit approval of the final scope.

Collection approval does not authorize export, transmission, retention, or test derivation. Export approval does not upload anything. The user manually transfers the `.ltpm-feedback` file to the developer.

Never include secrets, credentials, full conversations, whole project stores, the private machine profile, unrelated private paths, or unnecessary copyrighted material by default. Prefer pseudonymous project aliases and minimal excerpts. Report inspected scope, uninspected scope, and known evidence gaps.

## Feedback file

Prepare `issue.json` and `redaction-report.json` according to [feedback-schema.json](feedback-schema.json). The issue records observed and expected behavior, reproduction, impact, provisional classification, remediation scope, coverage, privacy decisions, consent, and the requested outcome. The export approval must enumerate all eight content sections—`producer`, `problem`, `classification_proposal`, `context`, `evidence`, `privacy`, `request`, and `redaction-report`—after the user reviews them; the exporter rejects partial, duplicate, or undeclared section approval.

The single-file export has extension `.ltpm-feedback` and contains:

```text
manifest.json
issue.json
redaction-report.json
attachments/...        # optional and individually approved
```

Run:

```bash
python3 scripts/feedback.py export \
  --issue /external/draft/issue.json \
  --redaction-report /external/draft/redaction-report.json \
  --output /external/outbox/problem.ltpm-feedback \
  --attachment /path/to/minimal.txt=attachments/minimal.txt
```

Omit `--attachment` when none is needed. Every archive destination must appear in `consent.export.approved_attachments`. The exporter refuses absent consent, an unconfirmed redaction report, unsafe paths, symlinks, unapproved attachments, existing output, or excessive content.

Verify or inspect without extracting or executing attachments:

```bash
python3 scripts/feedback.py verify /external/outbox/problem.ltpm-feedback
python3 scripts/feedback.py inspect /external/outbox/problem.ltpm-feedback
```

The output hash proves only byte integrity. The package is not authenticated, accepted, trusted, or automatically submitted.

## Retention and regression boundary

The user chooses `one-shot`, `until-resolved`, or `long-term-regression-candidate` retention and separately decides whether a non-reconstructive synthetic derivative may be proposed. The developer must still present an itemized retention and regression-test proposal. Real feedback remains in an authorized external store and never enters the framework repository or runtime release.

Only an accepted synthetic reproduction that cannot reconstruct private or project-specific source material may enter developer tests. A resolution receipt may later link the feedback ID to final classification, affected versions, fixed release, and any required child action; importing that receipt never changes project data automatically.

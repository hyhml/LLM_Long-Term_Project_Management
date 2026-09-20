# ADR-0010: Regression-test policy and external case boundary

- Status: Accepted
- Date: 2026-09-20
- Implemented in: `0.4.0-dev.1`

## Context

Framework tests are valuable only when they protect stable behavior. Adding a test for every edit would create a brittle implementation mirror, while storing real user failures in the framework repository could mix private or project-specific data into distributed code. The framework therefore needs both a necessity rule and a clear distinction between test machinery and test data.

## Decision

Maintain a small invariant suite for the framework's essential promises:

1. the exploration, package, verification, proposal, acceptance, and commit loop remains usable across conversations;
2. authoritative, pending, derived, indexed, packaged, developer-only, and external-data boundaries remain distinct;
3. important writes require itemized user decisions and advance revision exactly once;
4. stable project identity cannot be silently replaced;
5. derived views and indexes remain reproducible from authority;
6. retrieval and release claims preserve coverage, privacy, audience, and distribution limits.

Add or revise a regression test when a reproducible event reveals a reusable framework defect, including a user correction, invariant violation or near miss, repeated ambiguity, data-loss/conflict/privacy risk, or shared-component failure. A typo, duplicate case, unaccepted behavior, non-reproducible anecdote, or unsanitizable private example does not by itself justify a repository test.

Regression handling follows proposal before persistence:

```text
capture under temporary work authority
-> minimize and redact
-> classify framework code separately from case data
-> propose the regression item and storage boundary
-> obtain the required user decision
-> add the smallest invariant-level test
-> demonstrate failure before and success after when practical
-> record the covered invariant
```

Test code and non-identifying synthetic fixtures are framework material. Real regression cases, retrieval evaluation sets, historical failure corpora, and standard answers are external `data:regression` or `data:evaluation` material and require their own user-approved location, access, and versioning. They are never silently committed, bundled in the runtime skill, or converted into synthetic fixtures if reconstruction could expose the source.

When an intended framework change alters an invariant, update the ADR and test contract first, then the tests, then the implementation. Never weaken a test merely to make an unintended regression pass.

## Scope

Generic integrity, path-safety, privacy-boundary, and package-import tests remain core engineering tests. Domain-specific educational safety and adversarial suites are outside the current framework scope.

The detailed developer workflow is maintained in `development/policies/regression-testing.md` and is excluded from the runtime branch.

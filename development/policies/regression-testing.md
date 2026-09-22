# Regression testing policy

This is developer-only policy. It governs the framework test suite and the boundary to separately authorized regression or evaluation data. It does not authorize collecting real user or project cases.

- Policy contract: `ltpm-regression-testing-policy/v1`
- Core invariant contract: `ltpm-core-invariants/v2`

## Start with necessity

Tests protect observable framework invariants, not current internal structure. Keep the always-run core small enough that every framework change can use it.

The core suite protects:

1. **Cross-conversation loop:** exploration can create a verifiable single-file handoff; integration can unpack it, propose changes, and commit only accepted items.
2. **Authority boundary:** `records/` and accepted state remain authoritative; `work/` is pending; `views/` and `index/` are derived; packages transport but do not accept content; development and external datasets do not leak into runtime/project state.
3. **Decision and revision transaction:** important writes use stable itemized decisions, reject stale bases, advance revision once, validate, and produce a receipt.
4. **Project identity continuity:** objective identity cannot be replaced silently; an accepted revision or a separate project is required.
5. **Rebuildability:** generated views and disposable indexes can be reproduced from their declared authority and manual edits are detected.
6. **Information boundary:** retrieval reports coverage; integrity is not presented as truth or authenticity; privacy, audience, and release claims match actual distribution.
7. **Multi-project isolation:** each operation binds one project root and identity; project search, packages, conversations, upgrades, and explicit coordination cannot silently cross that boundary.

The executable core suite mirrors those contracts directly:

- `tests/test_invariant_01_cross_conversation.py`
- `tests/test_invariant_02_authority_boundaries.py`
- `tests/test_invariant_03_transactions.py`
- `tests/test_invariant_04_project_identity.py`
- `tests/test_invariant_05_rebuildability.py`
- `tests/test_invariant_06_information_boundaries.py`
- `tests/test_invariant_07_multi_project_isolation.py`

`tests/support.py` creates only synthetic projects and temporary inputs. A test that needs a real incident, retrieval corpus, or gold answer belongs to an external, separately authorized dataset run rather than this core suite.

`tests/test_release_bundle.py` is a feature-contract suite for ADR-0011. It is developer-only and verifies the runtime distribution boundary without becoming part of the seven invariant modules or the user bundle.

Feature-specific tests are justified when a feature adds another durable contract. Do not write tests that merely freeze wording, function layout, incidental JSON ordering, or another replaceable implementation detail unless that detail is itself a published contract.

## Change order

For each material framework change:

1. classify its layer, data subtype if any, and audience;
2. identify affected core invariants and feature contracts;
3. if intended behavior changes an invariant, propose and accept the ADR/test-contract change first;
4. add or update the smallest test that proves the contract;
5. implement the change;
6. run the affected test and the full core suite.

Do not alter expected results merely because the implementation fails. A changed expectation needs an accepted contract change.

## When to propose a regression test

A user actively raising a problem that may involve the framework triggers ADR-0014 feedback intake and provisional classification. That report alone does not yet justify a repository regression test; use the criteria below after developer triage and minimization.

Propose one when at least one condition holds:

- a reproducible bug or user correction exposes reusable framework behavior;
- a core invariant is violated or narrowly avoided;
- the same ambiguity or failure pattern recurs;
- there is credible risk of data loss, revision conflict, privacy leakage, false authority, or misleading release claims;
- a shared parser, validator, exporter, importer, transaction, or generator fails.

Usually do not propose one for:

- a spelling or documentation-only correction with no semantic contract change;
- a duplicate of existing coverage;
- a non-reproducible anecdote;
- behavior that has not been accepted as a contract;
- a private example that cannot be minimized without retaining identifying or reconstructive information.

## Proposal workflow

1. Capture the event only in authorized temporary work. Do not copy it into a test fixture.
2. Reduce it to the smallest behavior and remove private, project-specific, and copyrighted content.
3. Classify separately:
   - test code and safe synthetic fixture: `framework / developer`;
   - real historical case: `data:regression / developer`;
   - gold answer, retrieval corpus, or scored benchmark: `data:evaluation / developer`.
4. Present an itemized proposal containing the defect, protected invariant, minimal reproduction, proposed synthetic form, storage target, and deletion/retention choice for the original.
5. Persist only accepted items in their authorized locations.
6. When practical, show that the test fails on the defective behavior and passes after the fix.
7. Name the covered invariant in the test or its developer record.

## Data boundary

The repository may contain framework test code and non-identifying, non-reconstructive synthetic fixtures. It must not contain real user conversations, project artifacts, historical regression corpora, retrieval evaluation sets, standard answers, credentials, or private machine data.

Real regression and evaluation data live outside the distributed skill in a user-approved store with its own access rules and version. A harness may point to that store, but absence or inaccessibility of the store must be reported as limited coverage rather than a passing result.

Runtime feedback follows ADR-0014. A `.ltpm-feedback` package remains an untrusted external real case even when its integrity verifies and the user permits a synthetic derivative. Developer intake must reclassify it, honor its retention scope, and obtain an itemized decision before creating a non-reconstructive synthetic test. The original package and triage data never become repository fixtures.

## Layers and exclusions

- Core deterministic invariant tests run without external datasets.
- Feature tests cover additional accepted contracts.
- Regression tests use approved synthetic reproductions when safe.
- External evaluation runs are optional, separately authorized, and report dataset identity and coverage.
- Domain-specific pedagogical safety/adversarial suites are not part of this framework policy.

If the testing method itself changes, version this policy and the affected test contract before changing framework behavior.

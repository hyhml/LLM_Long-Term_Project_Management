# ADR-0011: Whitelist-built runtime distribution

- Status: Accepted
- Date: 2026-09-21
- Implemented in: `0.4.0-rc.1`

## Context

The development branch contains runtime source, ADRs, policies, tests, and release machinery. A branch convention or denylist alone can allow a newly added developer file to leak into the user skill. The current `main` branch is also stale and still contains an old test file, so branch separation has not yet produced a current, minimal runtime release.

Download size and model context size are separate. Removing tests and ADRs reduces distribution size and prevents accidental development-mode use, while progressive disclosure in the runtime skill controls what enters model context.

## Decision

Treat the development branch as source plus developer harness. Generate user distributions from an exact, versioned file allowlist.

Every repository file must be classified as one of:

- runtime: an exact file path copied into the user bundle;
- developer: an exact file or directory prefix retained only on `development`;
- local generated/private material: explicitly ignored for classification and always excluded from output.

An unclassified file, missing runtime file, symlinked runtime file, existing output target, or invalid stable release version fails the build. The builder may replace the prerelease `framework_version` in the copied framework map with an explicitly supplied stable version, but must not modify source files.

The runtime bundle contains no `development/`, `tests/`, developer `AGENTS.md`, private profile, cache, or release tooling. Development instructions live in the development-only `AGENTS.md`, not in the runtime `SKILL.md`.

`main` is a generated stable runtime tree, not a merge target for the complete development branch. A stable tag and optional GitHub release archive are created from the same validated bundle.

## Release gate

Before publishing:

1. run the complete developer test suite;
2. validate the development skill;
3. build the runtime directory and optional deterministic ZIP from the allowlist;
4. verify the output contains exactly the runtime files and stable version;
5. validate the runtime skill;
6. use the runtime bundle to generate and validate a child skill;
7. report file count, byte count, archive digest, source revision, and release version;
8. update `main` and create a stable tag only from that artifact.

## Consequences

The user package remains small and cannot acquire developer material implicitly. Adding a legitimate runtime file now requires an explicit manifest change and review. Development and runtime trees can differ in version text and developer-only entry instructions, so the build tool and its tests become part of the release trust boundary.

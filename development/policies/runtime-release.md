# Runtime release policy

This is developer-only policy. User distributions are generated artifacts, never copies of the complete development tree.

- Policy contract: `ltpm-runtime-release-policy/v1`
- Manifest: `development/release/runtime-allowlist.json`
- Builder: `development/release/build_runtime.py`
- Governance priority: high
- Load priority: conditional; read this policy only for runtime builds, `main` updates, tags, or releases

Once a release task begins, this policy is foreground work. It does not apply to ordinary design-only or implementation-only changes.

## Classification boundary

- `runtime_files` is an exact allowlist. Only these files enter a user bundle.
- `developer_files` and `developer_prefixes` remain on `development` and must not appear in output.
- local private data, Git metadata, caches, and compiled Python files are ignored during source classification and always excluded.
- every other source file is unclassified and blocks the build.

Do not solve an unclassified-file failure by broadly allowing a directory. Decide whether the file is runtime or developer material, then add the narrowest path classification.

## Build and verify

Run from the repository root:

```bash
python3 development/release/build_runtime.py \
  --release-version 0.5.0 \
  --output-dir /new/runtime/directory \
  --archive /new/long-term-project-manager-v0.5.0.zip
```

Both output targets must be absent. The builder audits source classification before creating either target, copies exact runtime files, injects the stable version only into the copied framework map, verifies the output set, and creates a deterministic ZIP when requested.

## Release execution

Before running commands, map each release claim to one evidence-producing gate and note what later change would invalidate it. Complete runtime sources and release metadata before the final gate whenever possible.

1. Run affected tests while implementing; after runtime sources are frozen, run the complete developer suite once.
2. Validate the development skill once.
3. Build the official runtime directory and archive once from the exact allowlist.
4. Verify the output set and stable version, validate the runtime skill, and generate and validate a child skill from that exact artifact.
5. Publish `main` by replacing its tracked tree with the validated runtime directory; do not merge `development` into `main`. Tag the resulting stable commit and publish the already validated archive.
6. Confirm remotely that `main`, the stable tag, and the GitHub Release metadata and asset presence match the intended release.
7. Write the release receipt from the evidence already collected.

Reuse valid evidence. Do not repeat the full suite, deterministic-build check, skill validation, or smoke checks merely to populate a receipt. Rerun only a gate invalidated by a later change:

- runtime source or runtime metadata changes invalidate affected tests, the final suite, and the built artifact;
- artifact changes invalidate artifact validation and publication evidence;
- tag, branch, or GitHub Release metadata changes invalidate only the corresponding remote confirmation;
- developer-only receipts or status documents written after publication require static checks, not a rebuild or runtime tests.

Run the complete release gate from ADR-0011, but satisfy each requirement with the single valid result planned above. The archive offered to users must be built from the same runtime content and its local SHA-256 must be reported.

Do not download the published archive again as a mandatory verification step. Remote confirmation of refs, Release metadata, asset name, size, and availability is sufficient; local archive validation and its reported digest remain the content-integrity evidence. Never claim a release exists from a local build alone.

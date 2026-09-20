# Runtime release policy

This is developer-only policy. User distributions are generated artifacts, never copies of the complete development tree.

- Policy contract: `ltpm-runtime-release-policy/v1`
- Manifest: `development/release/runtime-allowlist.json`
- Builder: `development/release/build_runtime.py`

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
  --release-version 0.4.0 \
  --output-dir /new/runtime/directory \
  --archive /new/long-term-project-manager-v0.4.0.zip
```

Both output targets must be absent. The builder audits source classification before creating either target, copies exact runtime files, injects the stable version only into the copied framework map, verifies the output set, and creates a deterministic ZIP when requested.

Run the complete release gate from ADR-0011. Publish `main` by replacing its tracked tree with the validated runtime directory; do not merge `development` into `main`. Tag the resulting stable commit. The archive offered to users must be built from the same runtime content and its SHA-256 must be reported.

After publishing, confirm remotely that `main`, the stable tag, and any GitHub release refer to the intended commit or artifact. Never claim a release exists from a local build alone.

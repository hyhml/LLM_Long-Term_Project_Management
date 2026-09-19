# Private machine profile

The profile is machine-local framework state, not project state. Its path is `private/local-environment.json` relative to this framework skill.

## First run

1. Run `python scripts/environment_profile.py detect` and inspect the JSON draft.
2. Remove irrelevant private paths and anything resembling a credential.
3. Show the user a concise proposal covering OS, architecture, CPU, memory, accelerators, command-line tools, installed skills, and locally discoverable model names.
4. Ask the user to correct omissions and inaccuracies.
5. Only after confirmation, write the confirmed JSON with `python scripts/environment_profile.py save --input <confirmed-json-file>`.

Detection is advisory. A command being present does not prove that credentials, network access, permissions, or a usable model are available.

## Updates

Update the profile only on the user's instruction. Present field-level proposed changes and save only accepted items. Increase `profile_revision` on every accepted update.

Project skills may read this file at runtime to select tools. They must not copy it into project state, commits, logs, or `.llmpack` exports. A handoff may include a minimal sanitized execution summary listing only capabilities actually used.

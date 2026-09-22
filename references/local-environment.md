# Private machine profile

The profile is machine-local framework state, not project state. Its path is `private/local-environment.json` relative to this framework skill.

## First run

Explain that the purpose is to select tools the skill can use. State that the bounded scan checks minimal platform compatibility, known command availability, installed skill names, and locally discoverable model names; it does not read credentials, arbitrary file contents, unrelated paths, or perform a broad hardware inventory.

After one user approval, run:

```bash
python scripts/environment_profile.py initialize --approved
```

This single operation discovers the bounded scope and privately saves `private/local-environment.json`. Report the result without asking for a second save approval. Command presence is discovered capability, not proof that credentials, network access, permissions, or a usable model are available.

Detection is advisory. A command being present does not prove that credentials, network access, permissions, or a usable model are available.

## Updates

Update the profile only on the user's instruction. The legacy `detect` and `save --input` commands remain available for diagnostics and explicit edits. Increase `profile_revision` on every accepted update.

Project skills may read this file at runtime to select tools. They must not copy it into project state, commits, logs, or `.llmpack` exports. A handoff may include a minimal sanitized execution summary listing only capabilities actually used.

# Explicit cross-project coordination

Use this mode only when the user explicitly requests comparison or coordination across named managed projects. It is read-mostly and does not replace either project's normal conversation binding.

Read compact maps with:

```bash
python scripts/coordinate_projects.py \
  --project-skill /absolute/project-a/.agents/skills/project-a \
  --project-skill /absolute/project-b/.agents/skills/project-b
```

Report every participating `project_id`, binding status, revision, searched scope, and unsearched scope. Read detailed records only when the comparison requires them and authorization covers them.

Never create a merged authority or multi-project transaction. If the analysis suggests changes, produce a separate proposal set for each destination `project_id`. Commit those proposals only from the respective project's separately bound context after its own user decisions, validation, revision handling, and receipt.

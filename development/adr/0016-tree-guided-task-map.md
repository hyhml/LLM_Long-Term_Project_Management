# ADR-0016: Research content tree guides the task-focused project map

- Status: Accepted
- Date: 2026-10-13
- Scope: Optional research workflow and derived project views
- Distribution: This ADR is developer-only; its implemented runtime rules are separately allowlisted.

## Decision

For a research project, accepted content questions, evidence assessments, dependencies, and gaps live in one optional `artifact` record marked `ltpm-research-content-tree/v1`. This is formal content in the existing record store, not a task board or a derived view. The validator checks stable node IDs, references, cycles, and optional task links. Projects without a tree remain valid.

Task planning follows the tree: gap → candidate task with acceptance evidence → itemized user decision → accepted task board. A completed task supplies evidence and potential tree changes for separate review; it does not close a research question automatically.

`project-map.json` and `project-map.md` become task-focused derived views. They display the objective, accepted tasks, and the tree artifact entry when one exists. Other formal records and sources remain retrievable through their formal locations. The map does not decide what research content exists or which task should be approved.

The record-store and project-map schemas remain unchanged because the tree is an optional typed `content` shape and the map's existing `nodes` list supports selective projection. The renderer marks the new projection as `render_project_views.py/v4`. A prior all-record view is accepted only when it matches the deterministic v3 projection; an explicit rebuild or accepted transaction replaces it with the task-focused projection without changing formal data or the project revision. No child adapter or project-data migration occurs as a side effect.

## Boundaries

- Tree, evidence, source, and task-board changes are separate proposal items, even if accepted into one revision.
- Source metadata is not source-body authorization; evidence references do not prove a claim.
- The validator proves reference shape and existence, not scientific quality or task priority.
- Real feedback stays outside the repository. Feature tests use synthetic projects.

## Validation

Synthetic tests must cover task-only map projection, a valid tree and task link, unknown references, dependency cycles, old-view compatibility, deterministic regeneration, and no automatic task-board change. A release gate must validate the exact runtime bundle and a generated child before installed behavior is claimed.

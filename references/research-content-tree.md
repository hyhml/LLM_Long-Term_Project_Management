# Research content tree

Use this optional structure for projects whose next work should be justified by research questions and evidence gaps. Read the project map to identify the current confirmed task, then read the accepted tree record for planning or task context. For **future** work, direction is tree → candidate task → user decision → task board and map; task results return as proposed evidence and tree changes.

## Formal shape

One accepted `artifact` record in `records/store.json` may have `content.schema: "ltpm-research-content-tree/v1"`. Its `content.nodes` is a non-empty list. Each node has a stable `node_id`, `title`, `question`, `parent_id` (string or `null`), `depends_on` (node IDs), `evidence_refs` (formal record or registered source IDs), `evidence_assessment` (a qualified statement, not a truth verdict), and `open_gaps` (strings). The validator checks uniqueness, existing references, and cycles. There may be at most one such tree artifact per project. Other projects need no tree.

```json
{
  "id": "artifact-research-tree",
  "kind": "artifact",
  "title": "Research content tree",
  "confirmation_status": "accepted",
  "content": {
    "schema": "ltpm-research-content-tree/v1",
    "nodes": [{
      "node_id": "question-001",
      "title": "Example question",
      "question": "Which evidence distinguishes the alternatives?",
      "parent_id": null,
      "depends_on": [],
      "evidence_refs": [],
      "evidence_assessment": "No independent check yet",
      "open_gaps": ["Compare the alternatives under the same conditions"]
    }]
  }
}
```

An accepted task can link to tree nodes through `content.research_tree_refs`. Each link has a `node_id`, `evidence_gap`, non-empty `acceptance_evidence` list, and `tree_update_after_task`. The validator checks that the node exists and these planning fields are present; it does not judge whether the proposed task is scientifically useful. A task can link to several nodes. A gap may inspire several candidate tasks.

## Review and commit

Keep new or changed nodes and candidate tasks under `work/` until review. Present tree changes, evidence or source changes, and task-board changes as separate items. The user may accept a tree revision without accepting a task, or accept a task while deferring a proposed tree change. Commit accepted items through one project transaction and regenerate the map. The map shows only the objective, accepted tasks, and the tree artifact entry; ordinary research records remain in formal storage and are read selectively. A task status of `done` never sets a tree node's evidence assessment or closes its gaps automatically.

Existing compatible children may retain a previously generated all-record map until an explicit derived-view rebuild or accepted transaction regenerates it. Rebuilding changes only `views/`; it does not alter formal project facts or advance the project revision.

# Formal project transaction

Use this protocol for task changes, exploration archival, handoff integration, candidate-tool retention decisions, relation changes, source registration, and project-contract revisions.

Read `references/data-model.md` before constructing or editing formal objects.

Before preparing a candidate, confirm that the accepted task contract classifies the work as `data:project` and names its write authority, storage targets, validation route, project-version route, and project-local release boundary. Route framework, regression/evaluation dataset, machine-environment, and private-user writes to separately authorized locations.

## Prepare

Read the current revision and create an isolated candidate:

```bash
python scripts/project_transaction.py prepare \
  --project-skill /absolute/project/.agents/skills/example-project \
  --operation-id descriptive-operation-id
```

Present every proposal separately. Record each user decision as `accepted`, `accepted-with-modification`, `rejected`, or `deferred`. Do not edit the live formal files. Apply only accepted changes to the candidate directory printed by the command.

Keep epistemic roles separate: a `claim` states an assertion, `evidence` records support, `attempt` records an action and outcome, `review` records an evaluation, and `decision` records an accepted project choice. Connect them with typed relations instead of collapsing them into one conclusion.

The decision ledger passed to commit is a JSON object with a non-empty `decisions` list. Every item requires `change_id`, `decision`, `operation`, `target`, and `reason`. An objective-contract change additionally requires an accepted `revise-objective` decision targeting `state/project.json#objective_contract`; keep `objective_id` unchanged and increment `objective_revision` once.

## Commit

```bash
python scripts/project_transaction.py commit \
  --project-skill /absolute/project/.agents/skills/example-project \
  --operation-id descriptive-operation-id \
  --decisions /absolute/path/decisions.json
```

The tool verifies the live base revision, validates the candidate at that revision, advances all formal components exactly once, regenerates the map, marks the retrieval index stale, validates again, publishes the files, and creates a receipt under `packages/archive/receipts/`. The tool validates the decision ledger but cannot infer whether every candidate edit corresponds to an accepted item; the maintainer/integrator must enforce that mapping during candidate editing and review.

This is a framework workflow transaction with in-process rollback. It is not crash-atomic storage: immutable snapshots and an atomic `HEAD` remain proposed in ADR-0001. Never claim stronger guarantees.

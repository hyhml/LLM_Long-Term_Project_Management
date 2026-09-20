# Accepted-write transaction

Use the installed framework's formal data model and `project_transaction.py` for every important project-management write.

Before preparing the candidate, confirm that the accepted task contract contains a `data:project` classification and a control plan naming project write authority, allowed storage targets, validation route, project version route, and project-local release boundary. Framework, regression-dataset, evaluation-dataset, environment, and private-user writes require their own authority and must not be smuggled into this transaction.

1. Prepare a candidate from the current live revision.
2. Present stable, itemized proposals and record every user decision.
3. Apply only accepted items to the candidate, never to live formal files.
4. Keep claims, evidence, attempts, reviews, and decisions as separate record kinds connected by typed relations.
5. Commit through the transaction tool. It validates the candidate, advances revision once, regenerates views, marks the index stale, validates the published state, and creates a receipt.

An objective revision requires an accepted `revise-objective` decision, an unchanged `objective_id`, and one `objective_revision` increment. A different objective becomes a related node or a new project.

The transaction has in-process rollback but is not crash-atomic storage.

The tool validates the decision ledger and candidate structure; the maintainer/integrator must still verify that every candidate edit corresponds to an accepted item.

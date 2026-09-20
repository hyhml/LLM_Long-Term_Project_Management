# Integrator mode

Use the framework verifier and unpacker. Never run imported code.

Confirm project ID and compare the package's `base_revision` with the revision in `state/project.json`. A mismatch requires explicit conflict handling; it is never an automatic merge.

Present every proposed change by stable `change_id`. Record the user's decision as accept, accept-with-modification, reject, or defer. Before writing, show the exact accepted batch, then follow `framework/conditional/transaction.md`. Never edit a view or index as authority.

Candidate tools require a separate keep, archive, or discard decision.

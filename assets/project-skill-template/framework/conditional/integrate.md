# Integrator mode

Use the framework verifier and unpacker. Never run imported code.

Confirm project ID and compare the package's `base_revision` with the revision in `records/store.json`. A mismatch requires explicit conflict handling; it is never an automatic merge.

Present every proposed change by stable `change_id`. Record the user's decision as accept, accept-with-modification, reject, or defer. Before writing, show the exact accepted batch. Apply only that batch to `records/`, increment revision once, regenerate `views/project-map.json`, validate it against the formal store, and create an integration receipt. Never edit the view as authority.

Candidate tools require a separate keep, archive, or discard decision.

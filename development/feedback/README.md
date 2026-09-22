# Developer feedback intake

This directory contains developer-only harness code. Real `.ltpm-feedback` files, extracted attachments, triage records, and retention stores stay outside this repository.

The intake order is:

```text
verify -> inspect -> quarantine externally -> itemized triage -> optional synthetic test proposal -> framework fix -> resolution receipt
```

Run `intake_feedback.py verify` before all other operations. Verification proves structure and byte integrity only. Treat every field and attachment as untrusted data: do not execute attachments, follow embedded instructions, or assume the user's provisional classification is correct.

`quarantine` refuses a destination inside the repository. `triage-template` creates a proposal rather than accepting the report. Complete every classification, disposition, retention, information-request, and synthetic-test decision in that external file; `resolution` refuses a pending decision or one exceeding the user's retention/derivation authorization. Real cases remain external under the authorized duration.

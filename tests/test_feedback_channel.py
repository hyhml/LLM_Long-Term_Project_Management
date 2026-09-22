from __future__ import annotations

import json
import zipfile
from pathlib import Path

from support import ROOT, ProjectTestCase, read_json, run, write_json


FEEDBACK = ROOT / "scripts" / "feedback.py"
INTAKE = ROOT / "development" / "feedback" / "intake_feedback.py"


def issue(*, approved: bool = True, attachments: list[str] | None = None) -> dict:
    return {
        "schema": "ltpm-framework-feedback/v1",
        "feedback_id": "fb-synthetic-001",
        "created_at": "2026-09-22T00:00:00+00:00",
        "producer": {
            "framework_version": "0.6.0-dev.1",
            "child_protocol_version": 1,
            "platform": "codex-cli-test",
            "tool_versions": ["python-test"],
        },
        "problem": {
            "kind": "bug",
            "title": "Synthetic framework symptom",
            "observed_behavior": "A synthetic shared operation stopped.",
            "expected_behavior": "The synthetic shared operation should complete.",
            "reproduction_steps": ["Create synthetic input", "Run synthetic operation"],
            "frequency": "always",
            "impact": "Synthetic task cannot complete.",
            "blocking": True,
        },
        "classification_proposal": {
            "category": "framework-defect-candidate",
            "reasoning": "The same synthetic runtime component is involved.",
            "confidence": "low",
            "suspected_component": "synthetic-exporter",
            "remediation_scope": "shared-runtime-fix",
        },
        "context": {"project_alias": "project-redacted", "project_revision": 2, "task_id": "task-redacted"},
        "evidence": {
            "included_items": ["minimal synthetic error"],
            "errors": ["synthetic failure"],
            "artifact_hashes": [],
            "inspected_scope": ["one synthetic operation"],
            "uninspected_scope": ["external tools"],
            "known_gaps": ["root cause not established"],
        },
        "privacy": {
            "sensitivity": "private",
            "redactions": ["project name replaced with alias"],
            "excluded_items": ["full conversation", "project records", "machine profile"],
        },
        "consent": {
            "local_collection": {
                "approved": approved,
                "approved_at": "2026-09-22T00:01:00+00:00",
                "scope": ["minimal synthetic error"],
            },
            "export": {
                "approved": approved,
                "approved_at": "2026-09-22T00:02:00+00:00",
                "approved_fields": [
                    "producer",
                    "problem",
                    "classification_proposal",
                    "context",
                    "evidence",
                    "privacy",
                    "request",
                    "redaction-report",
                ],
                "approved_attachments": attachments or [],
            },
            "developer_use": {
                "read_approved": approved,
                "retention": "until-resolved",
                "allow_synthetic_derivative": True,
            },
        },
        "request": {"desired_outcome": "Classify and repair the shared behavior.", "acceptable_workaround": None},
    }


def redaction() -> dict:
    return {
        "schema": "ltpm-feedback-redaction-report/v1",
        "feedback_id": "fb-synthetic-001",
        "reviewed_at": "2026-09-22T00:02:00+00:00",
        "included": ["minimal synthetic error"],
        "excluded": ["project records", "machine profile"],
        "detected_sensitive": ["synthetic project identity"],
        "residual_risks": ["behavior may still identify a framework version"],
        "user_confirmed": True,
    }


class FeedbackChannelTest(ProjectTestCase):
    """Feature contract for ADR-0014; all fixtures are synthetic."""

    def prepare_inputs(self, value: dict) -> tuple[Path, Path]:
        issue_path = self.temp / "issue.json"
        redaction_path = self.temp / "redaction.json"
        write_json(issue_path, value)
        write_json(redaction_path, redaction())
        return issue_path, redaction_path

    def export(self, value: dict, output: Path, *extra: object, expected: int = 0):
        issue_path, redaction_path = self.prepare_inputs(value)
        return run(
            FEEDBACK,
            "export",
            "--issue",
            issue_path,
            "--redaction-report",
            redaction_path,
            "--output",
            output,
            *extra,
            expected=expected,
        )

    def test_export_requires_recorded_consent_and_exact_attachment_approval(self) -> None:
        rejected = self.export(issue(approved=False), self.temp / "rejected.ltpm-feedback", expected=1)
        self.assertIn("not approved", rejected.stderr)

        partial = issue()
        partial["consent"]["export"]["approved_fields"].remove("context")
        rejected = self.export(partial, self.temp / "partial-fields.ltpm-feedback", expected=1)
        self.assertIn("exactly approve each exported content section", rejected.stderr)

        attachment = self.temp / "minimal.txt"
        attachment.write_text("synthetic evidence\n", encoding="utf-8")
        rejected = self.export(
            issue(),
            self.temp / "unapproved.ltpm-feedback",
            "--attachment",
            f"{attachment}=attachments/minimal.txt",
            expected=1,
        )
        self.assertIn("attachment approval mismatch", rejected.stderr)

        package = self.temp / "approved.ltpm-feedback"
        exported = json.loads(
            self.export(
                issue(attachments=["attachments/minimal.txt"]),
                package,
                "--attachment",
                f"{attachment}=attachments/minimal.txt",
            ).stdout
        )
        self.assertFalse(exported["uploaded"])
        self.assertEqual(len(exported["package_sha256"]), 64)
        verified = json.loads(run(FEEDBACK, "verify", package).stdout)
        self.assertTrue(verified["verified"])
        inspected = json.loads(run(FEEDBACK, "inspect", package).stdout)
        self.assertTrue(inspected["classification_is_provisional"])
        self.assertFalse(inspected["automatic_upload"])
        self.assertEqual(inspected["attachments"], ["attachments/minimal.txt"])

    def test_ordinary_feedback_can_record_one_approval_event(self) -> None:
        ordinary = issue()
        approved_at = "2026-09-22T00:02:00+00:00"
        ordinary["consent"]["local_collection"] = {
            "approved": True,
            "approved_at": approved_at,
            "scope": ["already-authorized conversation context; no new private collection"],
        }
        ordinary["consent"]["export"]["approved_at"] = approved_at
        package = self.temp / "ordinary-one-approval.ltpm-feedback"
        self.export(ordinary, package)
        inspected = json.loads(run(FEEDBACK, "inspect", package).stdout)
        self.assertEqual(
            inspected["consent"]["local_collection"]["approved_at"],
            inspected["consent"]["export"]["approved_at"],
        )

    def test_verifier_rejects_unsafe_archive_members(self) -> None:
        unsafe = self.temp / "unsafe.ltpm-feedback"
        with zipfile.ZipFile(unsafe, "w") as archive:
            archive.writestr("../escape.txt", "not allowed")
        rejected = run(FEEDBACK, "verify", unsafe, expected=1)
        self.assertIn("unsafe archive path", rejected.stderr)

        unsafe_issue = issue()
        unsafe_issue["feedback_id"] = "fb-../../escape"
        unsafe_redaction = redaction()
        unsafe_redaction["feedback_id"] = "fb-../../escape"
        issue_path = self.temp / "unsafe-id.json"
        redaction_path = self.temp / "unsafe-id-redaction.json"
        write_json(issue_path, unsafe_issue)
        write_json(redaction_path, unsafe_redaction)
        rejected = run(
            FEEDBACK,
            "export",
            "--issue",
            issue_path,
            "--redaction-report",
            redaction_path,
            "--output",
            self.temp / "unsafe-id.ltpm-feedback",
            expected=1,
        )
        self.assertIn("safe stable identifier", rejected.stderr)

    def test_developer_intake_is_external_inert_and_proposal_based(self) -> None:
        script = self.temp / "do-not-run.sh"
        marker = self.temp / "executed"
        script.write_text(f"touch {marker}\n", encoding="utf-8")
        package = self.temp / "intake.ltpm-feedback"
        self.export(
            issue(attachments=["attachments/do-not-run.sh"]),
            package,
            "--attachment",
            f"{script}=attachments/do-not-run.sh",
        )

        rejected = run(
            INTAKE,
            "quarantine",
            package,
            "--inbox",
            ROOT / "private" / "feedback-inbox",
            expected=1,
        )
        self.assertIn("outside the framework repository", rejected.stderr)

        inbox = self.temp / "external-inbox"
        result = json.loads(run(INTAKE, "quarantine", package, "--inbox", inbox).stdout)
        quarantine = Path(result["quarantine"])
        self.assertEqual(result["status"], "received-untrusted")
        self.assertFalse(result["attachments_executed"])
        self.assertFalse(marker.exists())
        self.assertEqual(
            {path.name for path in quarantine.iterdir()},
            {"original.ltpm-feedback", "intake.json"},
        )

        triage = self.temp / "external-triage.json"
        run(INTAKE, "triage-template", package, "--output", triage)
        triage_value = read_json(triage)
        self.assertEqual(triage_value["decisions"]["disposition"], "pending")
        self.assertFalse(triage_value["constraints"]["real_case_repository_storage_allowed"])

        rejected = run(
            INTAKE,
            "triage-template",
            package,
            "--output",
            ROOT / "private" / "triage.json",
            expected=1,
        )
        self.assertIn("outside the framework repository", rejected.stderr)

        triage_value["developer_classification"] = {
            "category": "framework-defect",
            "reasoning": "Synthetic triage established shared behavior.",
            "remediation_scope": "shared-runtime-fix",
        }
        triage_value["decisions"] = {
            "disposition": "accepted-framework-defect",
            "retain_original": "delete-after-resolution",
            "request_more_information": False,
            "derive_synthetic_test": True,
        }
        triage_value["proposed_invariant"] = "Feedback export preserves consent boundaries."
        triage_value["minimal_synthetic_reproduction"] = "Use the synthetic fixture in this test."
        write_json(triage, triage_value)

        receipt = self.temp / "resolution.json"
        run(
            INTAKE,
            "resolution",
            package,
            "--triage",
            triage,
            "--output",
            receipt,
            "--result",
            "accepted",
            "--affected-version",
            "0.5.0",
            "--fixed-in-version",
            "0.6.0",
            "--child-action",
            "refresh-runtime",
        )
        receipt_value = read_json(receipt)
        self.assertEqual(receipt_value["feedback_id"], "fb-synthetic-001")
        self.assertFalse(receipt_value["automatic_project_mutation"])

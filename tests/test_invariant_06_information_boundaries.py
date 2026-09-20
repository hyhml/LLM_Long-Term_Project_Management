from __future__ import annotations

import json

from support import ROOT, ProjectTestCase, handoff_with_change, read_json, run, write_json


class InformationBoundaryTest(ProjectTestCase):
    """Invariant 06: coverage, integrity, privacy, audience, and release claims stay qualified."""

    def test_empty_search_reports_coverage_not_global_absence(self) -> None:
        value = json.loads(
            run(
                ROOT / "scripts" / "search_project.py",
                "--project-skill",
                self.skill,
                "--query",
                "不存在的词语",
            ).stdout
        )
        self.assertEqual(value["results"], [])
        self.assertTrue(value["coverage"]["searched"])
        self.assertTrue(value["coverage"]["not_searched"])
        self.assertIn("does not establish absence", value["coverage"]["statement"])

    def test_source_registry_match_does_not_claim_source_body_was_opened(self) -> None:
        candidate = self.prepare("register-source")
        registry_path = candidate / "sources" / "registry.json"
        registry = read_json(registry_path)
        registry["sources"].append(
            {
                "source_id": "source-001",
                "source_type": "pdf",
                "title": "合成资料条目",
                "access_scope": "metadata-only",
                "confirmation_status": "accepted",
            }
        )
        write_json(registry_path, registry)
        decisions = self.write_decisions(
            "register-source.json",
            [self.accepted_decision("source-change-001", "register-source", "sources/registry.json#source-001")],
        )
        self.commit("register-source", decisions)
        value = json.loads(
            run(
                ROOT / "scripts" / "search_project.py",
                "--project-skill",
                self.skill,
                "--query",
                "合成资料",
            ).stdout
        )
        self.assertEqual(value["results"][0]["kind"], "source-registry-metadata")
        searched_source_scope = value["coverage"]["searched"][1]["scope"]
        self.assertIn("source bodies were not opened", searched_source_scope)

    def test_package_verification_claims_integrity_not_authenticity_or_acceptance(self) -> None:
        handoff_path = self.temp / "handoff.json"
        write_json(handoff_path, handoff_with_change())
        package = self.temp / "integrity-only.llmpack"
        run(
            ROOT / "scripts" / "handoff.py",
            "export",
            "--project-skill",
            self.skill,
            "--handoff",
            handoff_path,
            "--output",
            package,
        )
        value = json.loads(run(ROOT / "scripts" / "handoff.py", "verify", package).stdout)
        self.assertTrue(value["verified"])
        self.assertNotIn("authenticated", value)
        self.assertNotIn("trusted", value)
        self.assertNotIn("accepted", value)

    def test_machine_profile_detection_is_unconfirmed_and_sensitive_keys_are_rejected(self) -> None:
        profile = json.loads(run(ROOT / "scripts" / "environment_profile.py", "detect").stdout)
        self.assertEqual(profile["status"], "draft-unconfirmed")
        self.assertEqual(profile["profile_revision"], 0)

        unsafe_profile = self.temp / "unsafe-profile.json"
        write_json(unsafe_profile, {"api_token": "synthetic-secret-value"})
        rejected = run(
            ROOT / "scripts" / "environment_profile.py",
            "save",
            "--input",
            unsafe_profile,
            expected=1,
        )
        self.assertIn("sensitive key is not allowed", rejected.stderr)

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from support import ROOT, ProjectTestCase, handoff_with_change, read_json, run, write_json


class CrossConversationLoopTest(ProjectTestCase):
    """Invariant 01: an exploration handoff can reach one accepted formal commit."""

    def export_package(self, name: str = "handoff.llmpack") -> tuple[Path, dict]:
        handoff = handoff_with_change()
        handoff_path = self.temp / "handoff.json"
        write_json(handoff_path, handoff)
        package = self.temp / name
        exported = run(
            ROOT / "scripts" / "handoff.py",
            "export",
            "--project-skill",
            self.skill,
            "--handoff",
            handoff_path,
            "--output",
            package,
        )
        return package, json.loads(exported.stdout)

    def test_package_unpack_proposal_and_accepted_commit_close_the_loop(self) -> None:
        package, exported = self.export_package()
        self.assertEqual(exported["base_revision"], 0)
        self.assertEqual(exported["project_id"], read_json(self.skill / "state" / "project.json")["project_id"])

        verified = json.loads(run(ROOT / "scripts" / "handoff.py", "verify", package).stdout)
        self.assertTrue(verified["verified"])
        live_before = (self.skill / "records" / "store.json").read_bytes()

        unpacked = self.temp / "unpacked"
        run(ROOT / "scripts" / "handoff.py", "unpack", package, "--output-dir", unpacked)
        self.assertEqual((self.skill / "records" / "store.json").read_bytes(), live_before)
        proposal = read_json(unpacked / "handoff.json")["proposed_changes"][0]

        candidate = self.prepare("integrate-handoff")
        candidate_store_path = candidate / "records" / "store.json"
        candidate_store = read_json(candidate_store_path)
        candidate_store["records"].append(proposal["value"])
        write_json(candidate_store_path, candidate_store)
        decisions = self.write_decisions(
            "integration-decisions.json",
            [
                self.accepted_decision(
                    proposal["change_id"],
                    proposal["operation"],
                    proposal["target"],
                    proposal["reason"],
                )
            ],
        )
        committed = json.loads(self.commit("integrate-handoff", decisions).stdout)

        self.assertEqual(committed["old_revision"], 0)
        self.assertEqual(committed["new_revision"], 1)
        self.assertTrue(Path(committed["receipt"]).is_file())
        live_store = read_json(self.skill / "records" / "store.json")
        self.assertIn("claim-from-handoff", {record["id"] for record in live_store["records"]})

    def test_tampered_package_is_rejected_before_unpack(self) -> None:
        package, _ = self.export_package()
        tampered = self.temp / "tampered.llmpack"
        with zipfile.ZipFile(package, "r") as source, zipfile.ZipFile(tampered, "w") as destination:
            for info in source.infolist():
                data = source.read(info.filename)
                if info.filename == "handoff.json":
                    data += b" "
                destination.writestr(info, data)

        destination = self.temp / "tampered-output"
        rejected = run(
            ROOT / "scripts" / "handoff.py",
            "unpack",
            tampered,
            "--output-dir",
            destination,
            expected=1,
        )
        self.assertIn("handoff.json", rejected.stderr)
        self.assertFalse(destination.exists())

    def test_unsafe_archive_path_is_rejected_without_writing_outside_destination(self) -> None:
        package, _ = self.export_package()
        unsafe = self.temp / "unsafe.llmpack"
        with zipfile.ZipFile(package, "r") as source, zipfile.ZipFile(unsafe, "w") as destination:
            for info in source.infolist():
                destination.writestr(info, source.read(info.filename))
            destination.writestr("../escape.txt", b"must not escape")

        destination = self.temp / "unsafe-output"
        rejected = run(
            ROOT / "scripts" / "handoff.py",
            "unpack",
            unsafe,
            "--output-dir",
            destination,
            expected=1,
        )
        self.assertIn("unsafe archive path", rejected.stderr)
        self.assertFalse(destination.exists())
        self.assertFalse((self.temp / "escape.txt").exists())

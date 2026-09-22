from __future__ import annotations

import json
from pathlib import Path

from support import ROOT, ProjectTestCase, read_json, run, write_json


class DecisionRevisionTransactionTest(ProjectTestCase):
    """Invariant 03: accepted writes advance exactly once and failures do not publish."""

    def add_claim(self, candidate: Path, record_id: str = "claim-001") -> None:
        store_path = candidate / "records" / "store.json"
        store = read_json(store_path)
        store["records"].append(
            {
                "id": record_id,
                "kind": "claim",
                "title": "事务写入的主张",
                "confirmation_status": "accepted",
                "content": {"statement": "候选副本通过后才进入正式记录"},
            }
        )
        write_json(store_path, store)

    def test_accepted_batch_advances_once_creates_receipt_and_rejects_stale_base(self) -> None:
        stale_candidate = self.prepare("stale-change")
        self.assertFalse((stale_candidate / "SKILL.md").exists())
        candidate = self.prepare("add-claim")
        self.assertFalse((candidate / "SKILL.md").exists())
        self.assertEqual(list(self.skill.rglob("SKILL.md")), [self.skill / "SKILL.md"])
        self.add_claim(candidate)
        decisions = self.write_decisions(
            "accepted.json",
            [self.accepted_decision("change-001", "add-record", "records/store.json#claim-001")],
        )

        committed = json.loads(self.commit("add-claim", decisions).stdout)
        self.assertEqual(committed["old_revision"], 0)
        self.assertEqual(committed["new_revision"], 1)
        receipt = read_json(Path(committed["receipt"]))
        self.assertEqual(receipt["validation"], "passed")
        self.assertEqual(receipt["decisions"], read_json(decisions)["decisions"])
        self.assertFalse(candidate.exists())

        project = read_json(self.skill / "state" / "project.json")
        board = read_json(self.skill / "state" / "task-board.json")
        store = read_json(self.skill / "records" / "store.json")
        sources = read_json(self.skill / "sources" / "registry.json")
        project_map = read_json(self.skill / "views" / "project-map.json")
        self.assertEqual(project["revision"], 1)
        self.assertEqual({board["project_revision"], store["project_revision"], sources["project_revision"]}, {1})
        self.assertEqual(project_map["source"]["project_revision"], 1)

        stale = self.commit("stale-change", decisions, expected=1)
        self.assertIn("stale transaction", stale.stderr)
        self.assertEqual(read_json(self.skill / "state" / "project.json")["revision"], 1)

    def test_rejected_or_deferred_only_ledger_cannot_commit(self) -> None:
        self.prepare("nothing-accepted")
        decisions = self.write_decisions(
            "rejected.json",
            [
                {
                    "change_id": "change-001",
                    "decision": "rejected",
                    "operation": "add-record",
                    "target": "records/store.json#claim-001",
                    "reason": "用户未接受",
                },
                {
                    "change_id": "change-002",
                    "decision": "deferred",
                    "operation": "add-record",
                    "target": "records/store.json#claim-002",
                    "reason": "等待更多证据",
                },
            ],
        )
        rejected = self.commit("nothing-accepted", decisions, expected=1)
        self.assertIn("nothing was accepted", rejected.stderr)
        self.assertEqual(read_json(self.skill / "state" / "project.json")["revision"], 0)
        self.assertFalse((self.skill / "packages" / "archive" / "receipts" / "nothing-accepted.json").exists())

    def test_invalid_candidate_does_not_pollute_live_authority(self) -> None:
        live_before = (self.skill / "records" / "store.json").read_bytes()
        candidate = self.prepare("invalid-candidate")
        store_path = candidate / "records" / "store.json"
        store = read_json(store_path)
        store["records"].append(
            {
                "id": "claim-proposed",
                "kind": "claim",
                "title": "未确认内容",
                "confirmation_status": "proposed",
                "content": {},
            }
        )
        write_json(store_path, store)
        decisions = self.write_decisions(
            "invalid.json",
            [self.accepted_decision("change-001", "add-record", "records/store.json#claim-proposed")],
        )

        rejected = self.commit("invalid-candidate", decisions, expected=1)
        self.assertIn("unaccepted formal record", rejected.stderr)
        self.assertEqual((self.skill / "records" / "store.json").read_bytes(), live_before)
        self.assertEqual(read_json(self.skill / "state" / "project.json")["revision"], 0)
        self.assertFalse((self.skill / "packages" / "archive" / "receipts" / "invalid-candidate.json").exists())

    def test_committed_legacy_candidates_require_approved_cleanup(self) -> None:
        for number in (1, 2):
            operation = f"legacy-{number}"
            candidate = self.prepare(operation)
            self.add_claim(candidate, f"claim-{number}")
            decisions = self.write_decisions(
                f"accepted-{number}.json",
                [self.accepted_decision(f"change-{number}", "add-record", f"records/store.json#claim-{number}")],
            )
            committed = json.loads(self.commit(operation, decisions).stdout)
            self.assertEqual(committed["new_revision"], number)
            candidate.mkdir(parents=True, exist_ok=True)
            (candidate / "SKILL.md").write_text((self.skill / "SKILL.md").read_text(encoding="utf-8"), encoding="utf-8")

        self.assertEqual(len(list(self.skill.rglob("SKILL.md"))), 3)
        revision_before = read_json(self.skill / "state" / "project.json")["revision"]
        preview = json.loads(
            run(
                ROOT / "scripts" / "project_transaction.py",
                "cleanup-preview",
                "--project-skill",
                self.skill,
            ).stdout
        )
        self.assertEqual([item["operation_id"] for item in preview["eligible"]], ["legacy-1", "legacy-2"])

        changed_candidate = self.skill / preview["eligible"][0]["candidate"] / "changed-after-preview.txt"
        changed_candidate.write_text("preview scope changed\n", encoding="utf-8")
        stale = run(
            ROOT / "scripts" / "project_transaction.py",
            "cleanup-committed",
            "--project-skill",
            self.skill,
            "--approved-preview-sha256",
            preview["preview_sha256"],
            expected=1,
        )
        self.assertIn("approved cleanup preview", stale.stderr)
        changed_candidate.unlink()
        preview = json.loads(
            run(
                ROOT / "scripts" / "project_transaction.py",
                "cleanup-preview",
                "--project-skill",
                self.skill,
            ).stdout
        )

        cleaned = json.loads(
            run(
                ROOT / "scripts" / "project_transaction.py",
                "cleanup-committed",
                "--project-skill",
                self.skill,
                "--approved-preview-sha256",
                preview["preview_sha256"],
            ).stdout
        )
        self.assertEqual(cleaned["cleaned_operations"], ["legacy-1", "legacy-2"])
        self.assertTrue(Path(cleaned["receipt"]).is_file())
        self.assertEqual(read_json(self.skill / "state" / "project.json")["revision"], revision_before)
        self.assertEqual(list(self.skill.rglob("SKILL.md")), [self.skill / "SKILL.md"])

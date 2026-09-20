from __future__ import annotations

import json
from pathlib import Path

from support import ProjectTestCase, read_json, write_json


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
        self.prepare("stale-change")
        candidate = self.prepare("add-claim")
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

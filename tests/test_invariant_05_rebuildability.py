from __future__ import annotations

import json
from pathlib import Path

from support import ROOT, ProjectTestCase, read_json, run, write_json


class RebuildabilityTest(ProjectTestCase):
    """Invariant 05: derived state is deterministic and never becomes authority."""

    def test_map_rebuild_is_deterministic_and_ignores_pending_work(self) -> None:
        map_path = self.skill / "views" / "project-map.json"
        human_map_path = self.skill / "views" / "project-map.md"
        original = map_path.read_bytes()
        original_human = human_map_path.read_bytes()
        map_path.unlink()
        human_map_path.unlink()
        run(ROOT / "scripts" / "render_project_views.py", self.skill)
        self.assertEqual(map_path.read_bytes(), original)
        self.assertEqual(human_map_path.read_bytes(), original_human)
        self.assertIn(b"Derived, non-authoritative view", original_human)
        self.assertEqual(read_json(map_path)["authority"]["status"], "derived-non-authoritative")

        write_json(self.skill / "work" / "explorations" / "pending.json", {"claim": "pending"})
        run(ROOT / "scripts" / "render_project_views.py", self.skill)
        self.assertEqual(map_path.read_bytes(), original)
        self.assertEqual(human_map_path.read_bytes(), original_human)

    def test_human_view_exposes_review_sections_from_formal_data(self) -> None:
        store_path = self.skill / "records" / "store.json"
        store = read_json(store_path)
        store["records"].extend(
            [
                {
                    "id": "decision-human-map",
                    "kind": "decision",
                    "title": "保留人工审阅视图",
                    "confirmation_status": "accepted",
                    "content": {},
                },
                {
                    "id": "attempt-human-map",
                    "kind": "attempt",
                    "title": "人工编辑派生地图",
                    "confirmation_status": "accepted",
                    "content": {
                        "outcome": "failed",
                        "attempted": "直接编辑 Markdown",
                        "failure_reason": "派生文件不是事实来源",
                        "failure_conditions": "编辑没有对应正式记录",
                        "retry_conditions": "先提交正式记录",
                        "evidence_or_reproduction": "验证器拒绝人工改动",
                    },
                },
                {
                    "id": "risk-human-map",
                    "kind": "risk",
                    "title": "把派生视图误当权威",
                    "confirmation_status": "accepted",
                    "content": {},
                },
                {
                    "id": "evidence-human-map",
                    "kind": "evidence",
                    "title": "双视图来自同一 revision",
                    "confirmation_status": "accepted",
                    "content": {},
                },
            ]
        )
        store["relations"].extend(
            [
                {
                    "id": "relation-human-map-decision",
                    "from": "objective-001",
                    "type": "contains",
                    "to": "decision-human-map",
                    "confirmation_status": "accepted",
                },
                {
                    "id": "relation-human-map-evidence",
                    "from": "evidence-human-map",
                    "type": "supports",
                    "to": "decision-human-map",
                    "confirmation_status": "accepted",
                },
            ]
        )
        write_json(store_path, store)
        sources_path = self.skill / "sources" / "registry.json"
        sources = read_json(sources_path)
        sources["sources"].append(
            {
                "source_id": "source-human-map",
                "source_type": "document",
                "title": "人工地图反馈",
                "access_scope": "synthetic-test",
                "confirmation_status": "accepted",
            }
        )
        write_json(sources_path, sources)

        run(ROOT / "scripts" / "render_project_views.py", self.skill)
        run(ROOT / "scripts" / "validate_project.py", self.skill)
        human_map = (self.skill / "views" / "project-map.md").read_text(encoding="utf-8")
        for expected in (
            "## Objective",
            "### High priority",
            "### Low priority",
            "### Decisions",
            "### Attempts",
            "[outcome: failed]",
            "### Risks",
            "### Evidence",
            "## Sources",
            "source-human-map",
            "## Relations",
            "relation-human-map-evidence",
            "## Revision reference",
        ):
            self.assertIn(expected, human_map)

    def test_validator_detects_manual_derived_view_edit(self) -> None:
        map_path = self.skill / "views" / "project-map.json"
        project_map = read_json(map_path)
        project_map["nodes"][0]["title"] = "未经正式记录确认的修改"
        write_json(map_path, project_map)
        rejected = run(ROOT / "scripts" / "validate_project.py", self.skill, expected=1)
        self.assertIn("stale or manually edited", rejected.stdout)

    def test_validator_detects_manual_human_view_edit(self) -> None:
        human_map_path = self.skill / "views" / "project-map.md"
        human_map_path.write_text(
            human_map_path.read_text(encoding="utf-8") + "\nUnconfirmed manual claim.\n",
            encoding="utf-8",
        )
        rejected = run(ROOT / "scripts" / "validate_project.py", self.skill, expected=1)
        self.assertIn("views/project-map.md is stale or manually edited", rejected.stdout)

    def test_pre_human_map_child_remains_compatible_until_rebuilt(self) -> None:
        human_map_path = self.skill / "views" / "project-map.md"
        human_map_path.unlink()
        map_path = self.skill / "views" / "project-map.json"
        legacy_map = read_json(map_path)
        legacy_map.pop("authority")
        write_json(map_path, legacy_map)

        compatible = run(ROOT / "scripts" / "validate_project.py", self.skill)
        self.assertIn('"valid": true', compatible.stdout)
        self.assertIn("missing-compatible-rebuildable", compatible.stdout)

        candidate = self.prepare("create-human-map-for-legacy-child")
        store_path = candidate / "records" / "store.json"
        store = read_json(store_path)
        store["records"].append(
            {
                "id": "claim-legacy-human-map",
                "kind": "claim",
                "title": "旧项目通过正式事务生成 Markdown 地图",
                "confirmation_status": "accepted",
                "content": {},
            }
        )
        write_json(store_path, store)
        decisions = self.write_decisions(
            "legacy-human-map.json",
            [
                self.accepted_decision(
                    "change-legacy-human-map",
                    "add-record",
                    "records/store.json#claim-legacy-human-map",
                )
            ],
        )
        self.commit("create-human-map-for-legacy-child", decisions)
        self.assertTrue(human_map_path.is_file())
        self.assertEqual(read_json(map_path)["authority"]["status"], "derived-non-authoritative")
        run(ROOT / "scripts" / "validate_project.py", self.skill)

    def test_commit_marks_index_stale_and_keeps_view_on_new_authority_revision(self) -> None:
        candidate = self.prepare("rebuild-after-commit")
        store_path = candidate / "records" / "store.json"
        store = read_json(store_path)
        store["records"].append(
            {
                "id": "claim-rebuild",
                "kind": "claim",
                "title": "触发派生数据重建",
                "confirmation_status": "accepted",
                "content": {},
            }
        )
        write_json(store_path, store)
        decisions = self.write_decisions(
            "rebuild.json",
            [self.accepted_decision("change-001", "add-record", "records/store.json#claim-rebuild")],
        )
        committed = self.commit("rebuild-after-commit", decisions)

        project = read_json(self.skill / "state" / "project.json")
        project_map = read_json(self.skill / "views" / "project-map.json")
        human_map = (self.skill / "views" / "project-map.md").read_text(encoding="utf-8")
        index = read_json(self.skill / "index" / "manifest.json")
        self.assertEqual(project_map["source"]["project_revision"], project["revision"])
        self.assertIn(f"- Project revision: `{project['revision']}`", human_map)
        receipt = read_json(Path(json.loads(committed.stdout)["receipt"]))
        self.assertIn("views/project-map.md", {item["path"] for item in receipt["files"]})
        self.assertEqual(index["status"], "stale")
        self.assertIsNone(index["generated_from_revision"])
        self.assertTrue(index["coverage"]["exclusions"])

        before = (self.skill / "views" / "project-map.json").read_bytes()
        before_human = (self.skill / "views" / "project-map.md").read_bytes()
        run(ROOT / "scripts" / "render_project_views.py", self.skill)
        self.assertEqual((self.skill / "views" / "project-map.json").read_bytes(), before)
        self.assertEqual((self.skill / "views" / "project-map.md").read_bytes(), before_human)

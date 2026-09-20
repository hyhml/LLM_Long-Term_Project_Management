from __future__ import annotations

from support import ROOT, ProjectTestCase, read_json, run, write_json


class RebuildabilityTest(ProjectTestCase):
    """Invariant 05: derived state is deterministic and never becomes authority."""

    def test_map_rebuild_is_deterministic_and_ignores_pending_work(self) -> None:
        map_path = self.skill / "views" / "project-map.json"
        original = map_path.read_bytes()
        map_path.unlink()
        run(ROOT / "scripts" / "render_project_views.py", self.skill)
        self.assertEqual(map_path.read_bytes(), original)

        write_json(self.skill / "work" / "explorations" / "pending.json", {"claim": "pending"})
        run(ROOT / "scripts" / "render_project_views.py", self.skill)
        self.assertEqual(map_path.read_bytes(), original)

    def test_validator_detects_manual_derived_view_edit(self) -> None:
        map_path = self.skill / "views" / "project-map.json"
        project_map = read_json(map_path)
        project_map["nodes"][0]["title"] = "未经正式记录确认的修改"
        write_json(map_path, project_map)
        rejected = run(ROOT / "scripts" / "validate_project.py", self.skill, expected=1)
        self.assertIn("stale or manually edited", rejected.stdout)

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
        self.commit("rebuild-after-commit", decisions)

        project = read_json(self.skill / "state" / "project.json")
        project_map = read_json(self.skill / "views" / "project-map.json")
        index = read_json(self.skill / "index" / "manifest.json")
        self.assertEqual(project_map["source"]["project_revision"], project["revision"])
        self.assertEqual(index["status"], "stale")
        self.assertIsNone(index["generated_from_revision"])
        self.assertTrue(index["coverage"]["exclusions"])

        before = (self.skill / "views" / "project-map.json").read_bytes()
        run(ROOT / "scripts" / "render_project_views.py", self.skill)
        self.assertEqual((self.skill / "views" / "project-map.json").read_bytes(), before)

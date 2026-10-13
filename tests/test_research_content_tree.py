from __future__ import annotations

import sys

from support import ROOT, ProjectTestCase, read_json, run, write_json

sys.path.insert(0, str(ROOT / "scripts"))
from render_project_views import build_project_map, build_project_markdown, load_inputs  # noqa: E402


def sample_tree() -> dict:
    return {
        "id": "artifact-content-tree",
        "kind": "artifact",
        "title": "示例内容树",
        "confirmation_status": "accepted",
        "content": {
            "schema": "ltpm-research-content-tree/v1",
            "nodes": [
                {
                    "node_id": "question-root",
                    "parent_id": None,
                    "title": "核心问题",
                    "question": "哪些证据支持当前解释？",
                    "depends_on": [],
                    "evidence_refs": ["evidence-sample"],
                    "evidence_assessment": "初步材料，仍需复核",
                    "open_gaps": ["缺少独立复核"],
                },
                {
                    "node_id": "question-branch",
                    "parent_id": "question-root",
                    "title": "分支问题",
                    "question": "反例是否改变判断？",
                    "depends_on": ["question-root"],
                    "evidence_refs": [],
                    "evidence_assessment": "尚无证据",
                    "open_gaps": ["需要反例检验"],
                },
            ],
        },
    }


class ResearchContentTreeTest(ProjectTestCase):
    """A content tree guides proposals while the project map stays task-focused."""

    def add_tree(self) -> dict:
        path = self.skill / "records" / "store.json"
        store = read_json(path)
        store["records"].append(
            {
                "id": "evidence-sample",
                "kind": "evidence",
                "title": "示例证据",
                "confirmation_status": "accepted",
                "content": {},
            }
        )
        store["records"].append(sample_tree())
        write_json(path, store)
        return store

    def test_task_map_exposes_tree_entry_without_research_records(self) -> None:
        store = self.add_tree()
        store["records"][0]["content"]["research_tree_refs"] = [
            {
                "node_id": "question-branch",
                "evidence_gap": "需要反例检验",
                "acceptance_evidence": ["独立复核报告"],
                "tree_update_after_task": "审阅新证据并修订分支问题",
            }
        ]
        write_json(self.skill / "records" / "store.json", store)
        run(ROOT / "scripts" / "render_project_views.py", self.skill)
        run(ROOT / "scripts" / "validate_project.py", self.skill)

        project_map = read_json(self.skill / "views" / "project-map.json")
        self.assertEqual(
            {node["id"] for node in project_map["nodes"]},
            {"objective-001", "task-001", "task-002", "artifact-content-tree"},
        )
        self.assertEqual(project_map["navigation"]["research_content_tree"], "../records/store.json#artifact-content-tree")
        self.assertEqual(project_map["source"]["project_revision"], 0)
        self.assertNotIn("evidence-sample", (self.skill / "views" / "project-map.md").read_text(encoding="utf-8"))
        self.assertEqual(read_json(self.skill / "state" / "task-board.json")["tasks"]["high"][0]["status"], "pending")

    def test_invalid_tree_links_and_cycle_are_rejected(self) -> None:
        store = self.add_tree()
        store["records"][0]["content"]["research_tree_refs"] = [
            {"node_id": "missing", "evidence_gap": "缺口", "acceptance_evidence": ["报告"], "tree_update_after_task": "复核"}
        ]
        store["records"][-1]["content"]["nodes"][0]["depends_on"] = ["question-branch"]
        write_json(self.skill / "records" / "store.json", store)
        run(ROOT / "scripts" / "render_project_views.py", self.skill)
        rejected = run(ROOT / "scripts" / "validate_project.py", self.skill, expected=1)
        self.assertIn("dependency cycle", rejected.stdout)
        self.assertIn("unknown research tree node", rejected.stdout)

    def test_prior_all_record_map_is_accepted_until_rebuilt(self) -> None:
        self.add_tree()
        inputs = load_inputs(self.skill)
        old_view = build_project_map(*inputs, legacy=True)
        write_json(self.skill / "views" / "project-map.json", old_view)
        (self.skill / "views" / "project-map.md").write_text(
            build_project_markdown(*inputs, old_view, legacy=True), encoding="utf-8"
        )
        run(ROOT / "scripts" / "validate_project.py", self.skill)
        self.assertIn("evidence-sample", (self.skill / "views" / "project-map.md").read_text(encoding="utf-8"))

        run(ROOT / "scripts" / "render_project_views.py", self.skill)
        run(ROOT / "scripts" / "validate_project.py", self.skill)
        refreshed = read_json(self.skill / "views" / "project-map.json")
        self.assertEqual(refreshed["source"]["generator"], "render_project_views.py/v4")
        self.assertNotIn("evidence-sample", {node["id"] for node in refreshed["nodes"]})
        self.assertEqual(read_json(self.skill / "state" / "project.json")["revision"], 0)

    def test_accepted_tree_and_task_link_commit_in_one_revision(self) -> None:
        candidate = self.prepare("accept-research-tree")
        store_path = candidate / "records" / "store.json"
        store = read_json(store_path)
        store["records"].extend(
            [
                {
                    "id": "evidence-sample",
                    "kind": "evidence",
                    "title": "示例证据",
                    "confirmation_status": "accepted",
                    "content": {},
                },
                sample_tree(),
            ]
        )
        store["records"][0]["content"]["research_tree_refs"] = [
            {
                "node_id": "question-root",
                "evidence_gap": "缺少独立复核",
                "acceptance_evidence": ["复核报告"],
                "tree_update_after_task": "审阅后更新证据判断",
            }
        ]
        write_json(store_path, store)
        decisions = self.write_decisions(
            "accept-research-tree.json",
            [
                self.accepted_decision("add-evidence", "add-record", "records/store.json#evidence-sample"),
                self.accepted_decision("add-tree", "add-record", "records/store.json#artifact-content-tree"),
                self.accepted_decision("link-task", "update-record", "records/store.json#task-001"),
            ],
        )
        self.commit("accept-research-tree", decisions)
        run(ROOT / "scripts" / "validate_project.py", self.skill)
        self.assertEqual(read_json(self.skill / "state" / "project.json")["revision"], 1)
        self.assertEqual(read_json(self.skill / "views" / "project-map.json")["source"]["project_revision"], 1)

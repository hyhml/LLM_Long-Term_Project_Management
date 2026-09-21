from __future__ import annotations

import json

from support import ROOT, ProjectTestCase, read_json, run, valid_task_contract, write_json


class AuthorityBoundaryTest(ProjectTestCase):
    """Invariant 02: accepted, pending, derived, private, and developer data stay separate."""

    def test_generated_project_has_only_project_runtime_authority_layout(self) -> None:
        validated = json.loads(run(ROOT / "scripts" / "validate_project.py", self.skill).stdout)
        self.assertTrue(validated["valid"])
        framework_map = read_json(ROOT / "references" / "framework-map.json")
        instance = read_json(self.skill / "framework" / "instance.json")
        self.assertEqual(instance["last_adapter_update_with"], framework_map["framework_version"])
        self.assertEqual(instance["schema"], "ltpm-project-instance/v1")
        self.assertTrue((self.skill / "project-instructions.md").is_file())
        self.assertFalse((self.skill / "framework" / "conditional").exists())

        for relative in ("state", "records", "sources", "work", "views", "index", "packages"):
            self.assertTrue((self.skill / relative).is_dir())
        for excluded in ("development", "tests", "private", "database"):
            self.assertFalse((self.skill / excluded).exists())
        self.assertIn("allow_implicit_invocation: false", (self.skill / "agents" / "openai.yaml").read_text())

    def test_pending_work_cannot_change_derived_map(self) -> None:
        map_path = self.skill / "views" / "project-map.json"
        original = map_path.read_bytes()
        pending = self.skill / "work" / "explorations" / "unconfirmed.json"
        write_json(pending, {"claim": "not accepted"})
        run(ROOT / "scripts" / "render_project_views.py", self.skill)
        self.assertEqual(map_path.read_bytes(), original)

    def test_unaccepted_formal_record_is_rejected(self) -> None:
        store_path = self.skill / "records" / "store.json"
        store = read_json(store_path)
        store["records"].append(
            {
                "id": "claim-unaccepted",
                "kind": "claim",
                "title": "仍是提案",
                "confirmation_status": "proposed",
                "content": {},
            }
        )
        write_json(store_path, store)
        rejected = run(ROOT / "scripts" / "render_project_views.py", self.skill, expected=1)
        self.assertIn("unaccepted formal record", rejected.stderr)

    def test_project_task_contract_rejects_other_data_authorities(self) -> None:
        project_path = self.skill / "state" / "project.json"
        project = read_json(project_path)
        project["current_focus"]["task_contract"] = valid_task_contract()
        write_json(project_path, project)
        run(ROOT / "scripts" / "render_project_views.py", self.skill)
        valid = json.loads(run(ROOT / "scripts" / "validate_project.py", self.skill).stdout)
        self.assertTrue(valid["valid"])

        for layer, subtype in (("framework", "project"), ("data", "regression"), ("data", "evaluation")):
            with self.subTest(layer=layer, subtype=subtype):
                project["current_focus"]["task_contract"] = valid_task_contract()
                project["current_focus"]["task_contract"]["classification"].update(
                    {"layer": layer, "data_subtype": subtype}
                )
                write_json(project_path, project)
                run(ROOT / "scripts" / "render_project_views.py", self.skill)
                rejected = run(ROOT / "scripts" / "validate_project.py", self.skill, expected=1)
                self.assertIn("data:project", rejected.stdout)

        project["current_focus"]["task_contract"] = valid_task_contract()
        del project["current_focus"]["task_contract"]["control_plan"]
        write_json(project_path, project)
        run(ROOT / "scripts" / "render_project_views.py", self.skill)
        rejected = run(ROOT / "scripts" / "validate_project.py", self.skill, expected=1)
        self.assertIn("control_plan", rejected.stdout)

    def test_failed_attempt_without_reusable_context_is_not_formal_knowledge(self) -> None:
        store_path = self.skill / "records" / "store.json"
        store = read_json(store_path)
        store["records"].append(
            {
                "id": "attempt-001",
                "kind": "attempt",
                "title": "缺少失败上下文",
                "confirmation_status": "accepted",
                "content": {"outcome": "failed", "attempted": "运行测试"},
            }
        )
        write_json(store_path, store)
        run(ROOT / "scripts" / "render_project_views.py", self.skill)
        rejected = run(ROOT / "scripts" / "validate_project.py", self.skill, expected=1)
        self.assertIn("lacks reusable failure context", rejected.stdout)

    def test_initializer_refuses_to_overwrite_existing_project_skill(self) -> None:
        run(
            ROOT / "scripts" / "init_project.py",
            "--project-root",
            self.project,
            "--skill-name",
            "sample-project",
            "--project-name",
            "示例项目",
            "--goal",
            "另一个目标",
            "--scope",
            "不应覆盖",
            "--evidence-standard",
            "不应覆盖",
            "--criterion",
            "不应覆盖",
            expected=1,
        )

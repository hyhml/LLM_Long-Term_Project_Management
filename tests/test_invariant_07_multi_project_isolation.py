from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from support import ROOT, ProjectTestCase, export_handoff, handoff_with_change, read_json, run, write_json


def digest_files(root: Path, relatives: tuple[str, ...]) -> str:
    digest = hashlib.sha256()
    for relative in relatives:
        digest.update(relative.encode("utf-8"))
        digest.update((root / relative).read_bytes())
    return digest.hexdigest()


class MultiProjectIsolationTest(ProjectTestCase):
    """Invariant 07: shared framework operations remain bound to one project instance."""

    def create_second_project(self) -> Path:
        project = self.temp / "second-project"
        project.mkdir()
        created = json.loads(
            run(
                ROOT / "scripts" / "init_project.py",
                "--project-root",
                project,
                "--skill-name",
                "harness-design",
                "--project-name",
                "Harness 设计",
                "--goal",
                "设计独立的 harness",
                "--scope",
                "Harness architecture",
                "--evidence-standard",
                "独立测试",
                "--criterion",
                "隔离验证通过",
                "--high-task",
                "只属于 harness 的任务",
            ).stdout
        )
        return Path(created["created"])

    def test_search_and_coordination_keep_projects_separate(self) -> None:
        second = self.create_second_project()
        first_result = json.loads(
            run(
                ROOT / "scripts" / "search_project.py",
                "--project-skill",
                self.skill,
                "--query",
                "只属于 harness",
            ).stdout
        )
        self.assertEqual(first_result["results"], [])
        self.assertEqual(first_result["project_id"], self.created["project_id"])

        second_result = json.loads(
            run(
                ROOT / "scripts" / "search_project.py",
                "--project-skill",
                second,
                "--query",
                "只属于 harness",
            ).stdout
        )
        self.assertEqual(len(second_result["results"]), 1)
        self.assertNotEqual(second_result["project_id"], self.created["project_id"])

        coordinated = json.loads(
            run(
                ROOT / "scripts" / "coordinate_projects.py",
                "--project-skill",
                self.skill,
                "--project-skill",
                second,
            ).stdout
        )
        self.assertFalse(coordinated["authority"]["merged"])
        self.assertFalse(coordinated["authority"]["writes_permitted"])
        self.assertEqual(len(coordinated["participants"]), 2)

    def test_identity_mismatch_duplicate_and_session_switch_fail_closed(self) -> None:
        second = self.create_second_project()
        second_id = read_json(second / "state" / "project.json")["project_id"]
        mismatch = run(
            ROOT / "scripts" / "project_binding.py",
            "inspect",
            "--project-skill",
            self.skill,
            "--expected-project-id",
            second_id,
            expected=1,
        )
        self.assertIn("expected project_id", mismatch.stderr)

        switch = json.loads(
            run(
                ROOT / "scripts" / "project_binding.py",
                "session-check",
                "--active-project-id",
                self.created["project_id"],
                "--project-skill",
                second,
            ).stdout
        )
        self.assertEqual(switch["action"], "switch-confirmation-required")
        self.assertFalse(switch["ordinary_project_work_allowed"])

        duplicate = self.skill.parent / "duplicate-project"
        shutil.copytree(self.skill, duplicate)
        ambiguous = run(
            ROOT / "scripts" / "project_binding.py",
            "inspect",
            "--project-skill",
            self.skill,
            expected=1,
        )
        self.assertIn('"status": "ambiguous"', ambiguous.stderr)

    def test_cross_project_handoff_is_rejected(self) -> None:
        second = self.create_second_project()
        handoff = self.temp / "handoff.json"
        package = self.temp / "first.llmpack"
        write_json(handoff, handoff_with_change())
        export_handoff(self.skill, handoff, package)
        rejected = run(
            ROOT / "scripts" / "handoff.py",
            "check-destination",
            package,
            "--project-skill",
            second,
            expected=1,
        )
        self.assertIn("does not match destination", rejected.stderr)

    def test_legacy_child_upgrade_preserves_project_data_and_revision(self) -> None:
        instance = read_json(self.skill / "framework" / "instance.json")
        legacy_version = {
            "schema_version": 1,
            "framework_name": "long-term-project-manager",
            "framework_version": "0.4.0",
            "generated_at": instance["created_at"],
            "project_id": instance["project_id"],
        }
        (self.skill / "framework" / "instance.json").unlink()
        write_json(self.skill / "framework" / "version.json", legacy_version)
        (self.skill / "project-instructions.md").unlink()
        conditional = self.skill / "framework" / "conditional"
        conditional.mkdir()
        (conditional / "legacy.md").write_text("legacy copied protocol\n", encoding="utf-8")
        (self.skill / "SKILL.md").write_text(
            "---\nname: sample-project\ndescription: Legacy explicit project skill.\n---\n\n# Legacy child\n",
            encoding="utf-8",
        )

        formal = (
            "state/project.json",
            "state/task-board.json",
            "records/store.json",
            "sources/registry.json",
        )
        before_digest = digest_files(self.skill, formal)
        before_revision = read_json(self.skill / "state" / "project.json")["revision"]
        run(ROOT / "scripts" / "validate_project.py", self.skill, "--allow-legacy")
        blocked = run(
            ROOT / "scripts" / "project_transaction.py",
            "prepare",
            "--project-skill",
            self.skill,
            "--operation-id",
            "blocked-before-upgrade",
            expected=1,
        )
        self.assertIn("requires an accepted thin-adapter upgrade", blocked.stderr)

        readable = json.loads(
            run(
                ROOT / "scripts" / "search_project.py",
                "--project-skill",
                self.skill,
                "--query",
                "验证高优先级",
            ).stdout
        )
        self.assertEqual(readable["binding_status"], "upgrade-required")

        plan_path = self.temp / "upgrade-plan.json"
        run(
            ROOT / "scripts" / "upgrade_project.py",
            "propose",
            "--project-skill",
            self.skill,
            "--output",
            plan_path,
        )
        plan = read_json(plan_path)
        decisions_path = self.temp / "upgrade-decisions.json"
        write_json(
            decisions_path,
            {
                "decisions": [
                    {"change_id": item["change_id"], "decision": "accepted"}
                    for item in plan["changes"]
                ]
            },
        )
        result = json.loads(
            run(
                ROOT / "scripts" / "upgrade_project.py",
                "apply",
                "--project-skill",
                self.skill,
                "--plan",
                plan_path,
                "--decisions",
                decisions_path,
                "--operation-id",
                "upgrade-v050",
            ).stdout
        )
        self.assertFalse(result["project_data_migrated"])
        self.assertEqual(digest_files(self.skill, formal), before_digest)
        self.assertEqual(read_json(self.skill / "state" / "project.json")["revision"], before_revision)
        self.assertTrue((self.skill / "framework" / "instance.json").is_file())
        self.assertFalse((self.skill / "framework" / "version.json").exists())
        self.assertFalse(conditional.exists())
        self.assertTrue((self.skill / "project-instructions.md").is_file())
        self.assertTrue(Path(result["receipt"]).is_file())
        run(
            ROOT / "scripts" / "upgrade_project.py",
            "verify",
            "--project-skill",
            self.skill,
        )

    def test_adapter_refresh_preserves_user_instructions_and_rolls_back_on_ambiguity(self) -> None:
        instructions = self.skill / "project-instructions.md"
        instructions.write_text("# 用户项目方法\n\n必须保留这一条。\n", encoding="utf-8")
        skill_path = self.skill / "SKILL.md"
        original_skill = skill_path.read_bytes() + b"\n<!-- local managed-file edit -->\n"
        skill_path.write_bytes(original_skill)

        inspected = json.loads(
            run(
                ROOT / "scripts" / "project_binding.py",
                "inspect",
                "--project-skill",
                self.skill,
            ).stdout
        )
        self.assertEqual(inspected["status"], "upgrade-required")

        plan_path = self.temp / "adapter-plan.json"
        run(
            ROOT / "scripts" / "upgrade_project.py",
            "propose",
            "--project-skill",
            self.skill,
            "--output",
            plan_path,
        )
        plan = read_json(plan_path)
        decisions = self.temp / "adapter-decisions.json"
        write_json(
            decisions,
            {
                "decisions": [
                    {"change_id": item["change_id"], "decision": "accepted"}
                    for item in plan["changes"]
                ]
            },
        )

        duplicate = self.skill.parent / "duplicate-during-upgrade"
        shutil.copytree(self.skill, duplicate)
        rejected = run(
            ROOT / "scripts" / "upgrade_project.py",
            "apply",
            "--project-skill",
            self.skill,
            "--plan",
            plan_path,
            "--decisions",
            decisions,
            "--operation-id",
            "rollback-on-ambiguity",
            expected=1,
        )
        self.assertIn("published upgrade failed validation", rejected.stderr)
        self.assertEqual(skill_path.read_bytes(), original_skill)
        self.assertEqual(instructions.read_text(encoding="utf-8"), "# 用户项目方法\n\n必须保留这一条。\n")
        self.assertFalse(
            (self.skill / "packages" / "archive" / "receipts" / "rollback-on-ambiguity-framework-upgrade.json").exists()
        )

        shutil.rmtree(duplicate)
        applied = json.loads(
            run(
                ROOT / "scripts" / "upgrade_project.py",
                "apply",
                "--project-skill",
                self.skill,
                "--plan",
                plan_path,
                "--decisions",
                decisions,
                "--operation-id",
                "refresh-adapter",
            ).stdout
        )
        self.assertEqual(instructions.read_text(encoding="utf-8"), "# 用户项目方法\n\n必须保留这一条。\n")
        self.assertTrue(Path(applied["receipt"]).is_file())

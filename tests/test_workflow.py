from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def run(*arguments: object, expected: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [PYTHON, *map(str, arguments)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != expected:
        raise AssertionError(
            f"command returned {result.returncode}, expected {expected}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


class WorkflowTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.temp = Path(self.temporary.name)
        self.project = self.temp / "project"
        self.project.mkdir()
        result = run(
            ROOT / "scripts" / "init_project.py",
            "--project-root",
            self.project,
            "--skill-name",
            "sample-project",
            "--project-name",
            "示例项目",
            "--goal",
            "完成可验证的示例",
            "--scope",
            "项目管理框架测试",
            "--evidence-standard",
            "自动化测试结果和可检查文件",
            "--criterion",
            "初始化和交接包测试通过",
            "--high-task",
            "验证高优先级流程",
            "--low-task",
            "记录后续改进",
        )
        self.created = json.loads(result.stdout)
        self.skill = Path(self.created["created"])

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_initialization_and_validation(self) -> None:
        result = run(ROOT / "scripts" / "validate_project.py", self.skill)
        self.assertTrue(json.loads(result.stdout)["valid"])
        self.assertIn("allow_implicit_invocation: false", (self.skill / "agents" / "openai.yaml").read_text())
        store = json.loads((self.skill / "records" / "store.json").read_text())
        project = json.loads((self.skill / "state" / "project.json").read_text())
        framework_version = json.loads((self.skill / "framework" / "version.json").read_text())
        project_map = json.loads((self.skill / "views" / "project-map.json").read_text())
        priorities = {node.get("task_priority") for node in project_map["nodes"] if node["type"] == "task"}
        self.assertEqual(priorities, {"high", "low"})
        self.assertEqual(project_map["source"]["project_revision"], project["revision"])
        self.assertEqual(store["project_revision"], project["revision"])
        self.assertEqual(project["objective_contract"]["objective_id"], "objective-001")
        self.assertEqual(framework_version["framework_version"], "0.3.0-dev.2")
        self.assertTrue((self.skill / "state" / "task-board.json").is_file())
        self.assertTrue((self.skill / "sources" / "registry.json").is_file())
        self.assertTrue((self.skill / "index" / "manifest.json").is_file())
        self.assertFalse((self.skill / "database").exists())
        self.assertTrue((self.skill / "work" / "explorations").is_dir())
        self.assertTrue((self.skill / "work" / "candidate-tools").is_dir())

    def test_view_is_deterministic_and_validator_rejects_manual_edits(self) -> None:
        map_path = self.skill / "views" / "project-map.json"
        original = map_path.read_bytes()
        run(ROOT / "scripts" / "render_project_views.py", self.skill)
        self.assertEqual(map_path.read_bytes(), original)

        pending = self.skill / "work" / "explorations" / "unconfirmed.json"
        pending.write_text('{"claim": "not accepted"}\n', encoding="utf-8")
        run(ROOT / "scripts" / "render_project_views.py", self.skill)
        self.assertEqual(map_path.read_bytes(), original)

        project_map = json.loads(map_path.read_text(encoding="utf-8"))
        project_map["nodes"][0]["title"] = "未经正式记录确认的修改"
        map_path.write_text(json.dumps(project_map, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        invalid = run(ROOT / "scripts" / "validate_project.py", self.skill, expected=1)
        self.assertIn("stale or manually edited", invalid.stdout)

    def test_renderer_refuses_unaccepted_formal_records(self) -> None:
        store_path = self.skill / "records" / "store.json"
        store = json.loads(store_path.read_text(encoding="utf-8"))
        store["records"].append(
            {
                "id": "claim-unaccepted",
                "kind": "claim",
                "title": "仍是提案",
                "confirmation_status": "proposed",
                "content": {},
            }
        )
        store_path.write_text(json.dumps(store, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result = run(ROOT / "scripts" / "render_project_views.py", self.skill, expected=1)
        self.assertIn("unaccepted formal record", result.stderr)

    def test_initializer_refuses_overwrite(self) -> None:
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

    def test_export_verify_unpack_and_detect_tampering(self) -> None:
        handoff = {
            "task_id": "task-001",
            "completion_criteria": ["产生可校验的包"],
            "summary": "完成探索",
            "findings": [{"id": "finding-001", "summary": "测试发现"}],
            "attempts": [],
            "failed_directions": [],
            "evidence": [],
            "artifacts": [{"path": "artifacts/result.txt"}],
            "candidate_tools": [],
            "proposed_changes": [
                {
                    "change_id": "change-001",
                    "operation": "add-node",
                    "target": "records.store.records",
                    "reason": "保存发现",
                    "value": {"id": "claim-001", "kind": "claim"},
                }
            ],
            "open_questions": [],
            "next_task_candidates": [],
        }
        handoff_path = self.temp / "handoff.json"
        handoff_path.write_text(json.dumps(handoff, ensure_ascii=False), encoding="utf-8")
        artifact = self.temp / "result.txt"
        artifact.write_text("result\n", encoding="utf-8")
        package = self.temp / "result.llmpack"

        export = run(
            ROOT / "scripts" / "handoff.py",
            "export",
            "--project-skill",
            self.skill,
            "--handoff",
            handoff_path,
            "--output",
            package,
            "--artifact",
            f"{artifact}=artifacts/result.txt",
        )
        export_value = json.loads(export.stdout)
        self.assertTrue(export_value["ok"])
        self.assertEqual(export_value["base_revision"], 0)

        verified = run(ROOT / "scripts" / "handoff.py", "verify", package)
        self.assertTrue(json.loads(verified.stdout)["verified"])
        unpacked = self.temp / "unpacked"
        run(ROOT / "scripts" / "handoff.py", "unpack", package, "--output-dir", unpacked)
        self.assertEqual((unpacked / "artifacts" / "result.txt").read_text(), "result\n")

        tampered = self.temp / "tampered.llmpack"
        with zipfile.ZipFile(package, "r") as source, zipfile.ZipFile(tampered, "w") as destination:
            for info in source.infolist():
                data = source.read(info.filename)
                if info.filename == "handoff.json":
                    data += b" "
                destination.writestr(info, data)
        result = run(ROOT / "scripts" / "handoff.py", "verify", tampered, expected=1)
        self.assertIn("handoff.json", result.stderr)

    def test_transaction_commits_once_creates_receipt_and_rejects_stale_base(self) -> None:
        transaction = ROOT / "scripts" / "project_transaction.py"
        run(transaction, "prepare", "--project-skill", self.skill, "--operation-id", "stale-change")
        prepared = run(transaction, "prepare", "--project-skill", self.skill, "--operation-id", "add-claim")
        candidate = Path(json.loads(prepared.stdout)["candidate"])
        store_path = candidate / "records" / "store.json"
        store = json.loads(store_path.read_text(encoding="utf-8"))
        store["records"].append(
            {
                "id": "claim-001",
                "kind": "claim",
                "title": "事务写入的主张",
                "confirmation_status": "accepted",
                "content": {"statement": "候选副本通过后才进入正式记录"},
            }
        )
        store_path.write_text(json.dumps(store, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        decisions = {
            "decisions": [
                {
                    "change_id": "change-001",
                    "decision": "accepted",
                    "operation": "add-record",
                    "target": "records/store.json#claim-001",
                    "reason": "保存已确认主张",
                }
            ]
        }
        decisions_path = self.temp / "decisions.json"
        decisions_path.write_text(json.dumps(decisions, ensure_ascii=False), encoding="utf-8")
        committed = run(
            transaction,
            "commit",
            "--project-skill",
            self.skill,
            "--operation-id",
            "add-claim",
            "--decisions",
            decisions_path,
        )
        commit_result = json.loads(committed.stdout)
        self.assertEqual(commit_result["new_revision"], 1)
        self.assertTrue(Path(commit_result["receipt"]).is_file())
        project = json.loads((self.skill / "state" / "project.json").read_text(encoding="utf-8"))
        project_map = json.loads((self.skill / "views" / "project-map.json").read_text(encoding="utf-8"))
        self.assertEqual(project["revision"], 1)
        self.assertIn("claim-001", {node["id"] for node in project_map["nodes"]})

        stale = run(
            transaction,
            "commit",
            "--project-skill",
            self.skill,
            "--operation-id",
            "stale-change",
            "--decisions",
            decisions_path,
            expected=1,
        )
        self.assertIn("stale transaction", stale.stderr)

    def test_objective_identity_cannot_be_replaced(self) -> None:
        transaction = ROOT / "scripts" / "project_transaction.py"
        prepared = run(transaction, "prepare", "--project-skill", self.skill, "--operation-id", "replace-objective")
        candidate = Path(json.loads(prepared.stdout)["candidate"])
        project_path = candidate / "state" / "project.json"
        project = json.loads(project_path.read_text(encoding="utf-8"))
        project["objective_contract"]["objective_id"] = "objective-999"
        project_path.write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        decisions_path = self.temp / "objective-decisions.json"
        decisions_path.write_text(
            json.dumps(
                {
                    "decisions": [
                        {
                            "change_id": "change-objective",
                            "decision": "accepted",
                            "operation": "revise-objective",
                            "target": "state/project.json#objective_contract",
                            "reason": "测试稳定身份",
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        rejected = run(
            transaction,
            "commit",
            "--project-skill",
            self.skill,
            "--operation-id",
            "replace-objective",
            "--decisions",
            decisions_path,
            expected=1,
        )
        self.assertIn("objective_id is stable", rejected.stderr)

    def test_accepted_objective_clarification_preserves_identity(self) -> None:
        transaction = ROOT / "scripts" / "project_transaction.py"
        prepared = run(transaction, "prepare", "--project-skill", self.skill, "--operation-id", "clarify-objective")
        candidate = Path(json.loads(prepared.stdout)["candidate"])
        project_path = candidate / "state" / "project.json"
        project = json.loads(project_path.read_text(encoding="utf-8"))
        project["objective_contract"]["objective"] = "完成可验证的示例，并明确验证边界"
        project["objective_contract"]["objective_revision"] = 1
        project_path.write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        decisions_path = self.temp / "clarification-decisions.json"
        decisions_path.write_text(
            json.dumps(
                {
                    "decisions": [
                        {
                            "change_id": "clarify-objective",
                            "decision": "accepted",
                            "operation": "revise-objective",
                            "target": "state/project.json#objective_contract",
                            "reason": "补充边界但不替换项目",
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        run(
            transaction,
            "commit",
            "--project-skill",
            self.skill,
            "--operation-id",
            "clarify-objective",
            "--decisions",
            decisions_path,
        )
        committed = json.loads((self.skill / "state" / "project.json").read_text(encoding="utf-8"))
        self.assertEqual(committed["objective_contract"]["objective_id"], "objective-001")
        self.assertEqual(committed["objective_contract"]["objective_revision"], 1)
        self.assertEqual(committed["revision"], 1)

    def test_failed_attempt_requires_reusable_context(self) -> None:
        store_path = self.skill / "records" / "store.json"
        store = json.loads(store_path.read_text(encoding="utf-8"))
        store["records"].append(
            {
                "id": "attempt-001",
                "kind": "attempt",
                "title": "缺少失败上下文",
                "confirmation_status": "accepted",
                "content": {"outcome": "failed", "attempted": "运行测试"},
            }
        )
        store_path.write_text(json.dumps(store, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        run(ROOT / "scripts" / "render_project_views.py", self.skill)
        invalid = run(ROOT / "scripts" / "validate_project.py", self.skill, expected=1)
        self.assertIn("lacks reusable failure context", invalid.stdout)

    def test_empty_search_reports_coverage_not_global_absence(self) -> None:
        result = run(
            ROOT / "scripts" / "search_project.py",
            "--project-skill",
            self.skill,
            "--query",
            "不存在的词语",
        )
        value = json.loads(result.stdout)
        self.assertEqual(value["results"], [])
        self.assertTrue(value["coverage"]["searched"])
        self.assertTrue(value["coverage"]["not_searched"])
        self.assertIn("does not establish absence", value["coverage"]["statement"])


class EnvironmentProfileTest(unittest.TestCase):
    def test_detection_is_an_unconfirmed_draft(self) -> None:
        result = run(ROOT / "scripts" / "environment_profile.py", "detect")
        profile = json.loads(result.stdout)
        self.assertEqual(profile["status"], "draft-unconfirmed")
        self.assertEqual(profile["profile_revision"], 0)
        self.assertIn("commands", profile)


if __name__ == "__main__":
    unittest.main()

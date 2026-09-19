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
        project_map = json.loads((self.skill / "state" / "project-map.json").read_text())
        priorities = {node.get("task_priority") for node in project_map["nodes"] if node["type"] == "task"}
        self.assertEqual(priorities, {"high", "low"})

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
                    "target": "project-map.nodes",
                    "reason": "保存发现",
                    "value": {"id": "finding-001", "type": "finding"},
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


class EnvironmentProfileTest(unittest.TestCase):
    def test_detection_is_an_unconfirmed_draft(self) -> None:
        result = run(ROOT / "scripts" / "environment_profile.py", "detect")
        profile = json.loads(result.stdout)
        self.assertEqual(profile["status"], "draft-unconfirmed")
        self.assertEqual(profile["profile_revision"], 0)
        self.assertIn("commands", profile)


if __name__ == "__main__":
    unittest.main()

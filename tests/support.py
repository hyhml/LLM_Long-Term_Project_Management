from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def run(*arguments: object, expected: int = 0, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [PYTHON, *map(str, arguments)],
        cwd=cwd or ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != expected:
        raise AssertionError(
            f"command returned {result.returncode}, expected {expected}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"expected JSON object: {path}")
    return value


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def export_handoff(project_skill: Path, handoff: Path, output: Path) -> subprocess.CompletedProcess[str]:
    preview = json.loads(
        run(
            ROOT / "scripts" / "handoff.py",
            "preview",
            "--project-skill",
            project_skill,
            "--handoff",
            handoff,
            "--output",
            output,
        ).stdout
    )
    return run(
        ROOT / "scripts" / "handoff.py",
        "export",
        "--project-skill",
        project_skill,
        "--handoff",
        handoff,
        "--output",
        output,
        "--approved-preview-sha256",
        preview["preview_sha256"],
    )


def valid_task_contract() -> dict:
    return {
        "schema": "ltpm-task-contract/v1",
        "expected_result": "验证持续分类门",
        "scope": ["当前项目任务"],
        "non_goals": ["修改通用框架"],
        "acceptance_evidence": ["项目验证器通过"],
        "allowed_side_effects": ["work/ 下的探索记录"],
        "stop_condition": "取得验收证据或遇到权限边界",
        "classification": {
            "layer": "data",
            "data_subtype": "project",
            "audience": "runtime-user",
        },
        "control_plan": {
            "write_authority": "explorer may write pending work only",
            "storage_targets": ["work/explorations/"],
            "validation_route": ["project validator", "user acceptance"],
            "version_route": "project revision on accepted commit",
            "release_boundary": "project-local",
        },
    }


def handoff_with_change(record_id: str = "claim-from-handoff") -> dict:
    return {
        "task_id": "task-001",
        "completion_criteria": ["产生可校验并可逐项接受的交接包"],
        "summary": "完成合成探索",
        "findings": [{"id": "finding-001", "summary": "合成测试发现"}],
        "attempts": [],
        "failed_directions": [],
        "evidence": [],
        "artifacts": [],
        "candidate_tools": [],
        "proposed_changes": [
            {
                "change_id": "change-001",
                "operation": "add-record",
                "target": f"records/store.json#{record_id}",
                "reason": "保存用户接受的交接发现",
                "value": {
                    "id": record_id,
                    "kind": "claim",
                    "title": "交接包中的主张",
                    "confirmation_status": "accepted",
                    "content": {"statement": "只有接受后才进入正式记录"},
                },
            }
        ],
        "open_questions": [],
        "next_task_candidates": [],
    }


class ProjectTestCase(unittest.TestCase):
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
            "核心不变量测试通过",
            "--high-task",
            "验证高优先级流程",
            "--low-task",
            "记录后续改进",
        )
        self.created = json.loads(result.stdout)
        self.skill = Path(self.created["created"])

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def prepare(self, operation_id: str) -> Path:
        result = run(
            ROOT / "scripts" / "project_transaction.py",
            "prepare",
            "--project-skill",
            self.skill,
            "--operation-id",
            operation_id,
        )
        return Path(json.loads(result.stdout)["candidate"])

    def write_decisions(self, filename: str, decisions: list[dict]) -> Path:
        path = self.temp / filename
        write_json(path, {"decisions": decisions})
        return path

    def accepted_decision(
        self,
        change_id: str,
        operation: str,
        target: str,
        reason: str = "合成测试接受项",
    ) -> dict:
        return {
            "change_id": change_id,
            "decision": "accepted",
            "operation": operation,
            "target": target,
            "reason": reason,
        }

    def commit(self, operation_id: str, decisions_path: Path, expected: int = 0) -> subprocess.CompletedProcess[str]:
        return run(
            ROOT / "scripts" / "project_transaction.py",
            "commit",
            "--project-skill",
            self.skill,
            "--operation-id",
            operation_id,
            "--decisions",
            decisions_path,
            expected=expected,
        )

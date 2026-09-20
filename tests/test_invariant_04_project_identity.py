from __future__ import annotations

from support import ProjectTestCase, read_json, write_json


class ProjectIdentityContinuityTest(ProjectTestCase):
    """Invariant 04: objective identity is stable and revisions are explicit."""

    def test_objective_identity_cannot_be_replaced(self) -> None:
        candidate = self.prepare("replace-objective")
        project_path = candidate / "state" / "project.json"
        project = read_json(project_path)
        project["objective_contract"]["objective_id"] = "objective-999"
        write_json(project_path, project)
        decisions = self.write_decisions(
            "replace-objective.json",
            [
                self.accepted_decision(
                    "change-objective",
                    "revise-objective",
                    "state/project.json#objective_contract",
                )
            ],
        )
        rejected = self.commit("replace-objective", decisions, expected=1)
        self.assertIn("objective_id is stable", rejected.stderr)
        self.assertEqual(read_json(self.skill / "state" / "project.json")["objective_contract"]["objective_id"], "objective-001")

    def test_objective_change_requires_an_explicit_revise_objective_decision(self) -> None:
        candidate = self.prepare("unauthorized-objective-change")
        project_path = candidate / "state" / "project.json"
        project = read_json(project_path)
        project["objective_contract"]["objective"] = "未经目标修订决定的新目标"
        project["objective_contract"]["objective_revision"] = 1
        write_json(project_path, project)
        decisions = self.write_decisions(
            "wrong-operation.json",
            [self.accepted_decision("change-001", "add-record", "records/store.json#claim-001")],
        )
        rejected = self.commit("unauthorized-objective-change", decisions, expected=1)
        self.assertIn("without an accepted revise-objective decision", rejected.stderr)

    def test_accepted_clarification_preserves_identity_and_increments_once(self) -> None:
        candidate = self.prepare("clarify-objective")
        project_path = candidate / "state" / "project.json"
        project = read_json(project_path)
        project["objective_contract"]["objective"] = "完成可验证的示例，并明确验证边界"
        project["objective_contract"]["objective_revision"] = 1
        write_json(project_path, project)
        decisions = self.write_decisions(
            "clarification.json",
            [
                self.accepted_decision(
                    "clarify-objective",
                    "revise-objective",
                    "state/project.json#objective_contract",
                )
            ],
        )
        self.commit("clarify-objective", decisions)

        committed = read_json(self.skill / "state" / "project.json")
        self.assertEqual(committed["objective_contract"]["objective_id"], "objective-001")
        self.assertEqual(committed["objective_contract"]["objective_revision"], 1)
        self.assertEqual(committed["revision"], 1)

    def test_objective_revision_cannot_skip_a_number(self) -> None:
        candidate = self.prepare("skip-objective-revision")
        project_path = candidate / "state" / "project.json"
        project = read_json(project_path)
        project["objective_contract"]["objective"] = "跳过版本号的目标"
        project["objective_contract"]["objective_revision"] = 2
        write_json(project_path, project)
        decisions = self.write_decisions(
            "skip-revision.json",
            [
                self.accepted_decision(
                    "change-objective",
                    "revise-objective",
                    "state/project.json#objective_contract",
                )
            ],
        )
        rejected = self.commit("skip-objective-revision", decisions, expected=1)
        self.assertIn("increment objective_revision exactly once", rejected.stderr)

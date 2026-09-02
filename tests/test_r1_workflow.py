import unittest

from src.contracts import (
    ApplicationOutcome,
    Capability,
    SkillInventory,
    Stage,
    TargetRole,
)
from src.r1_workflow import analyse_case


def outcome(stage: Stage, rejected: bool) -> ApplicationOutcome:
    return ApplicationOutcome(
        week=18, role_title="Operations Coordinator", stage_reached=stage, rejected=rejected
    )


class R1WorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.inventory = SkillInventory(
            capabilities=[
                Capability(skill=s, evidence=f"stub: {s}")
                for s in ("Excel", "Customer service", "Scheduling")
            ]
        )
        self.roles = [
            TargetRole(
                title="Data Analyst",
                rationale="stub",
                missing_skills=["SQL", "Python"],
                months_to_ready=9,
                est_cost_sgd=4200,
                reachable=True,
                confidence=0.55,
            ),
            TargetRole(
                title="Operations Coordinator",
                rationale="stub",
                missing_skills=["Scheduling"],
                months_to_ready=3,
                est_cost_sgd=1200,
                reachable=True,
                confidence=0.81,
            ),
        ]

    def test_handoff_contains_baseline_and_replan_reason(self) -> None:
        analysis = analyse_case(
            self.inventory,
            self.roles,
            [
                outcome(Stage.SCREENING, True),
                outcome(Stage.SCREENING, True),
                outcome(Stage.SCREENING, True),
                outcome(Stage.SCREENING, False),
            ],
        )

        self.assertEqual(analysis.baseline.target_role_title, "Operations Coordinator")
        self.assertTrue(analysis.needs_replan)
        self.assertIn("screening", analysis.replan_reason or "")
        self.assertIsNotNone(analysis.guidance)
        assert analysis.guidance is not None
        self.assertEqual(analysis.guidance.focus, "positioning")

    def test_handoff_does_not_request_a_replan_without_evidence(self) -> None:
        analysis = analyse_case(
            self.inventory,
            self.roles,
            [outcome(Stage.TECHNICAL, False)],
        )

        self.assertFalse(analysis.needs_replan)
        self.assertIsNone(analysis.replan_reason)
        self.assertIsNone(analysis.guidance)

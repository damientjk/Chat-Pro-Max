from dataclasses import dataclass
import unittest

from src.r1_workflow import analyse_case


@dataclass
class Skills:
    skills: list[str]


@dataclass
class Role:
    id: str
    title: str
    required_skills: list[str]


@dataclass
class Outcome:
    status: str
    stage: str


class R1WorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.skills = Skills(["Excel", "Customer service", "Scheduling"])
        self.roles = [
            Role("data", "Data Analyst", ["SQL", "Python", "Excel"]),
            Role(
                "operations",
                "Operations Coordinator",
                ["Excel", "Customer service", "Scheduling"],
            ),
        ]

    def test_handoff_contains_baseline_and_replan_reason(self) -> None:
        analysis = analyse_case(
            self.skills,
            self.roles,
            [
                Outcome("rejected", "screening"),
                Outcome("rejected", "screening"),
                Outcome("rejected", "screening"),
                Outcome("advanced", "screening"),
            ],
        )

        self.assertEqual(analysis.baseline.target_role_id, "operations")
        self.assertTrue(analysis.needs_replan)
        self.assertIn("screening", analysis.replan_reason or "")
        self.assertIsNotNone(analysis.guidance)
        assert analysis.guidance is not None
        self.assertEqual(analysis.guidance.focus, "positioning")

    def test_handoff_does_not_request_a_replan_without_evidence(self) -> None:
        analysis = analyse_case(
            self.skills,
            self.roles,
            [Outcome("advanced", "technical")],
        )

        self.assertFalse(analysis.needs_replan)
        self.assertIsNone(analysis.replan_reason)
        self.assertIsNone(analysis.guidance)

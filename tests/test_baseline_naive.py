import unittest

from src.baseline.naive import recommend_once
from src.contracts import Capability, SkillInventory, TargetRole


def inventory(*skills: str) -> SkillInventory:
    return SkillInventory(
        capabilities=[Capability(skill=s, evidence=f"stub: {s}") for s in skills]
    )


def role(title: str, missing: list[str], confidence: float = 0.7) -> TargetRole:
    return TargetRole(
        title=title,
        rationale="stub",
        missing_skills=missing,
        months_to_ready=4,
        est_cost_sgd=2500,
        reachable=True,
        confidence=confidence,
    )


class BaselineRecommendationTests(unittest.TestCase):
    def test_baseline_selects_the_smallest_remaining_gap(self) -> None:
        recommendation = recommend_once(
            inventory("Excel", "Customer service", "Scheduling"),
            [
                role("Data Analyst", ["SQL", "Python"]),
                role("Operations Coordinator", ["Scheduling"]),
            ],
        )

        self.assertEqual(recommendation.target_role_title, "Operations Coordinator")
        self.assertEqual(recommendation.open_gaps, 0)
        self.assertEqual(recommendation.gaps_already_closed, 1)
        self.assertEqual(recommendation.replans, 0)

    def test_gaps_the_candidate_can_already_evidence_do_not_count(self) -> None:
        """A TargetRole records the gap as it was. Training closes some of it."""
        recommendation = recommend_once(
            inventory("SQL"),
            [role("Data Analyst", ["SQL", "Python"])],
        )

        self.assertEqual(recommendation.open_gaps, 1)
        self.assertEqual(recommendation.gaps_already_closed, 1)

    def test_ties_break_on_confidence(self) -> None:
        recommendation = recommend_once(
            inventory("Excel"),
            [
                role("Logistics Systems Analyst", ["SQL"], confidence=0.4),
                role("Operations Business Partner", ["SQL"], confidence=0.9),
            ],
        )

        self.assertEqual(
            recommendation.target_role_title, "Operations Business Partner"
        )

    def test_baseline_requires_a_role(self) -> None:
        with self.assertRaisesRegex(ValueError, "At least one target role is required."):
            recommend_once(inventory("Excel"), [])

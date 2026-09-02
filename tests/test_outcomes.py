import unittest

from src.baseline.naive import BaselineRecommendation
from src.signals.outcomes import AgentOutcome, calculate_benefits


def decision(title: str) -> BaselineRecommendation:
    return BaselineRecommendation(
        target_role_title=title,
        open_gaps=2,
        gaps_already_closed=0,
        months_to_ready=9,
        est_cost_sgd=4200,
        rationale="stub",
    )


class BenefitMetricsTests(unittest.TestCase):
    def test_calculates_benefits_for_matching_personas(self) -> None:
        baseline = [decision("Data Analyst"), decision("Logistics Systems Analyst")]
        agent = [
            AgentOutcome(1, 3, 1500.0),
            AgentOutcome(1, 2, 1000.0),
        ]

        metrics = calculate_benefits(baseline, agent)

        self.assertEqual(metrics.candidates, 2)
        self.assertEqual(metrics.baseline_dead_paths, 2)
        self.assertEqual(metrics.agent_dead_paths_caught, 2)
        self.assertEqual(metrics.months_saved, 5)
        self.assertEqual(metrics.training_spend_avoided, 2500.0)

    def test_rejects_an_unfair_comparison(self) -> None:
        with self.assertRaisesRegex(ValueError, "same number of candidates"):
            calculate_benefits(
                [decision("Data Analyst")],
                [AgentOutcome(1, 3, 1500.0), AgentOutcome(0, 0, 0.0)],
            )

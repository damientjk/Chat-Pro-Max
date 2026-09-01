from dataclasses import dataclass
import unittest

from src.signals.outcomes import calculate_benefits


@dataclass
class BaselineDecision:
    target_role_id: str


@dataclass
class AgentOutcome:
    dead_paths_caught: int
    months_saved: int
    training_spend_avoided: float


class BenefitMetricsTests(unittest.TestCase):
    def test_calculates_benefits_for_matching_personas(self) -> None:
        baseline = [BaselineDecision("role-a"), BaselineDecision("role-b")]
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
                [BaselineDecision("role-a")],
                [AgentOutcome(1, 3, 1500.0), AgentOutcome(0, 0, 0.0)],
            )

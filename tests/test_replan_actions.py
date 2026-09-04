import unittest

from src.contracts import Stage
from src.signals.actions import recommend_replan_action
from src.signals.rejection import RejectionPattern


def strong_pattern(stage: Stage) -> RejectionPattern:
    return RejectionPattern(
        stage=stage,
        rejection_count=3,
        total_outcomes=4,
        rejection_rate=0.75,
        should_replan=True,
        reason=f"Repeated rejection at {stage.value}.",
    )


class ReplanActionTests(unittest.TestCase):
    def test_screening_rejections_improve_positioning(self) -> None:
        guidance = recommend_replan_action(strong_pattern(Stage.SCREENING))

        self.assertIsNotNone(guidance)
        assert guidance is not None
        self.assertEqual(guidance.focus, "positioning")
        self.assertFalse(guidance.requires_human_review)

    def test_technical_rejections_improve_skill_evidence(self) -> None:
        guidance = recommend_replan_action(strong_pattern(Stage.TECHNICAL))

        self.assertIsNotNone(guidance)
        assert guidance is not None
        self.assertEqual(guidance.focus, "skill gap")

    def test_stages_without_an_intervention_require_human_review(self) -> None:
        guidance = recommend_replan_action(strong_pattern(Stage.RECRUITER))

        self.assertIsNotNone(guidance)
        assert guidance is not None
        self.assertTrue(guidance.requires_human_review)

    def test_weak_signal_has_no_recommendation(self) -> None:
        weak = RejectionPattern(
            stage=Stage.SCREENING,
            rejection_count=1,
            total_outcomes=3,
            rejection_rate=1 / 3,
            should_replan=False,
            reason="One rejection is not enough evidence.",
        )

        self.assertIsNone(recommend_replan_action(weak))

import unittest

from src.contracts import ApplicationOutcome, Stage
from src.signals.rejection import detect_rejection_pattern


def outcome(stage: Stage, rejected: bool) -> ApplicationOutcome:
    return ApplicationOutcome(
        week=18, role_title="Operations Coordinator", stage_reached=stage, rejected=rejected
    )


class RejectionSignalTests(unittest.TestCase):
    def test_repeated_screening_rejections_trigger_a_replan(self) -> None:
        outcomes = [
            outcome(Stage.SCREENING, True),
            outcome(Stage.SCREENING, True),
            outcome(Stage.SCREENING, True),
            outcome(Stage.SCREENING, False),
        ]

        pattern = detect_rejection_pattern(outcomes)

        self.assertIsNotNone(pattern)
        assert pattern is not None
        self.assertEqual(pattern.stage, Stage.SCREENING)
        self.assertTrue(pattern.should_replan)

    def test_a_single_rejection_does_not_trigger_a_replan(self) -> None:
        pattern = detect_rejection_pattern(
            [outcome(Stage.TECHNICAL, True), outcome(Stage.SCREENING, False)]
        )

        self.assertIsNotNone(pattern)
        assert pattern is not None
        self.assertFalse(pattern.should_replan)

    def test_a_minority_of_rejections_is_not_a_pattern(self) -> None:
        """Three rejections out of ten is noise, even at one stage."""
        outcomes = [outcome(Stage.SCREENING, True)] * 3
        outcomes += [outcome(Stage.RECRUITER, False)] * 7

        pattern = detect_rejection_pattern(outcomes)

        assert pattern is not None
        self.assertEqual(pattern.rejection_count, 3)
        self.assertFalse(pattern.should_replan)

    def test_no_rejections_returns_no_signal(self) -> None:
        pattern = detect_rejection_pattern([outcome(Stage.TECHNICAL, False)])

        self.assertIsNone(pattern)

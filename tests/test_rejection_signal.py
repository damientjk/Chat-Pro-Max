from dataclasses import dataclass
import unittest

from src.signals.rejection import detect_rejection_pattern


@dataclass
class Outcome:
    status: str
    stage: str


class RejectionSignalTests(unittest.TestCase):
    def test_repeated_screening_rejections_trigger_a_replan(self) -> None:
        outcomes = [
            Outcome("rejected", "screening"),
            Outcome("rejected", "screening"),
            Outcome("rejected", "screening"),
            Outcome("advanced", "screening"),
        ]

        pattern = detect_rejection_pattern(outcomes)

        self.assertIsNotNone(pattern)
        assert pattern is not None
        self.assertEqual(pattern.stage, "screening")
        self.assertTrue(pattern.should_replan)

    def test_a_single_rejection_does_not_trigger_a_replan(self) -> None:
        pattern = detect_rejection_pattern(
            [Outcome("rejected", "technical"), Outcome("advanced", "screening")]
        )

        self.assertIsNotNone(pattern)
        assert pattern is not None
        self.assertFalse(pattern.should_replan)

    def test_no_rejections_returns_no_signal(self) -> None:
        pattern = detect_rejection_pattern([Outcome("advanced", "technical")])

        self.assertIsNone(pattern)

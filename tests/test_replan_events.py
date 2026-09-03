import unittest

from src.signals.actions import ReplanGuidance
from src.signals.events import build_replan_event
from src.signals.rejection import RejectionPattern


class ReplanEventTests(unittest.TestCase):
    def test_event_preserves_the_evidence_and_guidance(self) -> None:
        pattern = RejectionPattern(
            stage="technical",
            rejection_count=3,
            total_outcomes=4,
            rejection_rate=0.75,
            should_replan=True,
            reason="3 of 4 applications were rejected at technical.",
        )
        guidance = ReplanGuidance(
            focus="skill gap",
            action="Add a focused technical practice module and portfolio evidence.",
            rationale=pattern.reason,
        )

        event = build_replan_event(pattern, guidance)

        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.event_type, "rejection_pattern")
        self.assertEqual(event.stage, "technical")
        self.assertEqual(event.to_state_payload()["evidence"], {
            "rejection_count": 3,
            "total_outcomes": 4,
            "rejection_rate": 0.75,
        })

    def test_weak_evidence_does_not_create_an_event(self) -> None:
        weak_pattern = RejectionPattern(
            stage="screening",
            rejection_count=1,
            total_outcomes=3,
            rejection_rate=1 / 3,
            should_replan=False,
            reason="One rejection is not enough evidence.",
        )
        guidance = ReplanGuidance(
            focus="positioning",
            action="Rewrite the profile summary.",
            rationale=weak_pattern.reason,
        )

        self.assertIsNone(build_replan_event(weak_pattern, guidance))

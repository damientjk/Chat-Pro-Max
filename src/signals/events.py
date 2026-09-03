"""Stable Day 2 signal events for the agent-core re-plan trigger."""

from dataclasses import dataclass

from src.signals.actions import ReplanGuidance
from src.signals.rejection import RejectionPattern


@dataclass(frozen=True)
class ReplanEvent:
    """A serializable evidence event for R2's second adaptation edge.

    R1 creates the event from application outcomes. R2 remains responsible for
    persisting it and deciding how its LangGraph state moves next.
    """

    event_type: str
    stage: str
    rejection_count: int
    total_outcomes: int
    rejection_rate: float
    focus: str
    recommended_action: str
    reason: str
    requires_human_review: bool

    def to_state_payload(self) -> dict[str, object]:
        """Return a JSON-safe payload that can be stored in CaseState."""
        return {
            "event_type": self.event_type,
            "stage": self.stage,
            "evidence": {
                "rejection_count": self.rejection_count,
                "total_outcomes": self.total_outcomes,
                "rejection_rate": self.rejection_rate,
            },
            "focus": self.focus,
            "recommended_action": self.recommended_action,
            "reason": self.reason,
            "requires_human_review": self.requires_human_review,
        }


def build_replan_event(
    pattern: RejectionPattern | None,
    guidance: ReplanGuidance | None,
) -> ReplanEvent | None:
    """Create an event only when the rejection evidence warrants a re-plan."""
    if pattern is None or guidance is None or not pattern.should_replan:
        return None

    return ReplanEvent(
        event_type="rejection_pattern",
        stage=pattern.stage,
        rejection_count=pattern.rejection_count,
        total_outcomes=pattern.total_outcomes,
        rejection_rate=pattern.rejection_rate,
        focus=guidance.focus,
        recommended_action=guidance.action,
        reason=pattern.reason,
        requires_human_review=guidance.requires_human_review,
    )

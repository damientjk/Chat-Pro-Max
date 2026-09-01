"""Translate rejection evidence into an auditable re-plan recommendation."""

from dataclasses import dataclass

from src.signals.rejection import RejectionPattern


@dataclass(frozen=True)
class ReplanGuidance:
    """A recommendation for R2 to apply after a strong rejection pattern."""

    focus: str
    action: str
    rationale: str
    requires_human_review: bool = False


def recommend_replan_action(pattern: RejectionPattern | None) -> ReplanGuidance | None:
    """Suggest one specific corrective action for an evidence-backed signal.

    Returning ``None`` means there is not enough evidence to revise a plan.
    Unknown stages are deliberately sent to a human reviewer instead of
    pretending the system knows the correct intervention.
    """
    if pattern is None or not pattern.should_replan:
        return None

    actions = {
        "screening": (
            "positioning",
            "Rewrite the profile summary and role-specific resume language.",
        ),
        "technical": (
            "skill gap",
            "Add a focused technical practice module and portfolio evidence.",
        ),
        "final": (
            "interview readiness",
            "Add interview practice focused on outcomes, examples, and negotiation.",
        ),
    }
    focus, action = actions.get(
        pattern.stage,
        (
            "human review",
            "Ask a career coach to review the outcome pattern before changing the plan.",
        ),
    )

    return ReplanGuidance(
        focus=focus,
        action=action,
        rationale=pattern.reason,
        requires_human_review=focus == "human review",
    )

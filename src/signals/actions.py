"""Translate rejection evidence into an auditable re-plan recommendation."""

from dataclasses import dataclass

from ..contracts import Stage
from .rejection import RejectionPattern


@dataclass(frozen=True)
class ReplanGuidance:
    """A recommendation for R2 to apply after a strong rejection pattern."""

    focus: str
    action: str
    rationale: str
    requires_human_review: bool = False


# The stages we have a defined intervention for. Anything else — a rejection
# after RECRUITER, or after an OFFER — goes to a person rather than to a guess.
INTERVENTIONS: dict[Stage, tuple[str, str]] = {
    Stage.SCREENING: (
        "positioning",
        "Rewrite the profile summary and role-specific resume language.",
    ),
    Stage.TECHNICAL: (
        "skill gap",
        "Add a focused technical practice module and portfolio evidence.",
    ),
    Stage.FINAL: (
        "interview readiness",
        "Add interview practice focused on outcomes, examples, and negotiation.",
    ),
}


def recommend_replan_action(pattern: RejectionPattern | None) -> ReplanGuidance | None:
    """Suggest one specific corrective action for an evidence-backed signal.

    Returning ``None`` means there is not enough evidence to revise a plan.
    Stages with no defined intervention are deliberately sent to a human
    reviewer instead of pretending the system knows the correct fix.
    """
    if pattern is None or not pattern.should_replan:
        return None

    focus, action = INTERVENTIONS.get(
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

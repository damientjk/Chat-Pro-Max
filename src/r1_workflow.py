"""R1's boundary with the agent core owned by R2.

The module produces evidence for a re-plan, but it never executes the re-plan.
R2's LangGraph supervisor remains the single owner of state transitions.
"""

from dataclasses import dataclass
from typing import Iterable

from .baseline.naive import BaselineRecommendation, recommend_once
from .contracts import ApplicationOutcome, SkillInventory, TargetRole
from .signals.actions import ReplanGuidance, recommend_replan_action
from .signals.events import ReplanEvent, build_replan_event
from .signals.rejection import RejectionPattern, detect_rejection_pattern


@dataclass(frozen=True)
class R1CaseAnalysis:
    """R1 output passed to R2's case state and re-plan trigger."""

    baseline: BaselineRecommendation
    rejection_pattern: RejectionPattern | None
    guidance: ReplanGuidance | None
    replan_event: ReplanEvent | None

    @property
    def needs_replan(self) -> bool:
        """Whether R2 should take its re-plan edge for this case."""
        return bool(
            self.rejection_pattern and self.rejection_pattern.should_replan
        )

    @property
    def replan_reason(self) -> str | None:
        """A human-readable, auditable explanation for the state transition."""
        if not self.needs_replan:
            return None
        assert self.rejection_pattern is not None
        return self.rejection_pattern.reason


def analyse_case(
    inventory: SkillInventory,
    target_roles: Iterable[TargetRole],
    application_outcomes: Iterable[ApplicationOutcome],
) -> R1CaseAnalysis:
    """Produce R1's baseline and rejection evidence for one candidate."""
    pattern = detect_rejection_pattern(application_outcomes)
    guidance = recommend_replan_action(pattern)

    return R1CaseAnalysis(
        baseline=recommend_once(inventory, target_roles),
        rejection_pattern=pattern,
        guidance=guidance,
        replan_event=build_replan_event(pattern, guidance),
    )

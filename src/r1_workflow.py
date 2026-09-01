"""R1's boundary with the agent core owned by R2.

The module produces evidence for a re-plan, but it never executes the re-plan.
R2's LangGraph supervisor remains the single owner of state transitions.
"""

from dataclasses import dataclass
from typing import Iterable

from src.baseline.naive import (
    BaselineRecommendation,
    HasRoleDetails,
    HasSkills,
    recommend_once,
)
from src.signals.rejection import (
    HasOutcomeDetails,
    RejectionPattern,
    detect_rejection_pattern,
)


@dataclass(frozen=True)
class R1CaseAnalysis:
    """R1 output passed to R2's case state and re-plan trigger."""

    baseline: BaselineRecommendation
    rejection_pattern: RejectionPattern | None

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
    skills: HasSkills,
    target_roles: Iterable[HasRoleDetails],
    application_outcomes: Iterable[HasOutcomeDetails],
) -> R1CaseAnalysis:
    """Produce R1's baseline and rejection evidence for one candidate."""
    return R1CaseAnalysis(
        baseline=recommend_once(skills, target_roles),
        rejection_pattern=detect_rejection_pattern(application_outcomes),
    )

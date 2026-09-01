"""Compute the baseline-versus-agent benefit numbers for the presentation."""

from dataclasses import dataclass
from typing import Iterable, Protocol


class HasBaselineDecision(Protocol):
    target_role_id: str


class HasAgentOutcome(Protocol):
    dead_paths_caught: int
    months_saved: int
    training_spend_avoided: float


@dataclass(frozen=True)
class BenefitMetrics:
    candidates: int
    baseline_dead_paths: int
    agent_dead_paths_caught: int
    months_saved: int
    training_spend_avoided: float


def calculate_benefits(
    baseline_decisions: Iterable[HasBaselineDecision],
    agent_outcomes: Iterable[HasAgentOutcome],
) -> BenefitMetrics:
    """Compare the baseline and adaptive agent over exactly the same people.

    R4 should call this once after the six-person evaluation replay. The
    function refuses mismatched runs because a fair benefit claim needs the
    same personas on each side of the comparison.
    """
    baseline = list(baseline_decisions)
    adaptive = list(agent_outcomes)

    if len(baseline) != len(adaptive):
        raise ValueError(
            "Baseline and adaptive runs must contain the same number of candidates."
        )

    return BenefitMetrics(
        candidates=len(adaptive),
        baseline_dead_paths=sum(
            1 for decision in baseline if decision.target_role_id
        ),
        agent_dead_paths_caught=sum(
            outcome.dead_paths_caught for outcome in adaptive
        ),
        months_saved=sum(outcome.months_saved for outcome in adaptive),
        training_spend_avoided=sum(
            outcome.training_spend_avoided for outcome in adaptive
        ),
    )

"""Benefit metrics. Owner: R1.

The number the benefits slide lives on. Computed, not asserted.

TODO(R1): months saved, wasted training spend avoided, dead paths caught.
Run agent vs baseline across all six personas and record the comparison.
"""

from dataclasses import dataclass
from typing import Iterable

from ..baseline.naive import BaselineRecommendation
from ..contracts import CaseState


def summarise(state: CaseState) -> dict:
    return {
        "weeks_elapsed": state.get("week", 0),
        "applications": len(state.get("applications", [])),
        "adaptations": len(
            [e for e in state.get("events", []) if e.kind in ("replan", "reposition")]
        ),
        "outcome": state.get("outcome", ""),
    }


@dataclass(frozen=True)
class AgentOutcome:
    """What one adaptive run saved, relative to the baseline's single guess.

    Defined here rather than in contracts.py because it is scoring output, not
    graph state — no node reads or writes it. R4's harness fills these in from
    a completed CaseState.
    """

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
    baseline_decisions: Iterable[BaselineRecommendation],
    agent_outcomes: Iterable[AgentOutcome],
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
            1 for decision in baseline if decision.target_role_title
        ),
        agent_dead_paths_caught=sum(
            outcome.dead_paths_caught for outcome in adaptive
        ),
        months_saved=sum(outcome.months_saved for outcome in adaptive),
        training_spend_avoided=sum(
            outcome.training_spend_avoided for outcome in adaptive
        ),
    )

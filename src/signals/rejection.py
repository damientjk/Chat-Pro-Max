"""Detect repeated application rejections that justify a re-plan."""

from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Protocol


class HasOutcomeDetails(Protocol):
    status: str
    stage: str


@dataclass(frozen=True)
class RejectionPattern:
    """A concentrated rejection signal at one stage of the hiring process."""

    stage: str
    rejection_count: int
    total_outcomes: int
    rejection_rate: float
    should_replan: bool
    reason: str


def detect_rejection_pattern(
    outcomes: Iterable[HasOutcomeDetails],
    minimum_rejections: int = 3,
    minimum_rate: float = 0.60,
) -> RejectionPattern | None:
    """Return the strongest rejection pattern, if applications have failed.

    A re-plan is warranted only when at least ``minimum_rejections`` outcomes
    fail at the same stage and make up at least ``minimum_rate`` of all
    outcomes. This avoids changing a career plan after one isolated rejection.
    """
    all_outcomes = list(outcomes)
    rejected = [
        outcome
        for outcome in all_outcomes
        if outcome.status.strip().lower() == "rejected"
    ]
    if not rejected:
        return None

    stages = Counter(outcome.stage.strip().lower() for outcome in rejected)
    stage, rejection_count = stages.most_common(1)[0]
    rejection_rate = rejection_count / len(all_outcomes)
    should_replan = (
        rejection_count >= minimum_rejections and rejection_rate >= minimum_rate
    )

    action = (
        "Re-plan the candidate's positioning and next actions."
        if should_replan
        else "Keep collecting evidence before changing the plan."
    )

    return RejectionPattern(
        stage=stage,
        rejection_count=rejection_count,
        total_outcomes=len(all_outcomes),
        rejection_rate=rejection_rate,
        should_replan=should_replan,
        reason=(
            f"{rejection_count} of {len(all_outcomes)} applications were rejected "
            f"at {stage}. {action}"
        ),
    )

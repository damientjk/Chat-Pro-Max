"""Rejection-pattern detection. Owner: R1.

Rejection is evidence, not noise. The PATTERN says what to fix:

  all dying at SCREENING   -> the positioning is wrong  -> reposition
  reaching TECHNICAL, then losing -> the gap analysis missed something -> re-plan
  no responses at all      -> the target is wrong       -> back to targeting

No model call. Pure Python over the outcome list, so it is unit-testable and
drives a graph edge deterministically.

TWO READERS, TWO SHAPES
-----------------------
`diagnose` answers the graph's question — one word, or None — because
triggers.route needs an edge name and nothing else.

`detect_rejection_pattern` answers the deck's question: it keeps the counts and
the sentence that explains them, so a claim on a slide can be traced back to
the applications that produced it. Same threshold, same input type; it just
does not throw the arithmetic away.
"""

from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from ..contracts import ApplicationOutcome, Stage

MIN_SIGNAL = 3  # do not conclude anything from one rejection

# A stage has to dominate, not merely lead. Three rejections out of forty is
# noise; three out of four is a pattern.
MIN_RATE = 0.60


def diagnose(applications: list[ApplicationOutcome]) -> str | None:
    """Return 'reposition' | 'replan_gap' | 'retarget' | None."""
    recent = [a for a in applications if a.rejected]
    if len(recent) < MIN_SIGNAL:
        return None

    stages = Counter(a.stage_reached for a in recent)
    # TODO(R1): tune these thresholds against the eval personas.
    if stages[Stage.SCREENING] >= MIN_SIGNAL:
        return "reposition"
    if stages[Stage.TECHNICAL] >= MIN_SIGNAL:
        return "replan_gap"
    return None


@dataclass(frozen=True)
class RejectionPattern:
    """A concentrated rejection signal at one stage of the hiring process."""

    stage: Stage
    rejection_count: int
    total_outcomes: int
    rejection_rate: float
    should_replan: bool
    reason: str


def detect_rejection_pattern(
    outcomes: Iterable[ApplicationOutcome],
    minimum_rejections: int = MIN_SIGNAL,
    minimum_rate: float = MIN_RATE,
) -> RejectionPattern | None:
    """Return the strongest rejection pattern, if applications have failed.

    A re-plan is warranted only when at least ``minimum_rejections`` outcomes
    fail at the same stage and make up at least ``minimum_rate`` of all
    outcomes. This avoids changing a career plan after one isolated rejection.
    """
    all_outcomes = list(outcomes)
    rejected = [outcome for outcome in all_outcomes if outcome.rejected]
    if not rejected:
        return None

    stages = Counter(outcome.stage_reached for outcome in rejected)
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
            f"at {stage.value}. {action}"
        ),
    )

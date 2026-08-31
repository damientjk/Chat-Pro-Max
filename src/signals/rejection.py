"""Rejection-pattern detection. Owner: R1.

Rejection is evidence, not noise. The PATTERN says what to fix:

  all dying at SCREENING   -> the positioning is wrong  -> reposition
  reaching TECHNICAL, then losing -> the gap analysis missed something -> re-plan
  no responses at all      -> the target is wrong       -> back to targeting

No model call. Pure Python over the outcome list, so it is unit-testable and
drives a graph edge deterministically.
"""

from collections import Counter

from ..contracts import ApplicationOutcome, Stage

MIN_SIGNAL = 3  # do not conclude anything from one rejection


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

"""A plan must be paced across its own training window. Owner: R3.

The model is ASKED to spread the steps, and a prompt is not a guarantee. When
it ignored the instruction the steps landed in weeks 1 and 2 of a five-month
plan; graph._training_completed then credited every missing skill a fortnight
in, so the candidate was fully "retrained" before the market had even moved.

These tests exercise planner._paced directly, so they need no API key.
"""

from src.agents.planner import _WEEKS_PER_MONTH, _paced
from src.contracts import PlanStep, TargetRole


def step(week: int, gap: str) -> PlanStep:
    return PlanStep(week=week, description=f"close {gap}", closes_gap=gap, kind="course")


TARGET = TargetRole(
    title="Supply Chain Data Analyst",
    rationale="adjacent",
    missing_skills=["SQL", "dashboarding", "Python"],
    months_to_ready=5,
    est_cost_sgd=3000,
    reachable=True,
    confidence=0.7,
)


def window(week: int = 0, target: TargetRole = TARGET) -> tuple[int, int]:
    first = week + 1
    span = max(round(target.months_to_ready * _WEEKS_PER_MONTH), len(target.missing_skills))
    return first, first + span - 1


def test_steps_stacked_in_the_opening_weeks_are_spread_out():
    """The exact failure seen in the live run: everything in weeks 1 and 2."""
    first, last = window()
    paced = _paced(
        [step(1, "SQL"), step(2, "dashboarding"), step(2, "Python")], first, last
    )
    weeks = [s.week for s in paced]

    assert weeks == sorted(weeks), "steps came back out of order"
    assert len(set(weeks)) == len(weeks), "two steps share a week and complete together"
    assert max(weeks) > 4, f"a five-month plan still finishes in {max(weeks)} weeks: {weeks}"
    assert max(weeks) <= last, f"a step falls outside the training window: {weeks}"


def test_no_step_is_ever_scheduled_in_the_past():
    """A step dated before the current week is instantly 'complete'."""
    first, last = window(week=10)
    paced = _paced([step(1, "SQL"), step(2, "dashboarding")], first, last)
    assert all(s.week >= first for s in paced), (
        f"a step predates the week the plan was made: {[s.week for s in paced]}"
    )


def test_the_order_the_model_chose_is_preserved():
    """Only the weeks are rewritten — the sequence is the model's judgement."""
    first, last = window()
    gaps = ["SQL", "dashboarding", "Python"]
    paced = _paced([step(1, g) for g in gaps], first, last)
    assert [s.closes_gap for s in paced] == gaps


def test_a_single_step_lands_inside_the_window():
    first, last = window()
    (only,) = _paced([step(1, "SQL")], first, last)
    assert first <= only.week <= last

"""The shapes everyone imports. A break here breaks all five people.

Each test names the regression it exists to catch. If one fails, read that
sentence before reading the assertion — it says what the code was supposed to
guarantee, which is usually more useful than the diff.
"""

import pytest
from pydantic import ValidationError

from src.contracts import Stage, TargetRole


def test_stage_order_is_the_funnel_not_the_alphabet():
    """Stage(str, Enum) compares by spelling unless the operators are defined.

    Without them `Stage.OFFER > Stage.SCREENING` is False, because "offer"
    loses to "screening" on the first letter. That reads as correct and is not,
    so a threshold written with >= would silently misbehave.
    """
    assert Stage.OFFER > Stage.SCREENING
    assert Stage.TECHNICAL > Stage.RECRUITER
    assert Stage.SCREENING < Stage.FINAL
    assert [s.name for s in sorted(Stage)] == [
        "SCREENING", "RECRUITER", "TECHNICAL", "FINAL", "OFFER",
    ]


def test_stage_still_serialises_as_its_string():
    """The values go into documents, JSON and model output. Ordering must not
    have turned them into integers."""
    assert Stage.SCREENING.value == "screening"
    assert Stage.OFFER == "offer"


def test_confidence_outside_zero_to_one_is_rejected():
    """`confidence` is shown to a candidate as how sure we are. A model that
    returns 1.7 must fail here rather than on a slide."""
    with pytest.raises(ValidationError):
        TargetRole(
            title="x", rationale="y", missing_skills=[], months_to_ready=1,
            est_cost_sgd=1, reachable=True, confidence=1.7,
        )


def test_target_role_requires_keywords_not_positions():
    """Pydantic construction is keyword-only. With five owners, positional args
    into a seven-field shape break silently when a field is inserted."""
    with pytest.raises(TypeError):
        TargetRole("x", "y", [], 1, 1, True, 0.5)

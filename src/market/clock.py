"""The replay clock. Owner: R4.

The demo compresses six months into two minutes. That only works if the market
is a REPLAYABLE SERIES we control, not live data — we need to trigger the drift
event on cue, in every take, at the same week.

`snapshot(week)` is a pure function of `week`: call it twice for the same week
and you get exactly the same numbers back. That is what makes the replay
reproducible take after take, and what lets tests call it directly without
walking the whole graph first.
"""

from __future__ import annotations

import zlib

from ..contracts import MarketSnapshot

# Week the target role's hiring collapses. The first adaptation event.
DRIFT_WEEK = 10
HORIZON_WEEKS = 26

# The one role the scripted drift depends on. Do not rename without checking
# test_agent_loop.py's test_drift_fires_on_the_scripted_week_and_not_before —
# that test calls snapshot() directly and asserts the exact week this crosses
# the floor.
DRIFT_ROLE = "Supply Chain Data Analyst"

# Every role a persona might plausibly be targeted at, and its typical week's
# postings before any noise is applied. DRIFT_ROLE starts highest (so it is
# the obvious target at week 0) and, once it collapses, the runner-up becomes
# whichever the planner picks up instead — that hand-off is what makes the
# replan feel like a real pivot rather than a hardcoded second answer.
_ROLE_BASELINES: dict[str, int] = {
    DRIFT_ROLE: 130,
    "Customer Success Coordinator": 95,
    "Logistics Systems Analyst": 80,
    "Junior Data Analyst": 70,
    "Operations Business Partner": 65,
    "HR Coordinator": 50,
    "Project Coordinator": 55,
    "QA / Process Analyst": 40,
}

_SKILLS_IN_DEMAND: dict[str, float] = {
    "SQL": 0.8,
    "dashboarding": 0.6,
    "Python": 0.45,
    "stakeholder communication": 0.5,
}


def _noise(role: str, week: int, spread: int) -> int:
    """Deterministic pseudo-noise in [-spread, spread].

    A pure function of (role, week) rather than a seeded global RNG, so two
    different roles or two different weeks never accidentally share state,
    and a rerun of the same week always wobbles the same way.
    """
    seed = zlib.crc32(f"{role}:{week}".encode())
    return (seed % (2 * spread + 1)) - spread


def _drift_role_postings(week: int) -> int:
    """Supply Chain Data Analyst's trajectory: a real decline, not a cliff.

    Flat and healthy through week 4, eases down approaching the drift week,
    drops hard exactly at DRIFT_WEEK — that single crossing is the one the
    demo and the tests depend on — then stays low. The margin either side of
    the crossing (60 vs. the floor of 30, then 12) is wide enough that the
    +/-4 noise below can never flip which side of the floor a week lands on.
    """
    if week <= DRIFT_WEEK - 6:
        base = 130
    elif week < DRIFT_WEEK - 1:
        span = (DRIFT_WEEK - 2) - (DRIFT_WEEK - 6)
        t = (week - (DRIFT_WEEK - 6)) / span
        base = round(130 + (60 - 130) * t)
    elif week == DRIFT_WEEK - 1:
        base = 60  # comfortably above the floor
    elif week == DRIFT_WEEK:
        base = 12  # comfortably below the floor — the pivot fires here
    else:
        base = max(6, 18 - (week - DRIFT_WEEK))
    return max(0, base + _noise(DRIFT_ROLE, week, spread=4))


def _stable_role_postings(role: str, week: int) -> int:
    """Every other role: a mild wobble around its baseline for the whole run."""
    base = _ROLE_BASELINES[role]
    return max(0, base + _noise(role, week, spread=max(3, base // 12)))


def snapshot(week: int) -> MarketSnapshot:
    """The market as it looks in a given week."""
    postings = {
        role: (
            _drift_role_postings(week)
            if role == DRIFT_ROLE
            else _stable_role_postings(role, week)
        )
        for role in _ROLE_BASELINES
    }
    return MarketSnapshot(
        week=week,
        postings_by_role=postings,
        skills_in_demand=_SKILLS_IN_DEMAND,
    )


def has_drifted(market: MarketSnapshot, target_title: str, floor: int = 30) -> bool:
    """Deterministic, no model call, unit-testable. This drives a graph edge.

    Takes the week's snapshot rather than re-deriving it from the week number,
    so the router judges drift against exactly the numbers the rest of the
    graph is holding.
    """
    return market.postings_by_role.get(target_title, 0) < floor

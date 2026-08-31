"""The replay clock. Owner: R4.

The demo compresses six months into two minutes. That only works if the market
is a REPLAYABLE SERIES we control, not live data — we need to trigger the drift
event on cue, in every take, at the same week.

STUB — the shape is right, the numbers are made up. Make them plausible.
"""

from ..contracts import MarketSnapshot

# Week the target role's hiring collapses. The first adaptation event.
DRIFT_WEEK = 10
HORIZON_WEEKS = 26


def snapshot(week: int) -> MarketSnapshot:
    """The market as it looks in a given week."""
    # TODO(R4): make this a generated series with realistic noise, not a step
    # function. A cliff edge looks fake on the timeline.
    healthy = week < DRIFT_WEEK
    return MarketSnapshot(
        week=week,
        postings_by_role={
            "Supply Chain Data Analyst": 120 if healthy else 14,
            "Logistics Systems Analyst": 80,
            "Operations Business Partner": 65,
        },
        skills_in_demand={"SQL": 0.8, "dashboarding": 0.6, "Python": 0.45},
    )


def has_drifted(market: MarketSnapshot, target_title: str, floor: int = 30) -> bool:
    """Deterministic, no model call, unit-testable. This drives a graph edge.

    Takes the week's snapshot rather than re-deriving it from the week number,
    so the router judges drift against exactly the numbers the rest of the
    graph is holding.
    """
    return market.postings_by_role.get(target_title, 0) < floor

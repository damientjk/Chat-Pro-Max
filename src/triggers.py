"""Routing decisions. Owner: R2.

Every function here is ORDINARY PYTHON with no model call. That is deliberate:
control flow stays deterministic, testable without an API key, and reproducible
across every take of the demo video.

This is the file to point at when a judge asks how the agent decides to adapt.
"""

from .contracts import CaseState
from .market import clock
from .signals import rejection

PLACEMENT_WEEK = 18  # when training is far enough along to start applying


def route(state: CaseState) -> str:
    """Return the name of the next step. One decision, all in one place."""
    week = state["week"]
    target = state.get("target")
    market = state.get("market")

    if state.get("done"):
        return "end"
    if week >= clock.HORIZON_WEEKS:
        return "end"

    # --- adaptation event 1: the target stopped hiring --------------------
    if target and market and target.reachable and clock.has_drifted(market, target.title):
        return "drift"

    # --- adaptation event 2: the rejections share a shape -----------------
    since = state.get("signal_from_week", 0)
    recent = [a for a in state.get("applications", []) if a.week >= since]
    if rejection.diagnose(recent) == "reposition":
        return "reposition"

    # --- otherwise: apply if ready, else let another week pass ------------
    if week >= PLACEMENT_WEEK and state.get("plan"):
        return "apply"
    return "continue"

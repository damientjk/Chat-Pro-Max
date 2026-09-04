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

# Weeks between application batches. Two reasons, and they agree:
#
# Realism — nobody sends a fresh batch of applications every single week and
# gets every verdict back by the next one. A batch goes out, it takes weeks to
# come back, and only then is there anything new to learn from.
#
# Budget — placement.apply is by far the most expensive call in the graph
# (~2000 tokens a time). Applying every week from PLACEMENT_WEEK to the horizon
# is eight of them, ~16k tokens, against a free-tier ceiling of 8k per MINUTE.
# The run could not fit in its own budget and was rate-limited into failing.
# At three-week intervals it is three batches instead of eight.
APPLY_EVERY = 3


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
    # diagnose() reports WHAT the pattern is. What to DO about it is a routing
    # decision, so it lives here — including what a repeat of the same pattern
    # means, which diagnose() cannot know because it sees one window at a time.
    since = state.get("signal_from_week", 0)
    recent = [a for a in state.get("applications", []) if a.week >= since]
    diagnosis = rejection.diagnose(recent)

    if diagnosis == "reposition":
        # A second identical rewrite is not a second attempt. placement
        # .translate(repositioned=True) produces ONE rewrite; if that also dies
        # at screening, the framing has been tested and the target is what is
        # wrong. Without this the graph rewrites the same words every few weeks
        # for the rest of the horizon — which is what it used to do.
        return "retarget" if state.get("repositioned") else "reposition"

    if diagnosis == "replan_gap":
        # Screening is being passed; the interview is where it stops. That is a
        # gap in the plan, not in the wording, so it takes a different edge.
        return "replan_gap"

    # --- otherwise: apply if ready and due, else let another week pass ----
    if week >= PLACEMENT_WEEK and state.get("plan") and _batch_is_due(state, week):
        return "apply"
    return "continue"


def _batch_is_due(state: CaseState, week: int) -> bool:
    """Whether enough weeks have passed since the last batch went out.

    Derived from the applications themselves rather than a new CaseState field:
    contracts.py is frozen, and the answer is already in the data. The reducer
    only appends, so the most recent week is the last time we applied.
    """
    applications = state.get("applications", [])
    if not applications:
        return True  # nothing sent yet — start as soon as training allows
    return week - max(a.week for a in applications) >= APPLY_EVERY

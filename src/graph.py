"""The case supervisor. Owner: R2.

  START -> intake -> target -> plan -> advance_week
                                           |
                                       route()  <- triggers.py, pure Python
                                           |
            +--------------+---------------+--------------+
            |              |               |              |
          drift        reposition        apply        continue --+
            |              |               |                     |
          replan       reposition      placement                 |
            |              |               |                     |
            +--------------+---------------+---------------------+
                                    back to advance_week

Nodes are ordinary functions: state in, partial state out. LangGraph merges the
partial back. `events` and `applications` append rather than overwrite because
of the operator.add reducers in contracts.CaseState.

Every node below runs with NO model call in the stub build, so this graph runs
end to end with no API key. Replace the stubs one at a time; the wiring does
not change when you do.
"""

from langgraph.graph import END, START, StateGraph

from . import triggers
from .agents import archaeologist, placement, planner
from .contracts import CaseState, Event
from .market import clock


# --------------------------------------------------------------------------
# Nodes
# --------------------------------------------------------------------------


def intake(state: CaseState) -> dict:
    inventory = archaeologist.extract(state["candidate"])
    return {
        "inventory": inventory,
        "events": [Event(0, "intake", f"found {len(inventory.capabilities)} capabilities")],
    }


def target(state: CaseState) -> dict:
    chosen = planner.target(state["inventory"], state["week"])
    return {
        "target": chosen,
        "events": [
            Event(state["week"], "target", f"target: {chosen.title}", chosen.rationale)
        ],
    }


def plan(state: CaseState) -> dict:
    p = planner.plan(state["target"], state["week"])
    return {
        "plan": p,
        "events": [Event(state["week"], "plan", f"{len(p.steps)}-step plan to {p.target.title}")],
    }


def advance_week(state: CaseState) -> dict:
    week = state["week"] + 1
    return {"week": week, "market": clock.snapshot(week)}


def replan(state: CaseState) -> dict:
    """Adaptation event 1. The target stopped hiring; pick another and say why."""
    week = state["week"]
    old = state["target"]
    postings = clock.snapshot(week).postings_by_role.get(old.title, 0)

    # TODO(R3): ask the planner for the next-best target given what they have
    # already learned — some of the training carries over, and saying so is
    # what makes this feel like a plan rather than a restart.
    fresh = planner.target(state["inventory"], week)
    fresh.title = "Logistics Systems Analyst"
    fresh.rationale = "still hiring, and reuses the SQL work already done"

    return {
        "target": fresh,
        "plan": planner.plan(fresh, week, supersedes=old.title),
        "events": [
            Event(week, "drift", f"{old.title} postings fell to {postings}",
                  "below the floor we set for a viable target"),
            Event(week, "replan", f"switched to {fresh.title}", fresh.rationale),
        ],
    }


def reposition(state: CaseState) -> dict:
    """Adaptation event 2. Every application died at screening — rewrite it."""
    week = state["week"]
    return {
        "positioning": f"revised positioning for {state['target'].title}",
        "signal_from_week": week,  # old rejections no longer count
        "events": [
            Event(week, "reposition", "rewrote how we describe their experience",
                  "the last 3 applications all died at resume screening"),
        ],
    }


def apply_step(state: CaseState) -> dict:
    week = state["week"]
    repositioned = bool(state.get("positioning", "").startswith("revised"))
    positioning = state.get("positioning") or placement.translate(
        state["inventory"], state["plan"]
    )
    outcomes = placement.apply(state["plan"], week, positioning, repositioned)

    got_offer = any(not o.rejected for o in outcomes)
    events = [Event(week, "apply", f"{len(outcomes)} applications sent")]
    if got_offer:
        events.append(Event(week, "offer", f"offer: {state['target'].title}"))

    return {
        "applications": outcomes,
        "positioning": positioning,
        "events": events,
        "done": got_offer,
        "outcome": "placed" if got_offer else "",
    }


# --------------------------------------------------------------------------
# Wiring
# --------------------------------------------------------------------------


def build():
    g = StateGraph(CaseState)

    for name, fn in [
        ("intake", intake),
        ("target", target),
        ("plan", plan),
        ("advance_week", advance_week),
        ("replan", replan),
        ("reposition", reposition),
        ("apply", apply_step),
    ]:
        g.add_node(name, fn)

    g.add_edge(START, "intake")
    g.add_edge("intake", "target")
    g.add_edge("target", "plan")
    g.add_edge("plan", "advance_week")

    # The one decision point. triggers.route is pure Python — no model call.
    g.add_conditional_edges(
        "advance_week",
        triggers.route,
        {
            "drift": "replan",
            "reposition": "reposition",
            "apply": "apply",
            "continue": "advance_week",
            "end": END,
        },
    )

    # Everything loops back to the clock.
    for node in ("replan", "reposition", "apply"):
        g.add_edge(node, "advance_week")

    return g.compile()

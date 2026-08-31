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
        "events": [
            Event(week=0, kind="intake",
                  summary=f"found {len(inventory.capabilities)} capabilities")
        ],
    }


def target(state: CaseState) -> dict:
    chosen = planner.target(state["inventory"], state["market"], state["week"])
    return {
        "target": chosen,
        "events": [
            Event(week=state["week"], kind="target",
                  summary=f"target: {chosen.title}", because=chosen.rationale)
        ],
    }


def plan(state: CaseState) -> dict:
    p = planner.plan(state["target"], state["week"])
    return {
        "plan": p,
        "events": [
            Event(week=state["week"], kind="plan",
                  summary=f"{len(p.steps)}-step plan to {p.target.title}")
        ],
    }


def advance_week(state: CaseState) -> dict:
    week = state["week"] + 1
    return {"week": week, "market": clock.snapshot(week)}


def replan(state: CaseState) -> dict:
    """Adaptation event 1. The target stopped hiring; pick another and say why."""
    week = state["week"]
    market = state["market"]
    old = state["target"]
    postings = market.postings_by_role.get(old.title, 0)

    # The planner sees the market, so the new target is whatever is actually
    # hiring this week. Nothing is hardcoded here any more — this node states
    # the change, it does not decide it.
    #
    # TODO(R3): ask the planner for the next-best target given what they have
    # already learned — some of the training carries over, and saying so is
    # what makes this feel like a plan rather than a restart.
    fresh = planner.target(state["inventory"], market, week)

    return {
        "target": fresh,
        "plan": planner.plan(fresh, week, supersedes=old.title),
        "events": [
            Event(week=week, kind="drift",
                  summary=f"{old.title} postings fell to {postings}",
                  because="below the floor we set for a viable target"),
            Event(week=week, kind="replan", summary=f"switched to {fresh.title}",
                  because=fresh.rationale),
        ],
    }


def reposition(state: CaseState) -> dict:
    """Adaptation event 2. Every application died at screening — rewrite it."""
    week = state["week"]
    return {
        "positioning": placement.translate(
            state["inventory"], state["plan"], repositioned=True
        ),
        "repositioned": True,  # a flag, never something to read back out of the prose
        "signal_from_week": week,  # old rejections no longer count
        "events": [
            Event(week=week, kind="reposition",
                  summary="rewrote how we describe their experience",
                  because="the last 3 applications all died at resume screening"),
        ],
    }


def apply_step(state: CaseState) -> dict:
    week = state["week"]
    repositioned = state.get("repositioned", False)
    positioning = state.get("positioning") or placement.translate(
        state["inventory"], state["plan"]
    )
    outcomes = placement.apply(state["plan"], week, positioning, repositioned)

    got_offer = any(not o.rejected for o in outcomes)
    events = [Event(week=week, kind="apply", summary=f"{len(outcomes)} applications sent")]
    if got_offer:
        events.append(
            Event(week=week, kind="offer", summary=f"offer: {state['target'].title}")
        )

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

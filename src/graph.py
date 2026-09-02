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

import inspect

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import END, START, StateGraph

from . import triggers
from .agents import archaeologist, placement, planner
from .contracts import Capability, CaseState, Event, SkillInventory
from .market import clock


# --------------------------------------------------------------------------
# Persistence
# --------------------------------------------------------------------------


def _contract_types() -> list[tuple[str, str]]:
    """Every class defined in contracts.py, for the checkpoint allowlist.

    Derived, never hand-listed. LangGraph will only rebuild a custom class out
    of a checkpoint if it is named here, and the failure mode is SILENT: an
    unlisted type comes back as a plain dict, so `state["target"].title` raises
    AttributeError on resume and nowhere else. A list maintained by hand is a
    list that gets forgotten the first time someone adds a shape.
    """
    from . import contracts

    return [
        (contracts.__name__, name)
        for name, obj in vars(contracts).items()
        if inspect.isclass(obj) and obj.__module__ == contracts.__name__
    ]


def memory_checkpointer() -> MemorySaver:
    """In-process persistence that knows about our own types.

    TODO(R2): swap for SqliteSaver (pip install langgraph-checkpoint-sqlite)
    so a case survives a restart. Same interface, same serializer, one line.
    """
    return MemorySaver(
        serde=JsonPlusSerializer(allowed_msgpack_modules=_contract_types())
    )


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


def _training_completed(state: CaseState, week: int) -> list[Capability]:
    """Plan steps whose week has arrived, and which are not already capability.

    ASSUMPTION worth stating out loud: a step scheduled for week N is treated as
    done in week N. The candidate is assumed to follow the plan. A real system
    asks them to confirm, and this is where that confirmation would land.
    """
    plan = state.get("plan")
    inventory = state.get("inventory")
    if not plan or not inventory:
        return []

    have = {name.lower() for name in inventory.names()}
    return [
        Capability(
            skill=step.closes_gap,
            evidence=f"completed in week {step.week}: {step.description}",
        )
        for step in plan.steps
        if step.week <= week and step.closes_gap.lower() not in have
    ]


def advance_week(state: CaseState) -> dict:
    """One week passes. The market moves, and training that was due gets done.

    This is where the case ACCUMULATES rather than just ticking. Completed
    training is written back into the inventory as capability with the week it
    was earned — so from here on, every other node sees a person who can do
    more than they could last week. That is what makes a later pivot a pivot
    and not a restart.
    """
    week = state["week"] + 1
    update: dict = {"week": week, "market": clock.snapshot(week)}

    learned = _training_completed(state, week)
    if learned:
        current = state["inventory"]
        update["inventory"] = SkillInventory(
            capabilities=current.capabilities + learned
        )
        skills = ", ".join(c.skill for c in learned)
        update["events"] = [
            Event(week=week, kind="progress", summary=f"training done: {skills}",
                  because="the plan step scheduled for this week is complete, so "
                          "it counts as capability from now on"),
        ]
    return update


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
    inventory = state["inventory"]
    fresh = planner.target(inventory, market, week)

    # What the abandoned target needed, and they have now. The planner already
    # excludes these from the new plan because they are capability — this only
    # NAMES them, so the timeline can show the pivot keeping the work rather
    # than the candidate having to take it on trust.
    have = {name.lower() for name in inventory.names()}
    carried = [s for s in old.missing_skills if s.lower() in have]
    because = fresh.rationale
    if carried:
        because += f" — and keeps the {', '.join(carried)} work already done"

    return {
        "target": fresh,
        "plan": planner.plan(fresh, week, supersedes=old.title),
        "events": [
            Event(week=week, kind="drift",
                  summary=f"{old.title} postings fell to {postings}",
                  because="below the floor we set for a viable target"),
            Event(week=week, kind="replan", summary=f"switched to {fresh.title}",
                  because=because),
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


def build(checkpointer=None):
    """Compile the graph. Pass a checkpointer to make the case resumable.

    With one, LangGraph saves the whole state after every step, keyed by a
    thread id. That buys three things: the run can be resumed after a crash,
    any past week can be inspected or rewound to, and a human approval step can
    pause the graph and continue later — which is how `apply` becomes
    human-gated on Day 2 without restructuring anything.
    """
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

    return g.compile(checkpointer=checkpointer)

"""What the model is doing, while it is doing it. Owner: R2, for the UI layer.

The graph makes about nine model calls per case and, until now, none of them
were visible. The page showed the RESULT of each node and nothing about the
work, so a twelve-second call and an instant week-tick looked identical, and a
viewer had no way to tell that a model was involved at all.

This module wraps the five agent functions so each call announces itself:

    instrument(emit)

  ->  emit({"phase": "start", "agent": "Planner", "task": "choosing a ..."})
      emit({"phase": "end",   ..., "seconds": 6.2, "decision": "Logistics ..."})

WHY WRAP RATHER THAN EDIT THE AGENTS
------------------------------------
src/agents/ is R3's. graph.py looks each function up as a module attribute at
call time -- `planner.target(...)`, not a name imported into its own namespace
-- so replacing the attribute here intercepts every call without touching
either file. The alternative, threading a callback down through three agent
modules, would put display concerns in code that has no business knowing a UI
exists, and would collide with whatever R3 is editing.

The same indirection is what tests/conftest.py and scripts/preview_ui.py
already rely on to swap the agents for doubles.

WHAT `decision` IS FOR
----------------------
An elapsed time proves something happened; it does not say what. Each formatter
turns a return value into the one line a person would want -- the role that was
chosen and how confident the model was, how far a batch of applications got.
The formatters read only fields that contracts.py declares, which is the same
guarantee the page itself relies on.

Nothing here is imported by the graph, the agents, or the tests. It is display
scaffolding, and the run is identical with it removed.
"""

from __future__ import annotations

import time
from collections import Counter

from ..agents import archaeologist, placement, planner


# --------------------------------------------------------------------------
# Turning a return value into one readable line
# --------------------------------------------------------------------------


def _from_extract(inventory) -> str:
    n = len(inventory.capabilities)
    return f"{n} capabilit{'y' if n == 1 else 'ies'} evidenced from the CV"


def _from_target(role) -> str:
    line = f"{role.title} — {role.confidence:.0%} confident, {role.months_to_ready} months to ready"
    # reachable=False is the honest-refusal case the planner is allowed to
    # return. It changes the meaning of the whole line, so it cannot be dropped.
    return line if role.reachable else f"{line} — NOT reachable in their constraints"


def _from_plan(plan) -> str:
    if not plan.steps:
        return "no steps"
    weeks = [s.week for s in plan.steps]
    return f"{len(plan.steps)} steps, weeks {min(weeks)}–{max(weeks)}"


def _from_translate(positioning: str) -> str:
    # translate() returns headline / summary / proof points joined by blank
    # lines. The headline is the whole point of the rewrite, so it is the line
    # worth showing.
    headline = positioning.strip().splitlines()[0] if positioning.strip() else ""
    return f"“{headline}”" if headline else "positioning rewritten"


def _from_apply(outcomes) -> str:
    if not outcomes:
        return "no applications"
    tally = Counter(o.stage_reached.value for o in outcomes)
    spread = ", ".join(f"{n} {stage}" for stage, n in tally.most_common())
    return f"{len(outcomes)} applications: {spread}"


# module, attribute, agent name, what it is doing in plain English, formatter
CALLS = [
    (archaeologist, "extract", "Skill Archaeologist",
     "reading the CV for evidence of what they can already do", _from_extract),
    (planner, "target", "Planner",
     "choosing a target role against this week's hiring", _from_target),
    (planner, "plan", "Planner",
     "sequencing training against the specific gap", _from_plan),
    (placement, "translate", "Positioner",
     "rewriting how they are described to employers", _from_translate),
    (placement, "apply", "Screener",
     "judging a batch of applications from the employer's side", _from_apply),
]

# Named here so the page can say which half of the system is NOT a model call.
# Stating that is what makes the model half legible: a viewer who is told the
# routing is deterministic understands that the agents are doing the judgement.
DETERMINISTIC = [
    ("src/triggers.py", "which adaptation to take, and when to apply"),
    ("src/market/clock.py", "the weekly market, and whether the target has drifted"),
    ("src/signals/rejection.py", "the shape of the rejections coming back"),
]


def instrument(emit) -> None:
    """Wrap every agent function so `emit` sees each model call begin and end.

    Idempotent: calling it twice does not double-wrap, which matters because a
    second live run in the same process would otherwise report every call
    twice with nested timings.

    Exceptions propagate untouched — a failed call still reports its end, so a
    run that dies mid-node does not leave the page showing a spinner forever.
    """
    for module, attr, agent, task, describe in CALLS:
        original = getattr(module, attr)
        if getattr(original, "_instrumented", False):
            continue
        setattr(module, attr, _wrap(original, agent, task, describe, emit))


def _wrap(original, agent: str, task: str, describe, emit):
    def instrumented(*args, **kwargs):
        emit({"phase": "start", "agent": agent, "task": task})
        started = time.monotonic()
        try:
            result = original(*args, **kwargs)
        except Exception as exc:
            emit({
                "phase": "end", "agent": agent, "task": task,
                "seconds": round(time.monotonic() - started, 2),
                "decision": f"failed — {type(exc).__name__}",
                "failed": True,
            })
            raise
        emit({
            "phase": "end", "agent": agent, "task": task,
            "seconds": round(time.monotonic() - started, 2),
            "decision": _safely(describe, result),
            "failed": False,
        })
        return result

    instrumented._instrumented = True
    return instrumented


def _safely(describe, result) -> str:
    """A formatter must never be the reason a run fails.

    These read fields off model output. contracts.py validates the shapes, so
    this should not fire — but a display string is not worth taking a recorded
    demo run down for, and the call has already succeeded by the time we get
    here.
    """
    try:
        return describe(result)
    except Exception as exc:  # noqa: BLE001 — deliberately broad, see above
        return f"(could not summarise: {type(exc).__name__})"

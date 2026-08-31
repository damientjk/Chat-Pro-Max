"""Walk one candidate through six months. The Day 1 gate.

    uv run python -m src.run_demo

Runs with NO API key: every sub-agent is a stub and every routing decision is
ordinary Python. That is the point — the pipe is connected before anything is
intelligent, so each person can replace their own stub without waiting.
"""

from .contracts import CaseState
from .eval.personas import DEMO
from .graph import build
from .market import clock
from .signals import outcomes
from .ui.timeline import render


def initial_state() -> CaseState:
    return {
        "candidate": DEMO,
        "week": 0,
        # Week 0's market, so the target node has one before advance_week runs.
        "market": clock.snapshot(0),
        "applications": [],
        "events": [],
        "positioning": "",
        "repositioned": False,
        "signal_from_week": 0,
        "done": False,
        "outcome": "",
    }


def main() -> None:
    app = build()

    # The graph loops once per simulated week, so it needs far more than
    # LangGraph's default recursion_limit of 25.
    final = app.invoke(initial_state(), config={"recursion_limit": 200})

    print(f"\n  {DEMO.name}, {DEMO.age} — {DEMO.last_role}, {DEMO.last_industry}")
    print(f"  {clock.HORIZON_WEEKS} weeks\n")
    print(render(final["events"]))
    print(f"\n  {outcomes.summarise(final)}\n")


if __name__ == "__main__":
    main()

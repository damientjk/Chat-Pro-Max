"""Walk one candidate through six months. The Day 1 gate.

    uv run python -m src.run_demo

Runs with NO API key: every sub-agent is a stub and every routing decision is
ordinary Python. That is the point — the pipe is connected before anything is
intelligent, so each person can replace their own stub without waiting.
"""

from .contracts import CaseState
from .eval.personas import DEMO
from .graph import build, memory_checkpointer
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
    # Every step of the case is saved, so it can be inspected or resumed.
    app = build(checkpointer=memory_checkpointer())

    # A checkpointer needs a thread id — the identity of THIS case. One
    # candidate, one thread; that is what you resume or rewind to.
    config = {
        # The graph loops once per simulated week, so it needs far more than
        # LangGraph's default recursion_limit of 25.
        "recursion_limit": 200,
        "configurable": {"thread_id": f"case-{DEMO.name.lower().replace(' ', '-')}"},
    }
    # Streamed rather than invoked so the run reports progress. Nine sequential
    # model calls take a minute or more on Groq's free tier, and a terminal that
    # prints nothing for that long is indistinguishable from a hang — which
    # matters, because a malformed tool call really can take a run down.
    # stream_mode="values" yields the whole state after each step, so the last
    # one is exactly what invoke() would have returned.
    # Two stream modes at once: "values" yields the whole state after each step,
    # so the last one is exactly what invoke() would have returned; "updates"
    # names the node that just ran. Week alone is not enough — weeks 0 makes
    # three model calls before the counter moves, so a stall there would look
    # like a stall on nothing.
    final = None
    week = 0
    for mode, chunk in app.stream(
        initial_state(), config=config, stream_mode=["values", "updates"]
    ):
        if mode == "values":
            final = chunk
            week = chunk.get("week", week)
        else:
            for node in chunk:
                print(
                    f"\r  week {week:>2}/{clock.HORIZON_WEEKS}  {node:<14}",
                    end="",
                    flush=True,
                )
    print("\r" + " " * 48 + "\r", end="")

    print(f"\n  {DEMO.name}, {DEMO.age} — {DEMO.last_role}, {DEMO.last_industry}")
    print(f"  {clock.HORIZON_WEEKS} weeks\n")
    print(render(final["events"]))
    print(f"\n  {outcomes.summarise(final)}")

    # Proof the case is a record, not just a print. Every step is recoverable.
    history = list(app.get_state_history(config))
    print(f"  {len(history)} checkpoints saved — any week can be inspected or resumed\n")


if __name__ == "__main__":
    main()

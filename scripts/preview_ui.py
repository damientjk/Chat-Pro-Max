"""Preview the UI without a key, a network call, or a token.

    uv run python -m scripts.preview_ui

Renders the terminal timeline and the readiness footer from a full 26-week run
driven by the test doubles, so R5 can iterate on wording, alignment and colour
in about a fifth of a second instead of waiting minutes for a live run that may
be rate-limited half way through.

For the web version, `uv run python -m src.ui.web --replay` does the same job
against a recorded run.

WHY THIS IMPORTS FROM tests/
----------------------------
The doubles it needs already exist in tests/conftest.py and are kept honest by
tests/test_agent_doubles.py, which fails if one drifts from the real agent's
signature. A second copy here would be a second thing to keep in sync, and the
copy nobody runs is the one that goes stale. This is a development aid, not
part of the shipped agent, so the direction of that import is acceptable —
nothing under src/ depends on tests/.
"""

from src.graph import build, memory_checkpointer
from src.run_demo import initial_state
from src.ui.timeline import render, render_readiness


def install_doubles() -> None:
    """Swap the model-calling agents for the deterministic test doubles.

    Public because src/ui/web.py's --offline mode needs exactly this. One
    installer, so a double added here reaches both previews.
    """
    import src.agents.archaeologist as archaeologist
    import src.agents.placement as placement
    import src.agents.planner as planner
    from tests import conftest

    archaeologist.extract = conftest._extract
    planner.target = conftest._target
    planner.plan = conftest._plan
    placement.translate = conftest._translate
    placement.apply = conftest._apply


def main() -> None:
    install_doubles()

    app = build(checkpointer=memory_checkpointer())
    final = app.invoke(
        initial_state(),
        config={"recursion_limit": 200, "configurable": {"thread_id": "preview"}},
    )

    print()
    print(render(final["events"]))
    print()
    print(render_readiness(final.get("inventory"), final.get("target")))
    print()
    print(f"  outcome: {final.get('outcome') or 'ran out of runway'}")
    print("  (stub data — for layout only. Real numbers come from src.run_demo.)")
    print()


if __name__ == "__main__":
    main()

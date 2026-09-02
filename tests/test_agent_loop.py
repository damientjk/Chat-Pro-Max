"""The loop itself. Owner: R2.

The end-to-end test is the Day 3 gate written down: both adaptation events
fire and the candidate is placed. If that one fails, the demo is broken —
check it before anything else.
"""

from src.agents import archaeologist, planner
from src.contracts import ApplicationOutcome, Capability, SkillInventory, Stage
from src.graph import _training_completed, build, memory_checkpointer
from src.market import clock
from src.run_demo import initial_state
from src.signals import rejection
from src.triggers import route


def run_case(thread: str = "test"):
    """One full 26-week run, checkpointed, exactly as the demo does it."""
    app = build(checkpointer=memory_checkpointer())
    config = {"recursion_limit": 200, "configurable": {"thread_id": thread}}
    return app, config, app.invoke(initial_state(), config=config)


# --------------------------------------------------------------------------
# The gate
# --------------------------------------------------------------------------


def test_both_adaptation_events_fire_and_the_candidate_is_placed():
    """PLAN.md's non-negotiable Day 3 gate. Everything else is detail."""
    _, _, final = run_case()
    kinds = [e.kind for e in final["events"]]

    assert "drift" in kinds, "market drift was never detected"
    assert "replan" in kinds, "drift did not produce a new target"
    assert "reposition" in kinds, "the rejection pattern never triggered a rewrite"
    assert final["outcome"] == "placed"


def test_every_adaptation_states_a_reason():
    """An adaptation with no `because` is invisible to a judge, which for our
    purposes means it did not happen."""
    _, _, final = run_case()
    for e in final["events"]:
        if e.kind in ("drift", "replan", "reposition"):
            assert e.because, f"{e.kind} at week {e.week} has no reason"


# --------------------------------------------------------------------------
# Adaptation 1 — the market moves
# --------------------------------------------------------------------------


def test_drift_fires_on_the_scripted_week_and_not_before():
    """The demo depends on this landing on week 10 in every take."""
    target = "Supply Chain Data Analyst"
    assert not clock.has_drifted(clock.snapshot(clock.DRIFT_WEEK - 1), target)
    assert clock.has_drifted(clock.snapshot(clock.DRIFT_WEEK), target)


def test_the_pivot_keeps_training_already_done():
    """A re-plan that re-teaches SQL is a restart, not a pivot.

    Asked of the planner directly, at the moment of the pivot. Checking the
    FINAL plan instead would be wrong: a step planned at week 10 and completed
    at week 12 is still in that plan, and would look like re-teaching.
    """
    state = initial_state()
    base = archaeologist.extract(state["candidate"])
    trained = SkillInventory(
        capabilities=base.capabilities
        + [Capability(skill="SQL", evidence="completed in week 2: stub")]
    )

    fresh = planner.target(trained, clock.snapshot(clock.DRIFT_WEEK), clock.DRIFT_WEEK)
    assert "SQL" not in fresh.missing_skills, "the pivot re-teaches a skill already held"

    plan = planner.plan(fresh, clock.DRIFT_WEEK)
    assert "SQL" not in [s.closes_gap for s in plan.steps]


def test_training_done_before_the_pivot_is_recorded_as_capability():
    """End to end: what was learned in the first ten weeks is still theirs."""
    _, _, final = run_case()
    acquired = {n.lower() for n in final["inventory"].names()}
    assert "sql" in acquired, "training completed before week 10 was not recorded"


def test_completed_training_becomes_capability_once_only():
    """_training_completed is called every week. A step must not be added
    again each time its week has passed."""
    state = initial_state()
    state["inventory"] = archaeologist.extract(state["candidate"])
    state["target"] = planner.target(state["inventory"], state["market"], 0)
    state["plan"] = planner.plan(state["target"], 0)

    first = _training_completed(state, 5)
    assert first, "a step scheduled before week 5 should have completed"

    # fold them in, as advance_week does, then ask again
    state["inventory"] = type(state["inventory"])(
        capabilities=state["inventory"].capabilities + first
    )
    assert _training_completed(state, 5) == [], "the same training was counted twice"


# --------------------------------------------------------------------------
# Adaptation 2 — the rejections share a shape
# --------------------------------------------------------------------------


def test_three_screening_rejections_mean_reposition():
    apps = [
        ApplicationOutcome(week=18, role_title="x", stage_reached=Stage.SCREENING,
                           rejected=True)
        for _ in range(3)
    ]
    assert rejection.diagnose(apps) == "reposition"


def test_one_rejection_diagnoses_nothing():
    """MIN_SIGNAL exists so the agent does not rewrite someone's CV on the
    strength of a single no."""
    apps = [ApplicationOutcome(week=18, role_title="x",
                               stage_reached=Stage.SCREENING, rejected=True)]
    assert rejection.diagnose(apps) is None


def test_route_ends_the_case_once_an_offer_lands():
    state = initial_state()
    state["done"] = True
    assert route(state) == "end"


# --------------------------------------------------------------------------
# Persistence
# --------------------------------------------------------------------------


def test_checkpoints_restore_real_objects_not_dicts():
    """The failure this catches is silent: a contract type missing from the
    serializer allowlist comes back as a plain dict, so `target.title` raises
    AttributeError on resume and nowhere else."""
    app, config, _ = run_case(thread="restore")
    restored = app.get_state(config).values

    assert restored["target"].title, "target came back without attributes"
    assert restored["inventory"].names(), "inventory came back without methods"
    assert isinstance(restored["applications"][0].stage_reached, Stage)


def test_every_week_is_recoverable():
    """Checkpointing is the prerequisite for a human approval gate: the graph
    must be able to stop at a past step and carry on from there."""
    app, config, final = run_case(thread="history")
    weeks = {s.values.get("week") for s in app.get_state_history(config)}
    assert final["week"] in weeks
    assert clock.DRIFT_WEEK in weeks, "the week of the pivot was not saved"

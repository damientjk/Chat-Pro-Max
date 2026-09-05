"""Every diagnosis reaches an edge. Owner: R2.

signals/rejection.diagnose has always returned three verdicts. Until now the
router acted on one of them, so a technical-round pattern was detected and then
thrown away, and a screening pattern that survived a rewrite simply repeated the
rewrite. These tests pin the routing, not the diagnosis — R1 owns the thresholds.
"""

from src.contracts import ApplicationOutcome, Stage
from src.graph import build, memory_checkpointer
from src.run_demo import initial_state
from src.triggers import PLACEMENT_WEEK, route


def outcome(week: int, stage: Stage, rejected: bool = True) -> ApplicationOutcome:
    return ApplicationOutcome(
        week=week, role_title="Logistics Systems Analyst",
        stage_reached=stage, rejected=rejected,
    )


def state(**over) -> dict:
    """A case mid-flight, past the placement week, with a live plan."""
    base = {
        "week": PLACEMENT_WEEK + 1,
        "target": None,
        "market": None,
        "plan": object(),          # route only checks it is truthy
        "applications": [],
        "signal_from_week": 0,
        "repositioned": False,
        "done": False,
    }
    return {**base, "applications": list(base["applications"]), **over}


WEEK = PLACEMENT_WEEK + 1
SCREENED_OUT = [outcome(WEEK, Stage.SCREENING) for _ in range(3)]
LOST_AT_TECHNICAL = [outcome(WEEK, Stage.TECHNICAL) for _ in range(3)]


# --- the pattern that was already handled --------------------------------

def test_screening_rejections_rewrite_the_positioning():
    assert route(state(applications=SCREENED_OUT)) == "reposition"


# --- the two that were diagnosed and then dropped ------------------------

def test_technical_rejections_deepen_the_plan_rather_than_the_wording():
    """Screening is being passed, so the words are fine and the plan is not."""
    assert route(state(applications=LOST_AT_TECHNICAL)) == "replan_gap"


def test_screening_rejections_after_a_rewrite_change_the_target():
    """The rewrite is a one-shot test of the framing. It failed, so move on.

    This is the case that used to loop: a real 26-week run rewrote the
    positioning at week 21 and again at week 25, identically, because
    translate(repositioned=True) has only one rewrite to give.
    """
    assert route(state(applications=SCREENED_OUT, repositioned=True)) == "retarget"


# --- the window, which is what stops any of these repeating --------------

ADAPTATIONS = {"reposition", "replan_gap", "retarget", "drift"}


def test_rejections_before_the_last_adaptation_no_longer_count():
    """Each adaptation moves signal_from_week, closing the window behind it.

    What matters is that no adaptation fires, not which ordinary edge is taken —
    that depends on the application cadence, which is a separate concern.
    """
    answered = state(applications=SCREENED_OUT, signal_from_week=WEEK + 1)
    assert route(answered) not in ADAPTATIONS


def test_a_thin_pattern_changes_nothing():
    thin = state(applications=[outcome(WEEK, Stage.SCREENING)])
    assert route(thin) not in ADAPTATIONS


# --------------------------------------------------------------------------
# The nodes themselves, driven through the real graph
# --------------------------------------------------------------------------


def _always(stage: Stage):
    """A placement double whose applications always die at one stage."""
    def apply(plan, week, positioning, repositioned=False):
        return [
            ApplicationOutcome(
                week=week, role_title=plan.target.title,
                stage_reached=stage, rejected=True, notes="forced",
            )
            for _ in range(3)
        ]
    return apply


def run_with(monkeypatch, stage: Stage):
    monkeypatch.setattr("src.agents.placement.apply", _always(stage))
    app = build(checkpointer=memory_checkpointer())
    cfg = {"recursion_limit": 200, "configurable": {"thread_id": f"r-{stage.value}"}}
    return app.invoke(initial_state(), config=cfg)


def test_losing_at_technical_deepens_the_plan_in_a_real_run(monkeypatch):
    final = run_with(monkeypatch, Stage.TECHNICAL)
    summaries = [e.summary for e in final["events"] if e.kind == "replan"]
    assert any(s.startswith("deepened the plan for") for s in summaries), summaries


def test_a_failed_rewrite_abandons_the_target_in_a_real_run(monkeypatch):
    final = run_with(monkeypatch, Stage.SCREENING)
    kinds = [e.kind for e in final["events"]]
    summaries = [e.summary for e in final["events"]]

    assert "reposition" in kinds, "the first screening pattern should rewrite"
    assert any(s.startswith("abandoned ") for s in summaries), summaries


def test_the_positioning_never_describes_an_abandoned_target(monkeypatch):
    """A pivot that keeps the old framing applies for the new role in the old words.

    Empty is fine and expected — a reset means apply_step regenerates on the next
    batch. What must never happen is prose naming a target we have moved off.
    """
    final = run_with(monkeypatch, Stage.SCREENING)
    positioning = final["positioning"]
    assert positioning == "" or final["target"].title in positioning, (
        f"positioning {positioning!r} does not describe "
        f"the current target {final['target'].title!r}"
    )


def test_every_adaptation_still_states_a_reason(monkeypatch):
    final = run_with(monkeypatch, Stage.TECHNICAL)
    for e in final["events"]:
        if e.kind in {"drift", "replan", "reposition"}:
            assert e.because, f"{e.kind} at week {e.week} gave no reason"


# --------------------------------------------------------------------------
# Application cadence — the token budget, and the realism
# --------------------------------------------------------------------------

from src.triggers import APPLY_EVERY


def test_the_first_batch_goes_out_as_soon_as_training_allows():
    assert route(state(week=PLACEMENT_WEEK)) == "apply"


def test_no_second_batch_the_very_next_week():
    """Sending weekly is neither realistic nor affordable."""
    sent = [outcome(PLACEMENT_WEEK, Stage.SCREENING)]
    assert route(state(week=PLACEMENT_WEEK + 1, applications=sent)) == "continue"


def test_the_next_batch_goes_out_once_the_interval_has_passed():
    sent = [outcome(PLACEMENT_WEEK, Stage.SCREENING)]
    due = PLACEMENT_WEEK + APPLY_EVERY
    assert route(state(week=due, applications=sent)) == "apply"


def test_an_adaptation_still_outranks_the_cadence():
    """A diagnosed pattern is acted on immediately, not at the next batch."""
    sent = [outcome(PLACEMENT_WEEK, Stage.SCREENING) for _ in range(3)]
    assert route(state(week=PLACEMENT_WEEK + 1, applications=sent)) == "reposition"


# --------------------------------------------------------------------------
# How a case ENDS — contracts.py names two ways, and both must be recorded
# --------------------------------------------------------------------------


def test_a_case_that_never_places_says_so(monkeypatch):
    """An empty outcome cannot be told apart from a run still in progress.

    contracts.py has always advertised "ran_out_of_runway"; before this it was
    documentation for a value nothing ever set.
    """
    final = run_with(monkeypatch, Stage.SCREENING)

    assert final["outcome"] == "ran_out_of_runway"


def test_an_offer_is_not_overwritten_by_the_final_tick(monkeypatch):
    """The horizon guard must not clobber a placement that already landed."""
    final = build(checkpointer=memory_checkpointer()).invoke(
        initial_state(),
        config={"recursion_limit": 200, "configurable": {"thread_id": "placed"}},
    )

    assert final["outcome"] == "placed"

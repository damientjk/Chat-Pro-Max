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


def test_a_rewrite_is_tested_in_the_week_it_is_written(monkeypatch):
    """A reposition must be followed immediately by a batch carrying it.

    Not a nicety. The rejection pattern needs three rejections at one stage, so
    in a real run it fired at week 25; the next scheduled batch would have been
    week 27 and route() ends the case at 26. The second adaptation event was
    firing and then never being given a chance to pay off, which is why no run
    could end placed. If this fails, that is back.
    """
    final = run_with(monkeypatch, Stage.SCREENING)

    weeks = {e.kind: e.week for e in final["events"] if e.kind == "reposition"}
    assert weeks, "no reposition happened, so this test proves nothing"
    rewrite_week = weeks["reposition"]

    applied = [e.week for e in final["events"] if e.kind == "apply"]
    assert rewrite_week in applied, (
        f"rewrote at week {rewrite_week} but the next batch went out at "
        f"{[w for w in applied if w > rewrite_week] or 'never'} — "
        "the rewrite was never sent to anyone"
    )


def _gap_state(week: int = 20):
    """A case that has been losing at the technical round, ready for replan_gap."""
    from src.agents import archaeologist, planner
    from src.market import clock

    inventory = archaeologist.extract(initial_state()["candidate"])
    market = clock.snapshot(week)
    target = planner.target(inventory, market, week)
    return {
        "week": week,
        "inventory": inventory,
        "market": market,
        "target": target,
        "plan": planner.plan(target, week),
        "applications": [outcome(week, Stage.TECHNICAL) for _ in range(3)],
        "signal_from_week": 0,
        "repositioned": False,
    }


def test_a_gap_replan_that_keeps_the_target_says_it_deepened_the_plan():
    from src.graph import replan_gap

    state = _gap_state()
    event = replan_gap(state)["events"][0]
    assert event.summary == f"deepened the plan for {state['target'].title}"


def test_a_gap_replan_that_moves_the_target_says_so(monkeypatch):
    """replan_gap usually deepens the plan for the same role. When the planner
    comes back with a DIFFERENT one, the timeline has to report a switch.

    This is the case that went wrong in a real run: the target moved from
    Logistics Systems Analyst to Customer Success Coordinator at week 25, and
    the event still read "deepened the plan for Customer Success Coordinator" —
    so the only trace of the change was a role name that had quietly altered,
    with nothing on the timeline to account for it.
    """
    from src.contracts import TargetRole
    from src.graph import replan_gap

    state = _gap_state()
    # Pin the role they were on. The double picks whatever is hiring most that
    # week, which at week 20 is already Customer Success Coordinator — leave it
    # and the test asserts a switch that never had anywhere to go.
    state["target"] = state["target"].model_copy(
        update={"title": "Logistics Systems Analyst"}
    )
    old_title = state["target"].title

    def moved_on(inventory, market, week):
        return TargetRole(
            title="Customer Success Coordinator",
            rationale="stub: the interview keeps testing something this role does not need",
            missing_skills=["CRM platform proficiency"],
            months_to_ready=3,
            est_cost_sgd=2000,
            reachable=True,
            confidence=0.8,
        )

    monkeypatch.setattr("src.agents.planner.target", moved_on)
    update = replan_gap(state)
    event = update["events"][0]

    assert event.summary == f"switched from {old_title} to Customer Success Coordinator"
    # and the reason carries the NEW role's own rationale, not only the
    # rejection pattern that triggered the re-plan
    assert "the target moved too" in event.because, event.because
    assert "does not need" in event.because, event.because
    # a different target means the old framing has to go with it
    assert update["positioning"] == ""

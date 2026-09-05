"""Tests for eval/harness.py. Runs against the same stub doubles as the rest
of the suite (see conftest.py) — no API key required, no real numbers implied.
This checks the harness's arithmetic is correct, not what the real cohort
will score once R3's agents are wired in.
"""

from src.eval import harness
from src.eval.personas import ALL, DEMO
from src.market import clock


def test_agent_case_runs_to_completion():
    final, history = harness.run_agent_case(DEMO)
    assert final.get("week", 0) <= clock.HORIZON_WEEKS
    assert final.get("done") is True
    assert len(history) > 1


def test_agent_case_catches_the_scripted_drift():
    """The doubles script exactly one collapse, at DRIFT_WEEK. The harness
    should see it, whichever role happened to be on top when it fired."""
    _final, history = harness.run_agent_case(DEMO)
    outcome = harness.derive_outcome(history)

    assert outcome.dead_paths_caught == 1
    assert outcome.months_saved >= 0
    assert outcome.training_spend_avoided >= 0.0


def test_baseline_case_is_a_single_week_zero_decision():
    decision = harness.run_baseline_case(DEMO)

    assert decision.replans == 0
    assert decision.open_gaps >= 0
    assert decision.gaps_already_closed == 0  # nothing trained yet at week 0


def test_baseline_lands_on_the_role_that_later_drifts():
    """With the doubles, week 0's top-postings role is exactly the one
    DRIFT_WEEK collapses — so the naive pick should register as a dead path."""
    decision = harness.run_baseline_case(DEMO)
    dead_path_week_market = clock.snapshot(clock.DRIFT_WEEK)

    assert clock.has_drifted(dead_path_week_market, decision.target_role_title)


def test_evaluate_scores_the_full_cohort():
    report = harness.evaluate(candidates=ALL)

    assert len(report.per_persona) == len(ALL)
    assert report.metrics.candidates == len(ALL)
    # Every persona in this stubbed world converges on the same market-driven
    # target, so every baseline pick and every agent catch should agree.
    assert report.baseline_dead_path_count == len(ALL)
    assert report.metrics.agent_dead_paths_caught == len(ALL)


def test_render_summary_mentions_the_headline_numbers():
    report = harness.evaluate(candidates=[DEMO])
    summary = harness.render_summary(report)

    assert "1 candidates evaluated" in summary
    assert f"week {clock.DRIFT_WEEK}" in summary

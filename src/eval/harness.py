"""Score agent vs baseline across the personas. Owner: R4.

This is where the benefits slide's one number comes from: how many candidates
the naive, one-shot recommender left on a target that had already stopped
hiring, against how many the adaptive agent caught and pivoted away from —
plus the months and spend that pivot saved.

TWO RUNS PER PERSONA
---------------------
`run_baseline_case` calls baseline.naive.run once, against week zero's market,
and never looks again — same as the naive.py docstring promises.

`run_agent_case` walks the same candidate through the full graph, with a
checkpointer, to the end of the horizon. The checkpointer is not incidental:
`derive_outcome` needs to see the target as it looked BEFORE each replan, not
just how the case ended up, and the checkpoint history is where that lives.
Re-deriving it from the events log would mean parsing prose that R5 owns for
the timeline, not scoring.

Run this after the graph is wired to the real sub-agents (R3) for the actual
numbers; against the test doubles in tests/conftest.py it still runs end to
end, which is what the tests below check, but every persona converges on the
same market-driven target, since the double ignores the candidate's own
inventory content. That is expected — it proves the harness's arithmetic is
right, not what the real cohort will do.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..baseline.naive import BaselineRecommendation, run as run_baseline
from ..contracts import CandidateProfile, CaseState, Plan, TargetRole
from ..graph import build, memory_checkpointer
from ..market import clock
from ..signals.outcomes import AgentOutcome, BenefitMetrics, calculate_benefits
from .personas import ALL, EXPECTED_TARGET

# LangGraph's default recursion_limit (25) is far too low for a 26-week loop
# with several nodes per week. Same figure run_demo.py uses, for the same
# reason — keep these in sync if the horizon changes.
RECURSION_LIMIT = 200

# Weeks per month, for turning the plan's week-based clock into the
# month-based units the benefits slide reports in. Not a contracts.py
# constant because nothing in the graph itself needs it — only this scoring.
WEEKS_PER_MONTH = 4.345


def _initial_state(candidate: CandidateProfile) -> CaseState:
    return {
        "candidate": candidate,
        "week": 0,
        "market": clock.snapshot(0),
        "applications": [],
        "events": [],
        "positioning": "",
        "repositioned": False,
        "signal_from_week": 0,
        "done": False,
        "outcome": "",
    }


def run_agent_case(candidate: CandidateProfile) -> tuple[CaseState, list]:
    """Walk one candidate through the full horizon.

    Returns the final state AND the full checkpoint history in chronological
    order (oldest first — LangGraph's own get_state_history comes back
    newest-first, which is the wrong direction for replaying "what did we
    believe at each step").
    """
    app = build(checkpointer=memory_checkpointer())
    config = {
        "recursion_limit": RECURSION_LIMIT,
        "configurable": {
            "thread_id": f"eval-{candidate.name.lower().replace(' ', '-')}"
        },
    }
    final = app.invoke(_initial_state(candidate), config=config)
    history = list(reversed(list(app.get_state_history(config))))
    return final, history


def run_baseline_case(candidate: CandidateProfile) -> BaselineRecommendation:
    """The naive comparator, as a scoreable decision rather than a Plan.

    baseline.naive.run() only returns a Plan. At week 0, before any training
    has happened, every one of the target's missing_skills is still open and
    none are closed — so unlike recommend_once(), there is no need to
    re-derive the gap against an inventory here; the answer at week 0 is
    always (all missing, none closed).
    """
    plan = run_baseline(candidate)
    target = plan.target
    return BaselineRecommendation(
        target_role_title=target.title,
        open_gaps=len(target.missing_skills),
        gaps_already_closed=0,
        months_to_ready=target.months_to_ready,
        est_cost_sgd=target.est_cost_sgd,
        rationale=target.rationale,
    )


def _dead_path_catches(
    history: list,
) -> list[tuple[TargetRole, TargetRole, Plan, int]]:
    """(old_target, fresh_target, old_plan, week) for every drift this case caught.

    Walks consecutive checkpoints rather than parsing the events log: the
    events are prose for R5's timeline, but the state itself is the source of
    truth for what target and plan we actually held right before the pivot.
    replan() appends its "drift" and "replan" events together in one step, so
    the checkpoint just before that step still holds the abandoned target.
    """
    caught = []
    for prev, curr in zip(history, history[1:]):
        prev_events = prev.values.get("events", [])
        curr_events = curr.values.get("events", [])
        new_events = curr_events[len(prev_events):]
        if not any(e.kind == "drift" for e in new_events):
            continue
        old_target = prev.values.get("target")
        old_plan = prev.values.get("plan")
        fresh_target = curr.values.get("target")
        if old_target and old_plan and fresh_target:
            caught.append((old_target, fresh_target, old_plan, curr.values.get("week", 0)))
    return caught


def derive_outcome(history: list) -> AgentOutcome:
    """Turn one completed case's checkpoint history into the benefit numbers.

    dead_paths_caught: how many times a target's hiring collapsed and the case
    pivoted away from it instead of riding it to nothing, the way the
    baseline would.

    months_saved / training_spend_avoided: for each catch, how much of the
    abandoned target's remaining runway and budget was never spent. Both are
    prorated from the old target's own months_to_ready / est_cost_sgd against
    how far into it the candidate already was when the market moved — caught
    early, most of it is saved; caught on the way to the finish line, less is.
    This is a proxy, not an audited figure: it is answering "how much of a
    dead path did we avoid walking", not billing anyone's actual spend.
    """
    caught = _dead_path_catches(history)

    months_saved = 0
    spend_avoided = 0.0
    for old_target, _fresh, old_plan, week in caught:
        elapsed_weeks = max(0, week - old_plan.created_week)
        elapsed_months = elapsed_weeks / WEEKS_PER_MONTH
        remaining_months = max(0.0, old_target.months_to_ready - elapsed_months)
        months_saved += round(remaining_months)
        if old_target.months_to_ready > 0:
            spend_avoided += old_target.est_cost_sgd * (
                remaining_months / old_target.months_to_ready
            )

    return AgentOutcome(
        dead_paths_caught=len(caught),
        months_saved=months_saved,
        training_spend_avoided=round(spend_avoided, 2),
    )


@dataclass(frozen=True)
class PersonaResult:
    """One candidate's side-by-side result — what the deck's before/after slide is."""

    name: str
    expected_target: str
    baseline: BaselineRecommendation
    baseline_on_dead_path: bool
    agent_outcome: AgentOutcome
    agent_final_target: str
    agent_placed: bool


@dataclass(frozen=True)
class EvalReport:
    per_persona: list[PersonaResult]
    metrics: BenefitMetrics

    @property
    def baseline_dead_path_count(self) -> int:
        """How many of the naive picks were on a target that had already
        stopped hiring by DRIFT_WEEK — the number the pitch's baseline half
        depends on."""
        return sum(1 for p in self.per_persona if p.baseline_on_dead_path)

    @property
    def agent_placed_count(self) -> int:
        return sum(1 for p in self.per_persona if p.agent_placed)


def evaluate(candidates: list[CandidateProfile] = ALL) -> EvalReport:
    """Run both systems across every persona and score them against each other."""
    dead_path_week_market = clock.snapshot(clock.DRIFT_WEEK)

    per_persona: list[PersonaResult] = []
    baseline_decisions: list[BaselineRecommendation] = []
    agent_outcomes: list[AgentOutcome] = []

    for candidate in candidates:
        decision = run_baseline_case(candidate)
        on_dead_path = clock.has_drifted(dead_path_week_market, decision.target_role_title)

        final, history = run_agent_case(candidate)
        outcome = derive_outcome(history)
        final_target = final.get("target")

        baseline_decisions.append(decision)
        agent_outcomes.append(outcome)
        per_persona.append(
            PersonaResult(
                name=candidate.name,
                expected_target=EXPECTED_TARGET.get(candidate.name, ""),
                baseline=decision,
                baseline_on_dead_path=on_dead_path,
                agent_outcome=outcome,
                agent_final_target=final_target.title if final_target else "",
                agent_placed=final.get("outcome") == "placed",
            )
        )

    metrics = calculate_benefits(baseline_decisions, agent_outcomes)
    return EvalReport(per_persona=per_persona, metrics=metrics)


def render_summary(report: EvalReport) -> str:
    """The one paragraph the benefits slide is built from."""
    n = len(report.per_persona)
    lines = [
        f"{n} candidates evaluated",
        f"baseline: {report.baseline_dead_path_count} of {n} put on a target "
        f"that had closed by week {clock.DRIFT_WEEK}",
        f"agent: caught {report.metrics.agent_dead_paths_caught} dead path(s) "
        f"across the cohort, placed {report.agent_placed_count} of {n}",
        f"~{report.metrics.months_saved} month(s) of training saved, "
        f"~S${report.metrics.training_spend_avoided:,.0f} in wasted spend avoided",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    # uv run python -m src.eval.harness
    report = evaluate()
    print(render_summary(report))
    print()
    for p in report.per_persona:
        print(
            f"  {p.name:20s} baseline -> {p.baseline.target_role_title:28s} "
            f"agent -> {p.agent_final_target:28s} placed={p.agent_placed}"
        )

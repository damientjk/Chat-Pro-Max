"""Test doubles for the sub-agent boundary. Owner: R2.

WHY THIS EXISTS
---------------
graph.py is the thing under test: the nodes, the edges, and the routing between
them. The prompts are not. Once Day 2 replaced the sub-agent stubs with real
`chat_model()` calls, every graph test became a live network call — which meant
the suite needed a Groq key, cost tokens to run, and could fail because a model
phrased something differently rather than because the graph was wrong.

So the five agent functions are replaced here with deterministic doubles. They
are the Day 1 stubs, kept because the demo's shape was tuned against them: the
target drifts at week 10, screening rejections accumulate, and the rewrite
produces the offer. Assertions about that shape stay meaningful.

R3 owns the real implementations. Nothing here is imported by src/ — if a
signature in src/agents/ changes, the double below must change with it, and the
test that catches the mismatch is the one you want to fail.

To exercise the real agents instead, run the demo: `uv run python -m src.run_demo`.
"""

import inspect

import pytest

from src.agents import archaeologist, placement, planner
from src.contracts import (
    ApplicationOutcome,
    CandidateProfile,
    Capability,
    MarketSnapshot,
    Plan,
    PlanStep,
    SkillInventory,
    Stage,
    TargetRole,
)


def _extract(candidate: CandidateProfile) -> SkillInventory:
    return SkillInventory(
        capabilities=[
            Capability(skill="vendor contract management", evidence="stub: managed 3PL SLAs"),
            Capability(skill="data reconciliation", evidence="stub: monthly stock variance"),
            Capability(skill="stakeholder escalation", evidence="stub: ran carrier disputes"),
        ]
    )


def _target(inventory: SkillInventory, market: MarketSnapshot, week: int) -> TargetRole:
    # Market-driven rather than hardcoded: the role hiring most this week, and
    # the in-demand skills they cannot yet evidence. That is what lets the
    # replan node produce a live answer instead of a scripted one.
    ranked = sorted(market.postings_by_role.items(), key=lambda kv: -kv[1])
    title, postings = ranked[0] if ranked else ("Supply Chain Data Analyst", 0)

    have = {name.lower() for name in inventory.names()}
    missing = [s for s in market.skills_in_demand if s.lower() not in have][:2]

    return TargetRole(
        title=title,
        rationale=(
            f"stub: hiring holds at {postings} postings, "
            "and the reconciliation experience transfers"
        ),
        missing_skills=missing,
        months_to_ready=4,
        est_cost_sgd=2500,
        reachable=True,
        confidence=0.72,
    )


def _plan(target_role: TargetRole, week: int, supersedes: str | None = None) -> Plan:
    return Plan(
        target=target_role,
        steps=[
            PlanStep(week=week + 2, description=f"stub: close {s}", closes_gap=s, kind="course")
            for s in target_role.missing_skills
        ],
        created_week=week,
        supersedes=supersedes,
    )


def _translate(inventory: SkillInventory, plan: Plan, repositioned: bool = False) -> str:
    if repositioned:
        return f"stub positioning for {plan.target.title}, rewritten after screening rejections"
    return f"stub positioning for {plan.target.title}"


def _apply(
    plan: Plan, week: int, positioning: str, repositioned: bool = False
) -> list[ApplicationOutcome]:
    # Fails everything at SCREENING so the rejection signal fires, then succeeds
    # once the positioning has been rewritten. That is what makes the second
    # adaptation event visible.
    if repositioned:
        return [
            ApplicationOutcome(
                week=week,
                role_title=plan.target.title,
                stage_reached=Stage.OFFER,
                rejected=False,
                notes="stub",
            )
        ]
    return [
        ApplicationOutcome(
            week=week,
            role_title=plan.target.title,
            stage_reached=Stage.SCREENING,
            rejected=True,
            notes="stub",
        )
        for _ in range(3)
    ]


# double -> the real function it stands in for. One list, so the fixture and
# the conformance test below cannot disagree about what is being replaced.
DOUBLES = (
    (archaeologist, "extract", _extract),
    (planner, "target", _target),
    (planner, "plan", _plan),
    (placement, "translate", _translate),
    (placement, "apply", _apply),
)

# Captured at import time, BEFORE the autouse fixture patches anything.
REAL_SIGNATURES = {
    f"{module.__name__}.{name}": inspect.signature(getattr(module, name))
    for module, name, _ in DOUBLES
}


@pytest.fixture(autouse=True)
def stub_agents(monkeypatch):
    """Swap every model-calling agent for a deterministic double.

    Autouse, so no test can reach the network by forgetting to ask for it.
    """
    for module, name, double in DOUBLES:
        monkeypatch.setattr(f"{module.__name__}.{name}", double)

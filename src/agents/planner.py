"""Targeting and planning. Owner: R3.

Two jobs:
  target()  pick reachable adjacent roles, and say what is NOT reachable
  plan()    sequence training against the specific gap

target() takes the week's MarketSnapshot because the whole product claim is
that we re-plan WHEN THE MARKET MOVES. A targeting function that cannot see
the market can only be corrected from outside, by hand — which is what
graph.replan used to do.

STUB — replace the bodies with real model calls. Keep the signatures.
"""

from ..contracts import MarketSnapshot, Plan, PlanStep, SkillInventory, TargetRole


def target(
    inventory: SkillInventory, market: MarketSnapshot, week: int
) -> TargetRole:
    # TODO(R3): ask the model for 2-3 adjacent roles with an honest gap
    # analysis. Include at least one with reachable=False — the honesty is
    # the product.
    #
    # The stub is deliberately market-driven rather than hardcoded: pick the
    # role hiring most this week, and call the in-demand skills they cannot
    # yet evidence the gap. That is enough for the replan node to get a live
    # answer instead of a scripted one.
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


def plan(target_role: TargetRole, week: int, supersedes: str | None = None) -> Plan:
    # TODO(R3): sequence real steps against target_role.missing_skills.
    return Plan(
        target=target_role,
        steps=[
            PlanStep(week=week + 2, description=f"stub: close {s}", closes_gap=s, kind="course")
            for s in target_role.missing_skills
        ],
        created_week=week,
        supersedes=supersedes,
    )

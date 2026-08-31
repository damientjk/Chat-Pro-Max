"""Targeting and planning. Owner: R3.

Two jobs:
  target()  pick reachable adjacent roles, and say what is NOT reachable
  plan()    sequence training against the specific gap

STUB — replace the bodies with real model calls. Keep the signatures.
"""

from ..contracts import Plan, PlanStep, SkillInventory, TargetRole


def target(inventory: SkillInventory, week: int) -> TargetRole:
    # TODO(R3): ask the model for 2-3 adjacent roles with an honest gap
    # analysis. Include at least one with reachable=False — the honesty is
    # the product.
    return TargetRole(
        title="Supply Chain Data Analyst",
        rationale="stub: reconciliation experience transfers directly",
        missing_skills=["SQL", "dashboarding"],
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
            PlanStep(week + 2, f"stub: close {s}", s, "course")
            for s in target_role.missing_skills
        ],
        created_week=week,
        supersedes=supersedes,
    )

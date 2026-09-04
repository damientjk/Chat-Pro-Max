"""Print R1's baseline decision, rejection signal and benefit numbers.

Runs on the shared contracts, offline, with no model call — so the numbers on
the benefits slide can be reproduced from a single command.
"""

from src.contracts import ApplicationOutcome, Capability, SkillInventory, Stage, TargetRole
from src.r1_workflow import analyse_case
from src.signals.outcomes import AgentOutcome, calculate_benefits

INVENTORY = SkillInventory(
    capabilities=[
        Capability(skill="Excel", evidence="built the ops team's variance workbook"),
        Capability(skill="Customer service", evidence="ran carrier disputes"),
        Capability(skill="Scheduling", evidence="inbound scheduling for a 3PL"),
    ]
)

SHORTLIST = [
    TargetRole(
        title="Data Analyst",
        rationale="strongest long-term ceiling, but the widest gap today",
        missing_skills=["SQL", "Python"],
        months_to_ready=9,
        est_cost_sgd=4200,
        reachable=True,
        confidence=0.55,
    ),
    TargetRole(
        title="Operations Coordinator",
        rationale="the scheduling and dispute work transfers almost intact",
        missing_skills=["Scheduling"],
        months_to_ready=3,
        est_cost_sgd=1200,
        reachable=True,
        confidence=0.81,
    ),
]

# Three straight screening rejections: the positioning is wrong, not the target.
OUTCOMES = [
    ApplicationOutcome(
        week=18, role_title="Operations Coordinator", stage_reached=Stage.SCREENING, rejected=True
    ),
    ApplicationOutcome(
        week=18, role_title="Operations Coordinator", stage_reached=Stage.SCREENING, rejected=True
    ),
    ApplicationOutcome(
        week=19, role_title="Operations Coordinator", stage_reached=Stage.SCREENING, rejected=True
    ),
    ApplicationOutcome(
        week=19, role_title="Operations Coordinator", stage_reached=Stage.RECRUITER, rejected=False
    ),
]


def main() -> None:
    analysis = analyse_case(INVENTORY, SHORTLIST, OUTCOMES)

    print(f"Baseline target: {analysis.baseline.target_role_title}")
    print(f"Baseline rationale: {analysis.baseline.rationale}")
    print(f"Re-plan signal: {analysis.needs_replan} - {analysis.replan_reason}")
    if analysis.guidance:
        print(
            f"Recommended change: {analysis.guidance.focus} - "
            f"{analysis.guidance.action}"
        )
    if analysis.replan_event:
        print(f"Day 2 event payload: {analysis.replan_event.to_state_payload()}")

    benefits = calculate_benefits(
        [analysis.baseline],
        [AgentOutcome(dead_paths_caught=1, months_saved=3, training_spend_avoided=1500)],
    )
    print(
        "Benefit comparison: "
        f"{benefits.agent_dead_paths_caught} dead path caught, "
        f"{benefits.months_saved} months saved, "
        f"${benefits.training_spend_avoided:,.0f} training spend avoided."
    )


if __name__ == "__main__":
    main()

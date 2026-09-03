"""A small R1-only demo until R2's shared contracts are available."""

from dataclasses import dataclass

from src.signals.outcomes import calculate_benefits
from src.r1_workflow import analyse_case


@dataclass
class Skills:
    skills: list[str]


@dataclass
class Role:
    id: str
    title: str
    required_skills: list[str]


@dataclass
class ApplicationOutcome:
    status: str
    stage: str


@dataclass
class AgentOutcome:
    dead_paths_caught: int
    months_saved: int
    training_spend_avoided: float


def main() -> None:
    analysis = analyse_case(
        Skills(["Excel", "Customer service", "Scheduling"]),
        [
            Role("data", "Data Analyst", ["SQL", "Python", "Excel"]),
            Role(
                "operations",
                "Operations Coordinator",
                ["Excel", "Customer service", "Scheduling"],
            ),
        ],
        [
            ApplicationOutcome("rejected", "screening"),
            ApplicationOutcome("rejected", "screening"),
            ApplicationOutcome("rejected", "screening"),
            ApplicationOutcome("advanced", "screening"),
        ],
    )
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

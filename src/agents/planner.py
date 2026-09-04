"""Targeting and planning. Owner: R3.

Two jobs:
  target()  pick a reachable adjacent role given what is hiring NOW, and be
            honest when the best available option is not actually reachable
  plan()    sequence training against the specific gap

target() takes the week's MarketSnapshot because the whole product claim is
that we re-plan WHEN THE MARKET MOVES. A role hiring at 14 postings this week is
not a viable target however good the fit -- that judgement has to see the market.
"""

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from .._common import structured
from ..contracts import MarketSnapshot, Plan, PlanStep, SkillInventory, TargetRole

# Below this many postings in a given week, a role is not worth training toward.
# Kept in step with market.clock.has_drifted so that targeting and the re-plan
# trigger agree on what "still hiring" means.
VIABILITY_FLOOR = 30

TARGET_SYSTEM = f"""You are a career-transition strategist.

Choose ONE target role the person should train toward next, given the skills
they already have and what the job market is hiring for THIS week.

Choose in TWO steps, in this order:

STEP 1 -- narrow to the roles that are actually available to them.
- Adjacent, not aspirational: the role must be reachable from their current
  capabilities with a few months of focused retraining.
- A role with fewer than {VIABILITY_FLOOR} postings this week is NOT a viable
  target, no matter how good the fit -- say so rather than sending them at a
  closing door.

STEP 2 -- among the roles that survive step 1, pick the one with the MOST
postings this week. Hiring volume is the tie-breaker, and it decides.
- Their capabilities are transferable, so several roles will look adjacent.
  When they do, the market decides between them. Passing over a role with far
  more openings for one with fewer is a worse outcome for this person, and you
  must not do it.
- A role whose TITLE resembles their old job title is not thereby the better
  choice. A title match is not evidence of anything: judge on the capabilities
  and the evidence lines, then on hiring volume. Someone who reconciled stock
  variance and built the team's reporting spreadsheet is a candidate for data
  and analyst roles, not only for roles with their old title in the name.

Honesty is the product. If the best available option genuinely cannot be
reached inside the person's stated constraints, return it with reachable=False
and explain why in the rationale. A tool that only ever says yes is not advice.

Fill every field:
- rationale: one or two sentences on why this role, grounded in their evidence
  and this week's hiring.
- missing_skills: the in-demand skills this role needs that they cannot yet
  evidence from their capabilities.
- months_to_ready and est_cost_sgd: an honest estimate to close that gap.
- reachable: true only if achievable within their constraints.
- confidence: your calibrated confidence in this recommendation, 0 to 1."""


def target(
    inventory: SkillInventory, market: MarketSnapshot, week: int
) -> TargetRole:
    llm = structured(TargetRole)
    postings = "\n".join(
        f"  {role}: {n} postings this week"
        for role, n in sorted(market.postings_by_role.items(), key=lambda kv: -kv[1])
    )
    demand = ", ".join(
        f"{skill} ({share:.0%} of postings)"
        for skill, share in market.skills_in_demand.items()
    )
    capabilities = "\n".join(
        f"  - {c.skill} (evidence: {c.evidence})" for c in inventory.capabilities
    )
    return llm.invoke(
        [
            SystemMessage(content=TARGET_SYSTEM),
            HumanMessage(
                content=(
                    f"Week {week} of their transition.\n\n"
                    f"What they can already do:\n{capabilities}\n\n"
                    f"What is hiring this week:\n{postings}\n\n"
                    f"Skills in demand: {demand}\n\n"
                    f"Viability floor: {VIABILITY_FLOOR} postings this week."
                )
            ),
        ]
    )


class _PlanDraft(BaseModel):
    """Transient container: with_structured_output needs a model, and we only
    want the model to produce the STEPS -- the target and supersedes are passed
    in, not re-invented by the model."""

    steps: list[PlanStep]


PLAN_SYSTEM = """You are sequencing a retraining plan.

Given a target role and the specific skills the person is missing, produce an
ordered list of concrete steps that each close ONE of those gaps. Keep it tight:
one focused step per missing skill, optionally a short capstone project that
combines them. Every step's closes_gap MUST be one of the missing skills given.
kind is one of: course, project, cert.

SPREAD THE STEPS ACROSS THE WHOLE TRAINING WINDOW you are given. A part-time
learner closing a real skills gap takes months, not a fortnight: schedule the
steps at roughly even intervals from the first week to the last, in the order
they must be learned. Do not stack them all into the opening weeks -- a plan
that claims someone is fully retrained two weeks in is not an honest plan."""

# Weeks per month, for turning the target's months_to_ready into a week span.
_WEEKS_PER_MONTH = 4.33


def plan(target_role: TargetRole, week: int, supersedes: str | None = None) -> Plan:
    llm = structured(_PlanDraft)

    # The window the steps have to fit inside. months_to_ready is the target's
    # own honest estimate, so the plan is paced by it rather than by whatever
    # the model feels like; at minimum one week per step, so a long plan with a
    # short estimate still gets ordered rather than piled onto a single week.
    first = week + 1
    span = max(
        int(round(target_role.months_to_ready * _WEEKS_PER_MONTH)),
        len(target_role.missing_skills) or 1,
    )
    last = first + span - 1

    draft = llm.invoke(
        [
            SystemMessage(content=PLAN_SYSTEM),
            HumanMessage(
                content=(
                    f"Target role: {target_role.title}\n"
                    f"Missing skills to close: {target_role.missing_skills}\n"
                    f"Estimated time to ready: {target_role.months_to_ready} months.\n"
                    f"Schedule the steps between week {first} and week {last} "
                    f"inclusive, spread across that span.\n"
                    + (
                        f"This plan replaces an abandoned path ({supersedes}); "
                        "reuse anything already learned and do not repeat it.\n"
                        if supersedes
                        else ""
                    )
                )
            ),
        ]
    )
    steps = draft.steps or [
        # Guard: never render a "0-step plan" on the timeline if the model
        # returns nothing usable.
        PlanStep(
            week=last,
            description=f"Consolidate readiness for {target_role.title}",
            closes_gap=(target_role.missing_skills or ["general readiness"])[0],
            kind="project",
        )
    ]
    return Plan(
        target=target_role,
        steps=_paced(steps, first, last),
        created_week=week,
        supersedes=supersedes,
    )


def _paced(steps: list[PlanStep], first: int, last: int) -> list[PlanStep]:
    """Force the steps into [first, last], in order, one per week at most.

    The window is a PROMPT instruction, and a prompt is not a guarantee. When
    the model ignored it the steps landed in weeks 1 and 2 of a five-month plan,
    and because graph._training_completed treats a step whose week has arrived
    as done, the candidate was credited with every missing skill a fortnight in
    -- fully "retrained" before the market had even moved. A plan that pretends
    someone is ready is worse than no plan, so the pacing is enforced here.

    Steps keep the order the model put them in; only their weeks are rewritten.
    """
    if not steps:
        return steps

    span = max(last - first, 0)
    stride = span / (len(steps) - 1) if len(steps) > 1 else 0

    paced = []
    for i, step in enumerate(steps):
        scheduled = first + round(i * stride)
        # Never earlier than the week before it, so two steps cannot collapse
        # onto one week and complete together.
        if paced and scheduled <= paced[-1].week:
            scheduled = paced[-1].week + 1
        paced.append(step.model_copy(update={"week": scheduled}))
    return paced

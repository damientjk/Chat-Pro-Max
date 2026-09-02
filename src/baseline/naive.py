"""One-shot recommender. Owner: R1.

Same inputs as the real agent. Picks once. Never re-plans. Never notices.

TODO(R1): run this to week 26 and record how many personas end on a target
that had closed by DRIFT_WEEK.

TWO ENTRY POINTS
----------------
`run` is the eval comparator: give it a candidate and it walks the same
archaeologist -> planner path the real agent walks, against week zero's market
and no other. R4's harness calls this.

`recommend_once` is the same rule with the search already done — hand it an
inventory and a shortlist of roles and it picks one. It exists because the
benefit numbers need a decision object with the gap and the cost on it, not a
Plan, and because it can be scored without running a graph.
"""

from dataclasses import dataclass
from typing import Iterable

from ..agents import archaeologist, planner
from ..contracts import CandidateProfile, Plan, SkillInventory, TargetRole
from ..market import clock


def run(candidate: CandidateProfile) -> Plan:
    inventory = archaeologist.extract(candidate)
    # Week 0's market and never another one. That is the whole point of the
    # baseline: it sees the market once, at the start, and never looks again.
    chosen = planner.target(inventory, clock.snapshot(0), week=0)
    return planner.plan(chosen, week=0)


@dataclass(frozen=True)
class BaselineRecommendation:
    """The baseline's single decision for one candidate."""

    target_role_title: str
    open_gaps: int
    gaps_already_closed: int
    months_to_ready: int
    est_cost_sgd: int
    rationale: str
    replans: int = 0  # always. The absence of this number is the comparison.


def _open_gap(inventory: SkillInventory, role: TargetRole) -> list[str]:
    """The role's missing skills that the candidate still cannot evidence.

    A TargetRole carries the gap as it looked when the planner wrote it. Training
    progress lands in the inventory afterwards, so re-checking here keeps the
    baseline from counting a gap the candidate has since closed.
    """
    have = {name.strip().lower() for name in inventory.names()}
    return [s for s in role.missing_skills if s.strip().lower() not in have]


def recommend_once(
    inventory: SkillInventory, target_roles: Iterable[TargetRole]
) -> BaselineRecommendation:
    """Choose the role with the smallest remaining gap, once.

    The function runs once only. Its output is intentionally immutable and
    always has ``replans == 0`` so it is a fair comparator for the real agent.
    Ties break on the planner's own confidence, so the choice is deterministic
    rather than dependent on the order the shortlist happened to arrive in.
    """
    roles = list(target_roles)
    if not roles:
        raise ValueError("At least one target role is required.")

    def score(role: TargetRole) -> tuple[int, float]:
        return len(_open_gap(inventory, role)), -role.confidence

    selected = min(roles, key=score)
    open_gaps = _open_gap(inventory, selected)
    closed = len(selected.missing_skills) - len(open_gaps)

    return BaselineRecommendation(
        target_role_title=selected.title,
        open_gaps=len(open_gaps),
        gaps_already_closed=closed,
        months_to_ready=selected.months_to_ready,
        est_cost_sgd=selected.est_cost_sgd,
        rationale=(
            "Selected once using the week-zero gap only: "
            f"{len(open_gaps)} skill(s) still missing, "
            f"{closed} already evidenced."
        ),
    )

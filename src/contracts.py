"""Shared types. Owner: R2.

DRAFT — this is a starting point for the Day 1 morning meeting, not a decision.
Argue with it, change it, then FREEZE it. Every other module imports from here,
so an unannounced change on Day 3 costs the whole team an afternoon.

Nothing in this file calls a model or the network. It is data shapes only.
"""

from __future__ import annotations

import operator
from dataclasses import dataclass, field
from enum import Enum
from typing import Annotated, Optional, TypedDict


# --------------------------------------------------------------------------
# Phase 0 — who the person is, and what they can actually do
# --------------------------------------------------------------------------


@dataclass
class CandidateProfile:
    """The raw input. What a person would tell us in the first conversation."""

    name: str
    age: int
    years_experience: int
    last_role: str
    last_industry: str
    history: str  # free text: the CV, in their own words
    constraints: str = ""  # "cannot relocate", "needs income within 4 months"


@dataclass
class Capability:
    """One thing they can do, and where we got it from.

    The evidence field is the whole point of the archaeologist: we claim
    'contract management' only because we can point at the line that shows it.
    """

    skill: str
    evidence: str


@dataclass
class SkillInventory:
    capabilities: list[Capability] = field(default_factory=list)

    def names(self) -> list[str]:
        return [c.skill for c in self.capabilities]


# --------------------------------------------------------------------------
# Phase 1 & 2 — where they are going, and how
# --------------------------------------------------------------------------


@dataclass
class TargetRole:
    """A candidate destination.

    `reachable` is deliberately allowed to be False. Saying what is NOT
    reachable is the advice nobody gives, and it is what protects their credits.
    """

    title: str
    rationale: str
    missing_skills: list[str]
    months_to_ready: int
    est_cost_sgd: int
    reachable: bool
    confidence: float  # 0.0 - 1.0, and we show it honestly


@dataclass
class PlanStep:
    week: int
    description: str
    closes_gap: str  # which missing skill this addresses
    kind: str  # "course" | "project" | "cert"


@dataclass
class Plan:
    target: TargetRole
    steps: list[PlanStep]
    created_week: int
    supersedes: Optional[str] = None  # title of the target we abandoned, if any


# --------------------------------------------------------------------------
# Phase 3 — the world, which does not sit still
# --------------------------------------------------------------------------


@dataclass
class MarketSnapshot:
    """One week of the job market. R4 generates a series of these."""

    week: int
    postings_by_role: dict[str, int]
    skills_in_demand: dict[str, float]  # skill -> share of postings requiring it


# --------------------------------------------------------------------------
# Phase 4 — applying, and what comes back
# --------------------------------------------------------------------------


class Stage(str, Enum):
    """How far an application got. The pattern across these is the signal."""

    SCREENING = "screening"
    RECRUITER = "recruiter"
    TECHNICAL = "technical"
    FINAL = "final"
    OFFER = "offer"


@dataclass
class ApplicationOutcome:
    week: int
    role_title: str
    stage_reached: Stage
    rejected: bool
    notes: str = ""


# --------------------------------------------------------------------------
# The event log — what the demo timeline renders
# --------------------------------------------------------------------------


@dataclass
class Event:
    """One thing the agent did or noticed, with the reason.

    R5 renders these as the timeline. If an adaptation is not in here with a
    `because`, the judges will not see it happen.
    """

    week: int
    kind: str  # "intake" | "target" | "plan" | "drift" | "replan" | "reposition" | "apply" | "offer"
    summary: str
    because: str = ""


# --------------------------------------------------------------------------
# CaseState — the LangGraph state object
# --------------------------------------------------------------------------


class CaseState(TypedDict, total=False):
    """The one object every node reads and writes.

    `events` and `applications` use operator.add so nodes APPEND rather than
    overwrite. Drop the Annotated wrapper and each node clobbers the history —
    the same mistake TODO 3 in the LangGraph lab teaches.
    """

    candidate: CandidateProfile
    inventory: SkillInventory
    target: Optional[TargetRole]
    plan: Optional[Plan]

    week: int
    market: Optional[MarketSnapshot]

    applications: Annotated[list[ApplicationOutcome], operator.add]
    events: Annotated[list[Event], operator.add]

    positioning: str  # how we currently describe them to employers

    # Rejections before this week are stale — a reposition resets the window.
    # The `applications` reducer only appends, so we move a pointer instead.
    signal_from_week: int

    done: bool
    outcome: str  # "placed" | "ran_out_of_runway" | ""

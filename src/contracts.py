"""Shared types. Owner: R2.

DRAFT — this is a starting point for the Day 1 morning meeting, not a decision.
Argue with it, change it, then FREEZE it. Every other module imports from here,
so an unannounced change on Day 3 costs the whole team an afternoon.

Nothing in this file calls a model or the network. It is data shapes only.

WHY PYDANTIC AND NOT DATACLASSES
--------------------------------
On Day 2 these stop being hand-built and start being what the model returns:

    llm.with_structured_output(TargetRole)

That takes a BaseModel. With dataclasses here, every agent owner writes a
private pydantic mirror of the same shape plus a conversion — two definitions
of one contract, which drift apart by Day 3. So the shapes are BaseModels and
there is exactly one definition of each.

The Field constraints are part of the contract, not decoration: confidence
really is 0.0-1.0, and pydantic raises if a model hands back 1.7 rather than
letting it reach the slide.

Pydantic makes construction keyword-only. Write Event(week=3, kind="drift", ...).
With five owners, positional args into a five-field shape are a bug waiting for
someone to add a field in the middle.

CaseState stays a TypedDict — that is what LangGraph wants for graph state.
"""

from __future__ import annotations

import operator
from enum import Enum
from typing import Annotated, Optional, TypedDict

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------
# Phase 0 — who the person is, and what they can actually do
# --------------------------------------------------------------------------


class CandidateProfile(BaseModel):
    """The raw input. What a person would tell us in the first conversation."""

    name: str
    age: int = Field(ge=0)
    years_experience: int = Field(ge=0)
    last_role: str
    last_industry: str
    history: str  # free text: the CV, in their own words
    constraints: str = ""  # "cannot relocate", "needs income within 4 months"


class Capability(BaseModel):
    """One thing they can do, and where we got it from.

    The evidence field is the whole point of the archaeologist: we claim
    'contract management' only because we can point at the line that shows it.
    """

    skill: str
    evidence: str


class SkillInventory(BaseModel):
    capabilities: list[Capability] = Field(default_factory=list)

    def names(self) -> list[str]:
        return [c.skill for c in self.capabilities]


# --------------------------------------------------------------------------
# Phase 1 & 2 — where they are going, and how
# --------------------------------------------------------------------------


class TargetRole(BaseModel):
    """A candidate destination.

    `reachable` is deliberately allowed to be False. Saying what is NOT
    reachable is the advice nobody gives, and it is what protects their credits.
    """

    title: str
    rationale: str
    missing_skills: list[str]
    months_to_ready: int = Field(ge=0)
    est_cost_sgd: int = Field(ge=0)
    reachable: bool
    confidence: float = Field(ge=0.0, le=1.0)  # and we show it honestly


class PlanStep(BaseModel):
    week: int = Field(ge=0)
    description: str
    closes_gap: str  # which missing skill this addresses
    kind: str  # "course" | "project" | "cert"


class Plan(BaseModel):
    target: TargetRole
    steps: list[PlanStep]
    created_week: int = Field(ge=0)
    supersedes: Optional[str] = None  # title of the target we abandoned, if any


# --------------------------------------------------------------------------
# Phase 3 — the world, which does not sit still
# --------------------------------------------------------------------------


class MarketSnapshot(BaseModel):
    """One week of the job market. R4 generates a series of these.

    Passed around as a value, never re-fetched: the snapshot in CaseState is
    the market for that week, so the planner and the router are looking at the
    same numbers the timeline will later quote.
    """

    week: int = Field(ge=0)
    postings_by_role: dict[str, int]
    skills_in_demand: dict[str, float]  # skill -> share of postings requiring it


# --------------------------------------------------------------------------
# Phase 4 — applying, and what comes back
# --------------------------------------------------------------------------


class Stage(str, Enum):
    """How far an application got. The pattern across these is the signal.

    DECLARATION ORDER IS THE CONTRACT: SCREENING is earliest, OFFER is last.

    The operators below exist because a plain str-mixin enum compares by
    spelling, so `Stage.OFFER > Stage.SCREENING` is False — "offer" loses to
    "screening" on the first letter. That reads as correct and silently is not,
    which is the worst kind of wrong for R1 tuning thresholds. With these,
    `>=` means "got at least this far", which is what anyone would assume.
    """

    SCREENING = "screening"
    RECRUITER = "recruiter"
    TECHNICAL = "technical"
    FINAL = "final"
    OFFER = "offer"

    @property
    def rank(self) -> int:
        """Position in the funnel. 0 is earliest. Derived from declaration
        order, so inserting a stage above only means putting it in the right
        place — there is no second list to keep in sync."""
        return list(type(self)).index(self)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Stage):
            return NotImplemented
        return self.rank < other.rank

    def __le__(self, other: object) -> bool:
        if not isinstance(other, Stage):
            return NotImplemented
        return self.rank <= other.rank

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, Stage):
            return NotImplemented
        return self.rank > other.rank

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, Stage):
            return NotImplemented
        return self.rank >= other.rank


class ApplicationOutcome(BaseModel):
    week: int = Field(ge=0)
    role_title: str
    stage_reached: Stage
    rejected: bool
    notes: str = ""


# --------------------------------------------------------------------------
# The event log — what the demo timeline renders
# --------------------------------------------------------------------------


class Event(BaseModel):
    """One thing the agent did or noticed, with the reason.

    R5 renders these as the timeline. If an adaptation is not in here with a
    `because`, the judges will not see it happen.
    """

    week: int = Field(ge=0)
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
    # Set every week by advance_week, and seeded for week 0 by run_demo. This
    # is the market: nodes read it rather than calling clock.snapshot again,
    # so the router, the planner and the timeline cannot disagree about what
    # the week looked like.
    market: Optional[MarketSnapshot]

    applications: Annotated[list[ApplicationOutcome], operator.add]
    events: Annotated[list[Event], operator.add]

    positioning: str  # how we currently describe them to employers

    # Whether the positioning has been rewritten once already. A FLAG, not a
    # thing to infer from the text: placement.translate returns prose on Day 2,
    # and any rule that sniffs it ("does it start with 'revised'?") stops being
    # true the moment the stub is replaced — silently, with no offer at the end.
    repositioned: bool

    # Rejections before this week are stale — a reposition resets the window.
    # The `applications` reducer only appends, so we move a pointer instead.
    signal_from_week: int

    done: bool
    outcome: str  # "placed" | "ran_out_of_runway" | ""

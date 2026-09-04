"""Placement. Owner: R3.

Translate their history into the target field's vocabulary, then apply.
Rejections come back as ApplicationOutcome and feed signals/rejection.py —
that feedback is what makes placement part of the loop rather than a job board
bolted on the end.

Two jobs:
  translate()  write how we describe this person to an employer in the TARGET
               role's language, using only the evidence lines we actually hold
  apply()      send a batch out and judge, honestly, how far each one gets

WHY apply() SCREENS RATHER THAN SUBMITS
---------------------------------------
Nothing here touches a real job board. The model plays the employer side: it
reads the positioning the way a recruiter screening a career-changer would, and
says where each application stops and why. That is what turns a rejection into
a SIGNAL — rejection.diagnose reads the pattern across the batch and the graph
routes on it. Actual submission stays human-gated and is out of scope for the
hackathon; see NEVER AUTO-SUBMIT below.
"""

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from .._common import structured
from ..contracts import ApplicationOutcome, Plan, SkillInventory, Stage
from ..signals.rejection import MIN_SIGNAL

# One batch = one week of applying. Sized to MIN_SIGNAL because a batch smaller
# than the signal threshold can never produce a diagnosable pattern — apply()
# would generate rejections that rejection.diagnose is structurally unable to
# read, and the reposition edge would never fire. The two constants are a
# contract, not a coincidence: import rather than restate.
BATCH = MIN_SIGNAL


# --------------------------------------------------------------------------
# translate — how we describe them
# --------------------------------------------------------------------------


class _Positioning(BaseModel):
    """Transient container. translate() returns prose, but asking for the parts
    separately is what stops the model handing back a paragraph of adjectives:
    every proof point has to be pinned to an evidence line it was given."""

    headline: str = Field(description="One line, the way they should be introduced")
    summary: str = Field(description="Two to four sentences, first person avoided")
    proof_points: list[str] = Field(
        description="Concrete achievements, each traceable to an evidence line"
    )

    def render(self) -> str:
        bullets = "\n".join(f"- {p}" for p in self.proof_points)
        return f"{self.headline}\n\n{self.summary}\n\n{bullets}".strip()


TRANSLATE_SYSTEM = """You are writing how a career-changer is presented to employers.

The person is moving INTO the target role from a different field. Your job is to
describe what they can already do in the vocabulary of the target role, so a
reader who has never worked in their old industry understands the value.

Rules:
- Use ONLY the capabilities and evidence lines given. Every proof point must
  trace back to one of them. Do not invent employers, tools, numbers or years.
- Translate, do not inflate. "Monthly stock variance reconciliation across four
  warehouses" becomes recurring data reconciliation over multiple sources -- it
  does NOT become "data engineering at scale".
- Lead with what transfers. Their old job title is the least interesting fact
  about them and should not be the headline.
- Name the retraining honestly if it is in flight. A plan in progress is a
  reason to talk to them, not something to hide."""

REPOSITION_NOTE = """

THIS IS THE SECOND ATTEMPT. The previous framing was rejected at resume
screening every single time, which means it did not read as a candidate for
this role at all -- most likely it was still written in the old field's
vocabulary, or it led with the career change instead of the capability.

Do not paraphrase the previous framing. Change what is in front:
- open on the target role's own terms, not on the transition
- put the target role's required skills in the first two lines, where a
  ten-second screen actually looks
- keep every proof point tied to real evidence -- fixing the framing is not a
  licence to start claiming things."""


def translate(
    inventory: SkillInventory, plan: Plan, repositioned: bool = False
) -> str:
    """How we describe this person for plan.target, in that role's language.

    `repositioned` says this is the SECOND framing -- the first died at
    screening -- so the prompt is TOLD that, rather than producing the same
    text again and hoping for a different result.
    """
    llm = structured(_Positioning, temperature=0.3)

    capabilities = "\n".join(
        f"  - {c.skill} (evidence: {c.evidence})" for c in inventory.capabilities
    )
    # What they are actively closing. Worth stating: mid-training is a fact
    # about the candidate, and hiding it is what makes a career-change resume
    # read as evasive.
    in_progress = "\n".join(
        f"  - {s.description} (closes: {s.closes_gap})" for s in plan.steps
    )

    system = TRANSLATE_SYSTEM + (REPOSITION_NOTE if repositioned else "")
    draft = llm.invoke(
        [
            SystemMessage(content=system),
            HumanMessage(
                content=(
                    f"Target role: {plan.target.title}\n"
                    f"Why this role: {plan.target.rationale}\n"
                    f"Still missing: {plan.target.missing_skills}\n\n"
                    f"What they can already do:\n{capabilities}\n\n"
                    f"Retraining under way:\n{in_progress}"
                )
            ),
        ]
    )
    return draft.render()


# --------------------------------------------------------------------------
# apply — and what comes back
# --------------------------------------------------------------------------


class _Screen(BaseModel):
    """One application, judged from the employer's side."""

    employer_context: str = Field(
        description="One line on the kind of employer and posting this was"
    )
    stage_reached: Stage = Field(
        description="How far this application got before it stopped"
    )
    notes: str = Field(
        description="Why it stopped there, in one sentence, specific to this framing"
    )


class _ScreenBatch(BaseModel):
    results: list[_Screen]


SCREEN_SYSTEM = f"""You are a hiring screener reading applications for one role.

You are given the role, the skills the applicant has NOT yet evidenced, and the
exact positioning text they applied with. Judge each application the way a real
screener does -- on what is in front of you, in the time a real screen takes.

For each application, say how far it got:
- screening  -- did not pass the resume screen. This is where a career-changer
                lands when the text does not read, in the first few lines, as a
                candidate for THIS role: wrong vocabulary, the required skills
                absent or buried, or the career change leading instead of the
                capability.
- recruiter  -- passed the screen, lost it in the first conversation
- technical  -- passed the screen, then the skills gap showed under questioning
- final      -- got to the end and lost to another candidate
- offer      -- hired

Be strict and be realistic, but judge what is actually in front of you. Weigh
the training they have COMPLETED as real evidence -- a gap that has been closed
is no longer a gap, and holding someone's starting point against them after
they have closed it is not strictness, it is not reading the application. Only
the skills still listed as outstanding are still missing.

Do not be kind about a genuinely weak application: a screen this person passes
only because you were generous is a rejection they receive later, after they
have spent months on it.

Return exactly {{n}} results, each for a plausibly different employer, and make
the notes specific to THIS positioning text -- name what in it did or did not
land. Do not write the same note {{n}} times."""

FIRST_PASS_NOTE = """

This is their first framing, written before any employer had seen it. A
career-changer's opening resume usually does stop at screening, because it is
still written in the old field's vocabulary. Expect most of this batch to stop
there."""

REAPPLY_NOTE = """

This applicant applied before with a weaker framing and was screened out every
time. The positioning below is the REWRITE, and they have more training behind
them now than they did then. Judge it fresh, not against their earlier attempt.

If the rewrite puts the role's required skills up front in the role's own
language and backs them with concrete evidence, it passes the resume screen --
that is what the screen is for, and there is no reason to fail it twice for a
problem that has been fixed. From there, judge each application on its merits:
across a batch of {n}, expect a spread, and an applicant who has closed the
gaps and can evidence them is a genuine hire. At least one of these should go
well beyond screening, and a strong one ends in an offer."""


def apply(
    plan: Plan, week: int, positioning: str, repositioned: bool = False
) -> list[ApplicationOutcome]:
    """Send a week's batch and judge how far each one got.

    NEVER AUTO-SUBMIT. Nothing here posts to a real job board; the model plays
    the employer side so the loop has feedback to route on. If this is ever
    wired to real postings, submission goes behind an explicit human gate --
    that is a product commitment, not a TODO.
    """
    llm = structured(_ScreenBatch, temperature=0.4)

    system = (
        SCREEN_SYSTEM + (REAPPLY_NOTE if repositioned else FIRST_PASS_NOTE)
    ).replace("{n}", str(BATCH))

    # target.missing_skills is the gap list from the week the target was CHOSEN
    # and is never updated, so quoting it directly told the screener at week 22
    # that the candidate still could not do things they finished in week 6 --
    # and the screener, correctly, rejected the unqualified applicant it had
    # been described. The plan's own schedule is the honest record of where
    # they are now: a step whose week has passed is training they have done,
    # which is the same rule graph._training_completed applies to the inventory.
    done = [s.closes_gap for s in plan.steps if s.week <= week]
    outstanding = [s.closes_gap for s in plan.steps if s.week > week]

    batch = llm.invoke(
        [
            SystemMessage(content=system),
            HumanMessage(
                content=(
                    f"Role applied for: {plan.target.title}\n"
                    f"Training completed and evidenced: {done or 'none yet'}\n"
                    f"Still outstanding: {outstanding or 'nothing — training complete'}\n"
                    f"Week {week} of a {plan.target.months_to_ready}-month retraining plan.\n\n"
                    f"They applied with this positioning:\n---\n{positioning}\n---"
                )
            ),
        ]
    )

    results = (batch.results or [])[:BATCH]
    while len(results) < BATCH:
        # Guard: the graph reads the SHAPE of the batch, so a short batch is a
        # silent routing bug rather than a cosmetic one -- fewer than MIN_SIGNAL
        # rejections is a pattern rejection.diagnose cannot see, and the person
        # keeps applying with a framing we already know is failing.
        results.append(
            _Screen(
                employer_context="unspecified employer",
                stage_reached=Stage.SCREENING,
                notes="no response",
            )
        )

    return [
        ApplicationOutcome(
            week=week,
            role_title=plan.target.title,
            # rejected is DERIVED, never taken from the model. The graph treats
            # any not-rejected outcome as an offer (graph.apply_step), so a
            # model that marks a live-but-unfinished application as "not
            # rejected" would end the run with a placement that never happened.
            # An offer is the only outcome that is not a rejection.
            stage_reached=r.stage_reached,
            rejected=r.stage_reached != Stage.OFFER,
            notes=f"{r.employer_context}: {r.notes}",
        )
        for r in results
    ]

"""Placement. Owner: R3.

Translate their history into the target field's vocabulary, then apply.
Rejections come back as ApplicationOutcome and feed signals/rejection.py —
that feedback is what makes placement part of the loop rather than a job board
bolted on the end.

STUB — replace with real model calls. Keep the signatures.
"""

from ..contracts import ApplicationOutcome, Plan, SkillInventory, Stage


def translate(
    inventory: SkillInventory, plan: Plan, repositioned: bool = False
) -> str:
    # TODO(R3): rewrite their experience in the target role's language, using
    # the evidence lines from the inventory.
    #
    # `repositioned` says this is the SECOND framing — the first one died at
    # screening — so the prompt should be told that rather than producing the
    # same text again and hoping for a different result.
    if repositioned:
        return f"stub positioning for {plan.target.title}, rewritten after screening rejections"
    return f"stub positioning for {plan.target.title}"


def apply(
    plan: Plan, week: int, positioning: str, repositioned: bool = False
) -> list[ApplicationOutcome]:
    # TODO(R3): match against market postings, tailor per posting, then submit
    # — human-gated. Never auto-submit.
    #
    # The stub fails everything at SCREENING so the rejection signal fires,
    # then succeeds once the positioning has been rewritten. That is what
    # makes the second adaptation event visible in the demo.
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

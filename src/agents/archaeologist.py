"""Skills archaeology. Owner: R3.

Not 'what was your job title'. What can this person ACTUALLY do, and what line
of their history proves it.

STUB — replace the body with a real model call. Keep the signature.
"""

from ..contracts import CandidateProfile, Capability, SkillInventory


def extract(candidate: CandidateProfile) -> SkillInventory:
    # TODO(R3): prompt the model with candidate.history and ask for
    # capabilities + the evidence line for each. Structured output via pydantic.
    return SkillInventory(
        capabilities=[
            Capability("vendor contract management", "stub: managed 3PL SLAs"),
            Capability("data reconciliation", "stub: monthly stock variance"),
            Capability("stakeholder escalation", "stub: ran carrier disputes"),
        ]
    )

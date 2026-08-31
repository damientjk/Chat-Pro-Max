"""Skills archaeology. Owner: R3.

Not 'what was your job title'. What can this person ACTUALLY do, and what line
of their history proves it.

STUB — replace the body with a real model call. Keep the signature.
"""

from ..contracts import CandidateProfile, Capability, SkillInventory


def extract(candidate: CandidateProfile) -> SkillInventory:
    # TODO(R3): prompt the model with candidate.history and ask for
    # capabilities + the evidence line for each. Structured output via
    # llm.with_structured_output(SkillInventory) — that is why the shapes in
    # contracts.py are pydantic models.
    return SkillInventory(
        capabilities=[
            Capability(skill="vendor contract management", evidence="stub: managed 3PL SLAs"),
            Capability(skill="data reconciliation", evidence="stub: monthly stock variance"),
            Capability(skill="stakeholder escalation", evidence="stub: ran carrier disputes"),
        ]
    )

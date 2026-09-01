"""Skills archaeology. Owner: R3.

Not 'what was your job title'. What can this person ACTUALLY do, and what line
of their history proves it.

The model reads the free-text history and returns capabilities WITH an evidence
line for each -- we never claim a skill we cannot point at. Structured output
means the model fills contracts.SkillInventory directly, and pydantic rejects a
malformed answer before it can reach the plan.
"""

from langchain_core.messages import HumanMessage, SystemMessage

from .._common import chat_model
from ..contracts import CandidateProfile, SkillInventory

SYSTEM = """You are a skills archaeologist for a career-transition service.

Given a person's work history, extract the concrete, transferable CAPABILITIES
they can already demonstrate -- the underlying skills, not their job titles.
A job title hides capability; dig it out. "Managed carrier SLAs" is evidence of
vendor and contract management and of negotiating under pressure, not a title.

Rules:
- For every capability, quote the exact phrase from their history that proves
  it in the evidence field. If nothing in the text supports a capability, do
  NOT list it. Never invent evidence.
- Prefer capabilities that transfer to adjacent roles over narrow, employer-
  specific tasks.
- Three to six capabilities is usually right. Quality over quantity."""


def extract(candidate: CandidateProfile) -> SkillInventory:
    llm = chat_model().with_structured_output(SkillInventory)
    return llm.invoke(
        [
            SystemMessage(content=SYSTEM),
            HumanMessage(
                content=(
                    f"Name: {candidate.name}\n"
                    f"Last role: {candidate.last_role} in {candidate.last_industry}\n"
                    f"Years of experience: {candidate.years_experience}\n\n"
                    f"History (their own words):\n{candidate.history}"
                )
            ),
        ]
    )

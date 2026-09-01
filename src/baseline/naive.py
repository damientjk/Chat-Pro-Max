"""A one-shot recommender used to compare against the adaptive agent.

This module intentionally does not know about market drift, application
outcomes, or re-planning. R2 will later pass in the shared contract objects.
"""

from dataclasses import dataclass
from typing import Iterable, Protocol


class HasSkills(Protocol):
    skills: list[str]


class HasRoleDetails(Protocol):
    id: str
    title: str
    required_skills: list[str]


@dataclass(frozen=True)
class BaselineRecommendation:
    """The baseline's single decision for one candidate."""

    target_role_id: str
    target_role_title: str
    matched_skills: int
    missing_skills: int
    rationale: str
    replans: int = 0


def recommend_once(
    skills: HasSkills, target_roles: Iterable[HasRoleDetails]
) -> BaselineRecommendation:
    """Choose the role with the strongest current skills match.

    The function runs once only. Its output is intentionally immutable and
    always has ``replans == 0`` so it is a fair comparator for the real agent.
    """
    roles = list(target_roles)
    if not roles:
        raise ValueError("At least one target role is required.")

    candidate_skills = {skill.strip().lower() for skill in skills.skills}

    def score(role: HasRoleDetails) -> tuple[int, int]:
        required = {skill.strip().lower() for skill in role.required_skills}
        matched = len(candidate_skills & required)
        missing = len(required - candidate_skills)
        return matched, -missing

    selected = max(roles, key=score)
    matched, negative_missing = score(selected)

    return BaselineRecommendation(
        target_role_id=selected.id,
        target_role_title=selected.title,
        matched_skills=matched,
        missing_skills=-negative_missing,
        rationale=(
            "Selected once using current skills only: "
            f"{matched} matching and {-negative_missing} missing skills."
        ),
    )

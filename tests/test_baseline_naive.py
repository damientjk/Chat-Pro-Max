from dataclasses import dataclass
import unittest

from src.baseline.naive import recommend_once


@dataclass
class Skills:
    skills: list[str]


@dataclass
class Role:
    id: str
    title: str
    required_skills: list[str]


class BaselineRecommendationTests(unittest.TestCase):
    def test_baseline_selects_best_current_fit(self) -> None:
        skills = Skills(skills=["Excel", "Customer service", "Scheduling"])
        roles = [
            Role("data", "Data Analyst", ["SQL", "Python", "Excel"]),
            Role(
                "operations",
                "Operations Coordinator",
                ["Excel", "Customer service", "Scheduling"],
            ),
        ]

        recommendation = recommend_once(skills, roles)

        self.assertEqual(recommendation.target_role_id, "operations")
        self.assertEqual(recommendation.matched_skills, 3)
        self.assertEqual(recommendation.missing_skills, 0)
        self.assertEqual(recommendation.replans, 0)

    def test_baseline_requires_a_role(self) -> None:
        with self.assertRaisesRegex(ValueError, "At least one target role is required."):
            recommend_once(Skills(skills=["Excel"]), [])

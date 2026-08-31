"""Seeded candidates with known-good answers. Owner: R4.

Six personas, each with the target role we believe is correct. That ground
truth is what lets us score both the agent and the baseline.
"""

from ..contracts import CandidateProfile

DEMO = CandidateProfile(
    name="Wei Ming",
    age=45,
    years_experience=19,
    last_role="Operations Executive",
    last_industry="Third-party logistics",
    history=(
        "Ran inbound scheduling for a 3PL. Managed carrier SLAs and monthly "
        "stock variance reconciliation across four warehouses. Built the "
        "spreadsheet the ops team still uses. Retrenched in the July cuts."
    ),
    constraints="Needs income within 6 months. Cannot relocate.",
)

# TODO(R4): five more, each with an expected target role for scoring.
ALL = [DEMO]
EXPECTED_TARGET = {"Wei Ming": "Supply Chain Data Analyst"}

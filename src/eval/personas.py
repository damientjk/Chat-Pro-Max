"""Seeded candidates with known-good answers. Owner: R4.

Six personas, each with the target role we believe is correct. That ground
truth is what lets us score both the agent and the baseline.

Each history is written with the specific evidence lines the archaeologist
needs to work from (a real employer detail, a number, a system name) — a
vague history produces a vague inventory, and a vague inventory makes both
the targeting and the eval score meaningless.

Target roles here line up with market.clock's _ROLE_BASELINES so each
persona has a real, currently-hiring destination in week 0 — except DEMO,
whose whole point is that its destination stops hiring at DRIFT_WEEK.
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

FARAH = CandidateProfile(
    name="Farah Yusof",
    age=43,
    years_experience=15,
    last_role="Customer Support Team Lead",
    last_industry="Telecom",
    history=(
        "Led a team of eight handling escalations for a telco's retail "
        "customers. Owned the CRM's ticket-routing rules and built the "
        "weekly SLA-breach report the call centre manager reads. Role made "
        "redundant after the support function was outsourced."
    ),
    constraints="Needs income within 4 months. Prefers hybrid.",
)

NURUL = CandidateProfile(
    name="Nurul Huda",
    age=38,
    years_experience=9,
    last_role="Junior Analyst",
    last_industry="Insurance",
    history=(
        "Pulled claims data into Excel for the underwriting team and wrote "
        "the monthly loss-ratio report. Picked up basic SQL to query the "
        "claims warehouse directly after the reporting backlog got too "
        "long. Team was outsourced to a shared-services centre."
    ),
    constraints="Available 10 hours/week for retraining.",
)

RAJESH = CandidateProfile(
    name="Rajesh Kumar",
    age=52,
    years_experience=22,
    last_role="Administrative Executive",
    last_industry="Manufacturing",
    history=(
        "Coordinated vendor onboarding and purchase orders for a factory's "
        "procurement office. Scheduled cross-department reviews and kept "
        "the compliance document tracker that audit relies on every "
        "quarter. Position cut when the plant consolidated admin functions."
    ),
    constraints="Needs income within 6 months. Cannot relocate.",
)

TAN = CandidateProfile(
    name="Tan Wei Ling",
    age=49,
    years_experience=17,
    last_role="Manufacturing Technician",
    last_industry="Electronics",
    history=(
        "Ran incoming-quality inspection on an SMT line and logged defect "
        "codes against the plant's process-control charts. Trained new "
        "hires on the inspection checklist. Line was moved overseas."
    ),
    constraints="Available 8 hours/week for retraining.",
)

BALA = CandidateProfile(
    name="Bala Subramaniam",
    age=55,
    years_experience=24,
    last_role="Office Manager",
    last_industry="Professional Services",
    history=(
        "Managed scheduling and onboarding paperwork for a 60-person "
        "consultancy, including the HRIS records the payroll vendor pulls "
        "from each month. Coordinated new-hire orientation end to end. "
        "Role folded when the firm merged its Singapore and KL offices."
    ),
    constraints="Needs income within 6 months. Cannot relocate.",
)

ALL = [DEMO, FARAH, NURUL, RAJESH, TAN, BALA]

EXPECTED_TARGET = {
    "Wei Ming": "Supply Chain Data Analyst",
    "Farah Yusof": "Customer Success Coordinator",
    "Nurul Huda": "Junior Data Analyst",
    "Rajesh Kumar": "Project Coordinator",
    "Tan Wei Ling": "QA / Process Analyst",
    "Bala Subramaniam": "HR Coordinator",
}

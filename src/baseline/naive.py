"""One-shot recommender. Owner: R1.

Same inputs as the real agent. Picks once. Never re-plans. Never notices.

TODO(R1): run this to week 26 and record how many personas end on a target
that had closed by DRIFT_WEEK.
"""

from ..agents import archaeologist, planner
from ..contracts import CandidateProfile, Plan


def run(candidate: CandidateProfile) -> Plan:
    inventory = archaeologist.extract(candidate)
    chosen = planner.target(inventory, week=0)
    return planner.plan(chosen, week=0)

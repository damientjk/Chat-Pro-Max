"""One-shot recommender. Owner: R1.

Same inputs as the real agent. Picks once. Never re-plans. Never notices.

TODO(R1): run this to week 26 and record how many personas end on a target
that had closed by DRIFT_WEEK.
"""

from ..agents import archaeologist, planner
from ..contracts import CandidateProfile, Plan
from ..market import clock


def run(candidate: CandidateProfile) -> Plan:
    inventory = archaeologist.extract(candidate)
    # Week 0's market and never another one. That is the whole point of the
    # baseline: it sees the market once, at the start, and never looks again.
    chosen = planner.target(inventory, clock.snapshot(0), week=0)
    return planner.plan(chosen, week=0)

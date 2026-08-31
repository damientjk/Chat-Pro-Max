"""Benefit metrics. Owner: R1.

The number the benefits slide lives on. Computed, not asserted.

TODO(R1): months saved, wasted training spend avoided, dead paths caught.
Run agent vs baseline across all six personas and record the comparison.
"""

from ..contracts import CaseState


def summarise(state: CaseState) -> dict:
    return {
        "weeks_elapsed": state.get("week", 0),
        "applications": len(state.get("applications", [])),
        "adaptations": len(
            [e for e in state.get("events", []) if e.kind in ("replan", "reposition")]
        ),
        "outcome": state.get("outcome", ""),
    }

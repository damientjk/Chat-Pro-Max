"""Render the event log as a timeline. Owner: R5.

Terminal version below so the demo works from day one. TODO(R5): the visual
version. If an adaptation is not visible on screen with its reason, the judges
did not see it happen.
"""

from ..contracts import Event

MARK = {
    "drift": "!!",
    "replan": "->",
    "reposition": "->",
    "offer": "**",
}


def render(events: list[Event]) -> str:
    lines = []
    for e in events:
        mark = MARK.get(e.kind, "  ")
        lines.append(f"  wk {e.week:>2}  {mark}  {e.summary}")
        if e.because:
            lines.append(f"            because {e.because}")
    return "\n".join(lines)

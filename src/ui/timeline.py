from ..contracts import Event


MARK = {
    "intake": "INTAKE",
    "target": "TARGET",
    "plan": "PLAN",
    "drift": "DRIFT",
    "replan": "REPLAN",
    "reposition": "REPOSITION",
    "apply": "APPLICATION",
    "offer": "OFFER",
}

ADAPTATION_EVENTS = {"drift", "replan", "reposition"}


def render(events: list[Event]) -> str:
    """Render the candidate's journey as a readable timeline."""

    if not events:
        return "No timeline events recorded."

    lines = [
        "SIX-MONTH ADAPTATION TIMELINE",
        "-----------------------------",
    ]

    for event in sorted(events, key=lambda item: item.week):
        mark = MARK.get(event.kind, event.kind.upper())

        lines.append(
            f"Week {event.week:>2} | {mark:<11} | {event.summary}"
        )

        if event.because:
            lines.append(f"        Reason: {event.because}")
        elif event.kind in ADAPTATION_EVENTS:
            lines.append("        Reason: not recorded")

    return "\n".join(lines)
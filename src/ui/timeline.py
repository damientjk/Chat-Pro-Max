from ..contracts import Event, SkillInventory, TargetRole


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

def calculate_readiness(
    inventory: SkillInventory,
    target: TargetRole | None,
) -> float:
    """Return the share of the target's skill gaps now completed."""

    if target is None:
        return 0.0

    missing = {
        skill.strip().casefold()
        for skill in target.missing_skills
    }

    if not missing:
        return 1.0

    acquired = {
        skill.strip().casefold()
        for skill in inventory.names()
    }

    completed = missing & acquired
    return len(completed) / len(missing)


def render_readiness(
    inventory: SkillInventory,
    target: TargetRole | None,
    width: int = 20,
) -> str:
    """Render readiness separately from recommendation confidence."""

    if target is None:
        return "Readiness: no target selected"

    score = calculate_readiness(inventory, target)
    filled = round(score * width)
    bar = "#" * filled + "-" * (width - filled)

    return "\n".join(
        [
            f"Readiness [{bar}] {score:.0%}",
            f"Estimated time to ready: {target.months_to_ready} months",
        ]
    )

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
"""Live web timeline. Owner: R5.

    uv run python -m src.ui.web                 # live run, real model calls
    uv run python -m src.ui.web --offline       # real graph, stub agents, no key
    uv run python -m src.ui.web --replay        # replay the last run, no key
    uv run python -m src.ui.web --replay F.json # replay a specific saved run
    uv run python -m src.ui.web --replay --pace 0.5   # replay at half the gaps

--offline records to .offline_run.json, never over the live .last_run.json:
stub output must never be the thing that gets filmed by mistake.

The page has play/pause, step and a scrubber. Space toggles play, arrow keys
step. There is deliberately NO speed control: the pace comes from the run
itself. Every frame carries the time it landed, so a replay reproduces the real
gaps -- a twelve-second model call is a real pause with the agent named, an
instant week-tick flicks past. A dropdown offering "2x" made no sense during a
live run, where the pace is whatever the model takes.

The terminal renderer in timeline.py stays the source of truth for what an
event MEANS. This serves the same event log to a browser so the six months can
be watched as a shape -- postings collapsing, readiness resetting on the pivot
-- rather than read as a wall of text.

WHAT THE PAGE IS TOLD, AND WHY
------------------------------
The frame is the whole contract with the browser. Beyond the case state it
carries three things that exist only to make the run legible:

  t       when this frame landed, so a replay can reproduce the waiting
  calls   the model calls the node made, from ui/activity.py -- which agent,
          what it was doing, how long it took, what it decided
  plan    the actual training steps. They were in CaseState from Day 1 and had
          never reached the browser, so the plan read as "4-step plan to X"

WHY STDLIB ONLY
---------------
No FastAPI, no uvicorn, no CDN. `http.server` with a Server-Sent Events
response does the whole job, so nothing enters pyproject.toml, requirements.txt
is unchanged, and Day 5's fresh-clone gate cannot fail because of this file. A
demo aid is not worth a dependency on the submission path.

LIVE AND REPLAY ARE BOTH FIRST-CLASS
------------------------------------
Either may be what the judges see, so neither is a fallback for the other. Live
renders each frame as it lands and drives the working indicator from real-time
activity messages; replay plays back on the recorded gaps and drives the same
indicator from each frame's recorded calls. Every live run still saves itself
to .last_run.json, because a live run makes ~9 model calls, takes minutes, and
on Groq's free tier can be rate-limited mid-take -- so get one good live run,
and film the replay as many times as you like.
"""

from __future__ import annotations

import json
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from queue import Empty, Queue

from ..contracts import CaseState
from ..market import clock
from .timeline import calculate_readiness

RECORDING = Path(__file__).resolve().parents[2] / ".last_run.json"
# Stub runs are kept apart from the real one — see work() below.
OFFLINE_RECORDING = Path(__file__).resolve().parents[2] / ".offline_run.json"
PAGE_FILE = Path(__file__).resolve().parent / "page.html"
PORT = 8000


# --------------------------------------------------------------------------
# Turning graph state into something a browser can draw
# --------------------------------------------------------------------------


def _plan_json(state: CaseState) -> dict | None:
    """The training plan, for the browser.

    The Plan has been in CaseState since Day 1 and had never left it: the page
    showed "4-step plan to Supply Chain Data Analyst" and nothing about what
    the four steps were. `supersedes` is included because it is the field that
    makes a re-plan read as carrying work forward rather than starting over.
    """
    plan = state.get("plan")
    if not plan:
        return None
    return {
        "created_week": plan.created_week,
        "supersedes": plan.supersedes,
        "steps": [s.model_dump() for s in plan.steps],
    }


def _frame(state: CaseState, node: str, *, t: float, calls: list[dict]) -> dict:
    """One update: everything the page needs to redraw, as plain JSON.

    The whole state is sent each time rather than a diff. Twenty-six weeks of
    small payloads costs nothing, and a client that can rebuild itself from any
    single frame survives a refresh mid-run -- which matters when the thing is
    being filmed.
    """
    target = state.get("target")
    market = state.get("market")
    inventory = state.get("inventory")

    return {
        "kind": "frame",
        "week": state.get("week", 0),
        "horizon": clock.HORIZON_WEEKS,
        "node": node,
        # Seconds since the run began. This is what lets a replay reproduce the
        # real pauses instead of evening every step out to a fixed tick, which
        # is what made the model calls invisible.
        "t": round(t, 3),
        # The model calls the node that produced this frame made, if any.
        "calls": calls,
        "target": target.title if target else None,
        "rationale": target.rationale if target else "",
        "months_to_ready": target.months_to_ready if target else None,
        "confidence": target.confidence if target else None,
        "readiness": (
            calculate_readiness(inventory, target) if inventory and target else 0.0
        ),
        # Postings for the role we are actually training toward. This is the
        # number the drift edge tests, so it is the one worth plotting.
        "postings": (
            market.postings_by_role.get(target.title, 0) if market and target else None
        ),
        "market": market.postings_by_role if market else {},
        "plan": _plan_json(state),
        "events": [e.model_dump() for e in state.get("events", [])],
        "applications": len(state.get("applications", [])),
        "outcome": state.get("outcome", ""),
        "done": bool(state.get("done")),
    }


def run_case(emit, offline: bool = False) -> None:
    """Drive the real graph, calling emit(message) as the case progresses.

    Two kinds of message go out. `frame` is the case state after a node; the
    page redraws from it. `activity` is a model call starting or finishing, and
    exists so a LIVE viewer sees which agent is busy the moment it becomes
    busy, rather than staring at a page that has not changed for twelve
    seconds. A replay ignores activity messages and uses each frame's recorded
    `calls` instead, so the indicator stays in step with whatever the viewer
    has scrubbed to.
    """
    from ..graph import build, memory_checkpointer
    from ..run_demo import initial_state
    from . import activity

    if offline:
        # Development only: the real graph, the real routing, stub agents.
        from scripts.preview_ui import install_doubles

        install_doubles()

    started = time.monotonic()
    # Calls finish inside a node, before that node's frame exists. They are
    # collected here and drained onto the next frame, so a scrubbed-back
    # viewer sees the calls attributed to the step they actually produced.
    pending: list[dict] = []
    # The week a call happened in is the week of the last frame: a node runs on
    # the state as it stood before it, which is exactly what that frame holds.
    seen = {"week": 0}

    def on_activity(record: dict) -> None:
        record = {**record, "week": seen["week"]}
        emit({"kind": "activity", **record})
        if record.get("phase") == "end":
            pending.append(record)

    activity.instrument(on_activity)

    app = build(checkpointer=memory_checkpointer())
    config = {
        "recursion_limit": 200,
        "configurable": {"thread_id": "web"},
    }

    # ORDER MATTERS: for each step LangGraph yields the "updates" chunk (which
    # names the node) BEFORE the "values" chunk holding that node's result. So
    # the node name is remembered and the frame is emitted on the values that
    # follow it — otherwise every frame shows the state from one node earlier
    # and the pivot appears a step late on screen.
    latest: dict = {}
    node = "start"
    for mode, chunk in app.stream(
        initial_state(), config=config, stream_mode=["values", "updates"]
    ):
        if mode == "updates":
            for name in chunk:
                node = name
        else:
            latest = chunk
            calls, pending[:] = list(pending), []
            emit(_frame(latest, node, t=time.monotonic() - started, calls=calls))
            seen["week"] = latest.get("week", 0)

    emit({
        **_frame(latest, "end", t=time.monotonic() - started, calls=list(pending)),
        "finished": True,
    })


# --------------------------------------------------------------------------
# Fan-out: one running case, any number of browser tabs
# --------------------------------------------------------------------------


class Broadcast:
    """Frames go to every connected tab, and new tabs get the backlog.

    Without the backlog, opening the page halfway through a run shows an empty
    timeline until the next node lands -- which, during a six-week stretch of
    advance_week, can be a long and confusing wait on camera.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._clients: list[Queue] = []
        self._history: list[dict] = []

    def subscribe(self) -> Queue:
        q: Queue = Queue()
        with self._lock:
            for frame in self._history:
                q.put(frame)
            self._clients.append(q)
        return q

    def unsubscribe(self, q: Queue) -> None:
        with self._lock:
            if q in self._clients:
                self._clients.remove(q)

    def publish(self, frame: dict) -> None:
        with self._lock:
            self._history.append(frame)
            targets = list(self._clients)
        for q in targets:
            q.put(frame)

    @property
    def history(self) -> list[dict]:
        with self._lock:
            return list(self._history)


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------


def make_handler(bus: Broadcast, config: dict):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args) -> None:
            pass  # the terminal is showing the run; access logs only clutter it

        def do_GET(self) -> None:
            if self.path.startswith("/events"):
                self._sse()
            else:
                body = _render_page(config).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        def _sse(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()

            q = bus.subscribe()
            try:
                while True:
                    try:
                        frame = q.get(timeout=15)
                    except Empty:
                        # A comment line keeps proxies and the browser from
                        # dropping an idle stream during a quiet stretch.
                        self.wfile.write(b": keep-alive\n\n")
                        self.wfile.flush()
                        continue
                    payload = json.dumps(frame).encode("utf-8")
                    self.wfile.write(b"data: " + payload + b"\n\n")
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass  # tab closed
            finally:
                bus.unsubscribe(q)

    return Handler


# --------------------------------------------------------------------------
# The page
# --------------------------------------------------------------------------


def _render_page(config: dict) -> str:
    """page.html, with one config block injected ahead of its own script.

    The page used to live here as a 300-line raw string. It is HTML, CSS and
    JavaScript, and inside a Python string it gets no highlighting and no
    bracket matching -- a CSS typo in it survived review and only showed up
    when the thing was rendered. It is a real file now, read fresh on every
    request so a reload picks up an edit without restarting the server.

    Everything the page needs to know about HOW it is being run -- live or
    replay, the pacing multiplier, the viability floor -- arrives in one JSON
    blob rather than as string substitutions, which is what __INTERVAL_MS__
    used to be.
    """
    blob = json.dumps(config)
    return PAGE_FILE.read_text(encoding="utf-8").replace(
        "<script>\n\"use strict\";",
        f"<script>window.CONFIG = {blob};</script>\n<script>\n\"use strict\";",
        1,
    )


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------


def _replay(bus: Broadcast, path: Path) -> None:
    """Push the recording out quickly — the browser decides the pace.

    Pacing here would fight the page's own controls: you could not scrub back
    to a frame the server had not sent yet, and pausing would only stall the
    render while the buffer kept filling. So the server delivers, the client
    plays. The small delay is just politeness to the socket.

    Frames from before the `kind` tag are stamped on the way past, so a
    recording made by an older build still replays.
    """
    for frame in json.loads(path.read_text()):
        bus.publish({"kind": "frame", **frame})
        time.sleep(0.01)


def _viability_floor() -> int:
    """The postings threshold the planner and the drift trigger both use.

    Imported rather than restated: planner.VIABILITY_FLOOR and
    clock.has_drifted's default already have to agree, and a third copy in the
    page would be the one nobody remembers to change. Imported lazily so
    --replay still starts without pulling the model stack in.
    """
    from ..agents.planner import VIABILITY_FLOOR

    return VIABILITY_FLOOR


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)

    # A multiplier on every recorded gap. The page takes its pace from the run
    # itself, so this is the only pacing knob left — and it is a flag rather
    # than an on-screen control because during a LIVE run there is nothing to
    # speed up: the pace is however long the model takes.
    pace = 1.0
    if "--pace" in argv:
        i = argv.index("--pace")
        try:
            pace = float(argv[i + 1])
        except (IndexError, ValueError):
            sys.exit("--pace takes a multiplier on the recorded gaps, e.g. --pace 0.5")
        if pace <= 0:
            sys.exit("--pace must be greater than 0")
        del argv[i:i + 2]

    offline = "--offline" in argv
    if offline:
        argv.remove("--offline")

    replay_path: Path | None = None
    if "--replay" in argv:
        i = argv.index("--replay")
        rest = argv[i + 1:]
        replay_path = Path(rest[0]) if rest and not rest[0].startswith("-") else RECORDING
        if not replay_path.exists():
            sys.exit(
                f"No recording at {replay_path}.\n"
                "Do one live run first: uv run python -m src.ui.web"
            )

    config = {
        # Live renders each frame as it lands; replay plays the recorded gaps.
        "mode": "replay" if replay_path else "live",
        "pace": pace,
        "floor": _viability_floor(),
        # Used only for recordings made before frames carried their own timing.
        "fallbackMs": 700,
    }

    bus = Broadcast()
    server = ThreadingHTTPServer(("127.0.0.1", PORT), make_handler(bus, config))
    server.daemon_threads = True

    def work() -> None:
        try:
            if replay_path:
                _replay(bus, replay_path)
            else:
                run_case(bus.publish, offline=offline)
                # Only the frames. Activity messages are the live channel; a
                # replay reads the same calls back off each frame, so recording
                # them too would just be a second copy to keep in step.
                frames = [m for m in bus.history if m.get("kind") == "frame"]
                # An offline run is stub output with no real timings, and
                # writing it over .last_run.json would silently replace the one
                # good live take with something that must never be filmed. It
                # gets its own file, so a --replay after a day of UI work is
                # still the real run.
                path = OFFLINE_RECORDING if offline else RECORDING
                path.write_text(json.dumps(frames))
                print(f"\n  recording saved to {path.name}")
                print(f"  replay it with:  uv run python -m src.ui.web --replay {path.name}\n"
                      if offline else
                      "  replay it with:  uv run python -m src.ui.web --replay\n")
        except Exception as exc:  # a failed run should not leave a blank page
            bus.publish({
                "kind": "frame",
                "week": 0, "horizon": clock.HORIZON_WEEKS, "node": "error",
                "t": 0.0, "calls": [], "plan": None,
                "target": None, "rationale": f"{type(exc).__name__}: {exc}",
                "readiness": 0.0, "postings": None, "market": {}, "applications": 0,
                "events": [], "outcome": "", "done": True, "finished": True,
            })
            raise

    url = f"http://127.0.0.1:{PORT}/"
    if replay_path:
        mode = f"replaying {replay_path.name}"
    else:
        mode = "live run, stub agents" if offline else "live run"
    print(f"\n  {url}  ({mode})")
    print("  ctrl-c to stop\n")

    threading.Thread(target=work, daemon=True).start()
    try:
        webbrowser.open(url)
    except Exception:
        # No browser on this box, or it refused. The URL is printed above and
        # the server is already serving — this is a convenience, not a step.
        pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  stopped")


if __name__ == "__main__":
    main()

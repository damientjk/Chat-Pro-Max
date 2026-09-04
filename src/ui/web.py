"""Live web timeline. Owner: R5.

    uv run python -m src.ui.web                 # live run, real model calls
    uv run python -m src.ui.web --replay        # replay the last run, no key
    uv run python -m src.ui.web --replay F.json # replay a specific saved run
    uv run python -m src.ui.web --replay --speed 2   # 2 seconds per step

The page has its own transport: play/pause, speed, step, and a scrubber, so
the pace can be changed while filming without restarting anything. Space
toggles play, arrow keys step. --speed only sets where it starts.

The terminal renderer in timeline.py stays the source of truth for what an
event MEANS. This serves the same event log to a browser so the six months can
be watched as a shape -- postings collapsing, readiness resetting on the pivot
-- rather than read as a wall of text.

WHY STDLIB ONLY
---------------
No FastAPI, no uvicorn, no CDN. `http.server` with a Server-Sent Events
response does the whole job, so nothing enters pyproject.toml, requirements.txt
is unchanged, and Day 5's fresh-clone gate cannot fail because of this file. A
demo aid is not worth a dependency on the submission path.

REPLAY IS THE ONE TO FILM
-------------------------
A live run makes ~9 model calls, takes minutes, and on Groq's free tier can be
rate-limited mid-take. Every live run therefore saves itself to .last_run.json,
and --replay re-streams that recording with no key and no network. Get one good
live run, then film the replay as many times as you like.
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
PORT = 8000


# --------------------------------------------------------------------------
# Turning graph state into something a browser can draw
# --------------------------------------------------------------------------


def _frame(state: CaseState, node: str) -> dict:
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
        "week": state.get("week", 0),
        "horizon": clock.HORIZON_WEEKS,
        "node": node,
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
        "events": [e.model_dump() for e in state.get("events", [])],
        "applications": len(state.get("applications", [])),
        "outcome": state.get("outcome", ""),
        "done": bool(state.get("done")),
    }


def run_case(emit) -> None:
    """Drive the real graph, calling emit(frame) as each node lands."""
    from ..graph import build, memory_checkpointer
    from ..run_demo import initial_state

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
            emit(_frame(latest, node))

    emit({**_frame(latest, "end"), "finished": True})


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


def make_handler(bus: Broadcast, interval_ms: int):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args) -> None:
            pass  # the terminal is showing the run; access logs only clutter it

        def do_GET(self) -> None:
            if self.path.startswith("/events"):
                self._sse()
            else:
                body = PAGE.replace("__INTERVAL_MS__", str(interval_ms)).encode("utf-8")
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

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Reskilling Agent — live case</title>
<style>
  :root {
    --bg: #0d1014; --panel: #151a21; --line: #232a34;
    --ink: #e6ebf2; --muted: #8b96a6;
    --accent: #6fa8dc; --ok: #57b894;
    --drift: #e0a458; --replan: #6fa8dc; --offer: #57b894; --reposition: #c58fd6;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--ink);
    font: 15px/1.55 ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
  }
  .top {
    display: flex; align-items: baseline; gap: 1.4rem; flex-wrap: wrap;
    padding: 1.1rem 1.6rem; border-bottom: 1px solid var(--line); background: var(--panel);
  }
  .top h1 { margin: 0; font-size: 1.05rem; font-weight: 600; letter-spacing: -.01em; }
  .wk {
    font: 600 1.5rem/1 ui-monospace, SFMono-Regular, Menlo, monospace;
    font-variant-numeric: tabular-nums; color: var(--accent);
  }
  .status { margin-left: auto; font-size: .82rem; color: var(--muted); font-family: ui-monospace, monospace; }
  .controls {
    display: flex; align-items: center; gap: .75rem; flex-wrap: wrap;
    padding: .7rem 1.6rem; border-bottom: 1px solid var(--line); background: #11161c;
    font-size: .82rem; color: var(--muted);
  }
  .controls button, .controls select {
    background: #1d232c; color: var(--ink); border: 1px solid var(--line);
    border-radius: 4px; padding: .3rem .6rem; font: inherit; cursor: pointer;
  }
  .controls button:hover, .controls select:hover { border-color: #39424f; }
  .controls button:focus-visible, .controls select:focus-visible,
  .controls input:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .controls label { display: flex; align-items: center; gap: .4rem; }
  .controls input[type=range] { flex: 1; min-width: 140px; accent-color: var(--accent); }
  .controls .count { font-family: ui-monospace, monospace; font-variant-numeric: tabular-nums; }
  .grid { display: grid; grid-template-columns: minmax(0,1.15fr) minmax(0,1fr); gap: 1.1rem; padding: 1.1rem 1.6rem 3rem; }
  @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
  .card { background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: 1.1rem 1.2rem; }
  .card h2 {
    margin: 0 0 .9rem; font-size: .7rem; font-weight: 600; letter-spacing: .13em;
    text-transform: uppercase; color: var(--muted);
  }
  .target { font-size: 1.15rem; font-weight: 600; margin-bottom: .2rem; }
  .rationale { color: var(--muted); font-size: .88rem; margin-bottom: 1rem; }
  .bar { height: 12px; border-radius: 6px; background: #1d232c; overflow: hidden; margin: .5rem 0 .35rem; }
  .bar > i { display: block; height: 100%; background: var(--ok); width: 0; transition: width .35s ease; }
  .figs { display: flex; gap: 1.6rem; flex-wrap: wrap; margin-top: .9rem; }
  .fig { display: flex; flex-direction: column; gap: .1rem; }
  .fig b { font: 600 1.2rem/1 ui-monospace, monospace; font-variant-numeric: tabular-nums; }
  .fig span { font-size: .72rem; color: var(--muted); text-transform: uppercase; letter-spacing: .08em; }
  svg { width: 100%; height: 150px; display: block; }
  .feed { display: flex; flex-direction: column; gap: .55rem; max-height: 62vh; overflow-y: auto; }
  .ev { display: grid; grid-template-columns: 3.4rem 1fr; gap: .8rem; padding: .55rem .1rem; border-bottom: 1px solid var(--line); }
  .ev:last-child { border-bottom: none; }
  .ev .w { font: 500 .82rem/1.5 ui-monospace, monospace; color: var(--muted); font-variant-numeric: tabular-nums; }
  .ev .k {
    display: inline-block; font: 600 .64rem/1.6 ui-monospace, monospace; letter-spacing: .1em;
    text-transform: uppercase; padding: 0 .4rem; border-radius: 3px; margin-bottom: .15rem;
    background: #232a34; color: var(--muted);
  }
  .ev.drift .k { background: #3a2a16; color: var(--drift); }
  .ev.replan .k { background: #16283a; color: var(--replan); }
  .ev.reposition .k { background: #2e1f36; color: var(--reposition); }
  .ev.offer .k { background: #14301f; color: var(--offer); }
  .ev .s { font-size: .93rem; }
  .ev .b { font-size: .83rem; color: var(--muted); margin-top: .1rem; }
  .adapt { box-shadow: inset 2px 0 0 currentColor; padding-left: .6rem; }
  .adapt.drift { color: var(--drift); } .adapt.replan { color: var(--replan); }
  .adapt.reposition { color: var(--reposition); } .adapt.offer { color: var(--offer); }
  .adapt .s, .adapt .b, .adapt .w { color: var(--ink); }
  .adapt .b { color: var(--muted); }
</style>
</head>
<body>
  <div class="top">
    <h1>Reskilling-to-Placement Agent</h1>
    <span class="wk" id="wk">week 0</span>
    <span id="node" style="color:var(--muted);font-family:ui-monospace,monospace;font-size:.82rem"></span>
    <span class="status" id="status">connecting…</span>
  </div>

  <div class="controls">
    <button id="play" aria-label="Play or pause">Pause</button>
    <label>Speed
      <select id="speed">
        <option value="2000">0.5x — slowest</option>
        <option value="1200">0.75x</option>
        <option value="700" selected>1x</option>
        <option value="350">2x</option>
        <option value="120">4x</option>
      </select>
    </label>
    <button id="back" aria-label="Step back">&larr;</button>
    <button id="fwd" aria-label="Step forward">&rarr;</button>
    <input type="range" id="scrub" min="0" max="0" value="0" aria-label="Scrub through the run">
    <span class="count" id="count">0 / 0</span>
  </div>

  <div class="grid">
    <div style="display:flex;flex-direction:column;gap:1.1rem">
      <div class="card">
        <h2>Current target</h2>
        <div class="target" id="target">—</div>
        <div class="rationale" id="rationale"></div>
        <div class="bar"><i id="rbar"></i></div>
        <div style="font-size:.8rem;color:var(--muted)">
          Readiness <b id="rpct" style="color:var(--ink)">0%</b>
          — share of this target's skill gap already evidenced
        </div>
        <div class="figs">
          <div class="fig"><b id="postings">—</b><span>postings</span></div>
          <div class="fig"><b id="apps">0</b><span>applications</span></div>
          <div class="fig"><b id="months">—</b><span>months to ready</span></div>
          <div class="fig"><b id="conf">—</b><span>confidence</span></div>
        </div>
      </div>
      <div class="card">
        <h2>Postings for the current target</h2>
        <svg id="chart" viewBox="0 0 520 150" preserveAspectRatio="none" role="img"
             aria-label="Postings for the role being trained toward, by week"></svg>
        <div style="font-size:.78rem;color:var(--muted);margin-top:.4rem">
          Dashed line is the viability floor. Crossing it is what fires the re-plan.
        </div>
      </div>
    </div>

    <div class="card">
      <h2>Timeline</h2>
      <div class="feed" id="feed"></div>
    </div>
  </div>

<script>
const ADAPT = new Set(["drift", "replan", "reposition", "offer"]);
const FLOOR = 30;

// Frames are BUFFERED and played back on a timer rather than rendered the
// moment they arrive. That is what makes the run watchable: a replay can be
// paused on the pivot, stepped through, or scrubbed back, and a live run still
// renders as it goes because frames simply arrive slower than the timer.
let frames = [];
let idx = -1;
let playing = true;
let interval = __INTERVAL_MS__;
let timer = null;

const $ = id => document.getElementById(id);

function drawChart(upTo, horizon) {
  // Rebuilt from scratch each render so scrubbing backwards shows the chart as
  // it was, not as it ended. Thirty-odd points — the cost is irrelevant.
  const series = [];
  for (let i = 0; i <= upTo; i++) {
    const f = frames[i];
    if (f && f.postings != null) series.push([f.week, f.postings]);
  }
  const svg = $("chart");
  if (!series.length) { svg.innerHTML = ""; return; }
  const seen = new Map();
  for (const [w, v] of series) seen.set(w, v);
  const pts = [...seen.entries()].sort((a, b) => a[0] - b[0]);

  const W = 520, H = 150, pad = 10;
  const maxY = Math.max(FLOOR * 1.5, ...pts.map(p => p[1])) * 1.1;
  const x = w => pad + (w / Math.max(1, horizon)) * (W - pad * 2);
  const y = v => H - pad - (v / maxY) * (H - pad * 2);
  const line = pts.map(([w, v], i) => `${i ? "L" : "M"}${x(w).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const area = `${line} L${x(pts[pts.length - 1][0]).toFixed(1)},${H - pad} L${x(pts[0][0]).toFixed(1)},${H - pad} Z`;
  svg.innerHTML = `
    <path d="${area}" fill="rgba(111,168,220,.14)"/>
    <path d="${line}" fill="none" stroke="#6fa8dc" stroke-width="2"
          stroke-linejoin="round" stroke-linecap="round"/>
    <line x1="${pad}" x2="${W - pad}" y1="${y(FLOOR).toFixed(1)}" y2="${y(FLOOR).toFixed(1)}"
          stroke="#e0a458" stroke-width="1" stroke-dasharray="4 4"/>
    <circle cx="${x(pts[pts.length - 1][0]).toFixed(1)}" cy="${y(pts[pts.length - 1][1]).toFixed(1)}"
            r="3.5" fill="#6fa8dc"/>`;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function renderEvents(events) {
  $("feed").innerHTML = events.map(e => {
    const adapt = ADAPT.has(e.kind);
    const cls = `ev ${e.kind}` + (adapt ? ` adapt ${e.kind}` : "");
    const because = e.because ? `<div class="b">${escapeHtml(e.because)}</div>` : "";
    return `<div class="${cls}">
        <div class="w">wk ${e.week}</div>
        <div><span class="k">${escapeHtml(e.kind)}</span>
             <div class="s">${escapeHtml(e.summary)}</div>${because}</div>
      </div>`;
  }).join("");
  const feed = $("feed");
  feed.scrollTop = feed.scrollHeight;
}

function show(i) {
  if (i < 0 || i >= frames.length) return;
  idx = i;
  const f = frames[i];
  $("wk").textContent = `week ${f.week}`;
  $("node").textContent = f.node || "";
  $("target").textContent = f.target || "—";
  $("rationale").textContent = f.rationale || "";
  $("rbar").style.width = Math.round(f.readiness * 100) + "%";
  $("rpct").textContent = Math.round(f.readiness * 100) + "%";
  $("postings").textContent = f.postings ?? "—";
  $("apps").textContent = f.applications;
  $("months").textContent = f.months_to_ready ?? "—";
  $("conf").textContent = f.confidence == null ? "—" : Math.round(f.confidence * 100) + "%";
  drawChart(i, f.horizon);
  renderEvents(f.events || []);
  if (f.finished) {
    $("status").textContent = f.outcome ? `finished — ${f.outcome}` : "finished — ran out of runway";
  }
  syncControls();
}

function syncControls() {
  $("scrub").max = String(Math.max(0, frames.length - 1));
  $("scrub").value = String(Math.max(0, idx));
  $("count").textContent = `${idx + 1} / ${frames.length}`;
  $("play").textContent = playing ? "Pause" : "Play";
}

function tick() {
  if (playing && idx < frames.length - 1) show(idx + 1);
  else syncControls();
}

function restartTimer() {
  if (timer) clearInterval(timer);
  timer = setInterval(tick, interval);
}

$("play").onclick = () => {
  // Replaying from the start once finished is what you want between takes.
  if (!playing && idx >= frames.length - 1 && frames.length) show(0);
  playing = !playing;
  syncControls();
};
$("speed").onchange = e => { interval = Number(e.target.value); restartTimer(); };
$("back").onclick = () => { playing = false; show(idx - 1); };
$("fwd").onclick = () => { playing = false; show(idx + 1); };
$("scrub").oninput = e => { playing = false; show(Number(e.target.value)); };

document.addEventListener("keydown", e => {
  if (e.target.tagName === "SELECT" || e.target.tagName === "INPUT") return;
  if (e.code === "Space") { e.preventDefault(); $("play").click(); }
  if (e.code === "ArrowLeft") $("back").click();
  if (e.code === "ArrowRight") $("fwd").click();
});

const es = new EventSource("/events");
es.onopen = () => { $("status").textContent = "live"; };
es.onmessage = ev => {
  frames.push(JSON.parse(ev.data));
  if (idx < 0) show(0);
  else syncControls();
};
es.onerror = () => { $("status").textContent = "disconnected"; };

restartTimer();
</script>
</body>
</html>
"""


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------


def _replay(bus: Broadcast, path: Path) -> None:
    """Push the recording out quickly — the browser decides the pace.

    Pacing here would fight the page's own controls: you could not scrub back
    to a frame the server had not sent yet, and pausing would only stall the
    render while the buffer kept filling. So the server delivers, the client
    plays. The small delay is just politeness to the socket.
    """
    for frame in json.loads(path.read_text()):
        bus.publish(frame)
        time.sleep(0.01)


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)

    # Seconds per frame the page STARTS at; the speed selector overrides it
    # live. Filming usually wants this slower than feels right while building.
    interval_ms = 700
    if "--speed" in argv:
        i = argv.index("--speed")
        try:
            interval_ms = max(50, int(float(argv[i + 1]) * 1000))
        except (IndexError, ValueError):
            sys.exit("--speed takes seconds per frame, e.g. --speed 1.5")
        del argv[i:i + 2]

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

    bus = Broadcast()
    server = ThreadingHTTPServer(("127.0.0.1", PORT), make_handler(bus, interval_ms))
    server.daemon_threads = True

    def work() -> None:
        try:
            if replay_path:
                _replay(bus, replay_path)
            else:
                run_case(bus.publish)
                RECORDING.write_text(json.dumps(bus.history))
                print(f"\n  recording saved to {RECORDING.name}")
                print("  replay it with:  uv run python -m src.ui.web --replay\n")
        except Exception as exc:  # a failed run should not leave a blank page
            bus.publish({
                "week": 0, "horizon": clock.HORIZON_WEEKS, "node": "error",
                "target": None, "rationale": f"{type(exc).__name__}: {exc}",
                "readiness": 0.0, "postings": None, "market": {}, "applications": 0,
                "events": [], "outcome": "", "done": True, "finished": True,
            })
            raise

    url = f"http://127.0.0.1:{PORT}/"
    mode = f"replaying {replay_path.name}" if replay_path else "live run"
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

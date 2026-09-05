# Reskilling-to-Placement Agent

An agent that plans a mid-career transition, **re-plans when the job market moves**,
and places — treating every rejection as evidence that updates the plan.

> A recommender can suggest a course. It cannot notice in month three that the
> role you're training for stopped hiring — and rebuild the plan around what's
> still open.

## Run it

```bash
uv sync
uv run pytest          # no key needed
uv run python -m src.run_demo
```

**The demo needs a Groq key.** Day 2 replaced the sub-agent stubs with real
model calls, so the scaffold no longer runs end to end without one:

```bash
cp .env.example .env      # then paste your Groq key
```

Get one at [console.groq.com](https://console.groq.com) — free, no card. `.env`
lives at the repo root, is gitignored, and is read automatically.

## Watch it run

```bash
uv run python -m src.ui.web            # live web timeline at localhost:8000
uv run python -m src.ui.web --replay   # replay the last run — no key, no network
uv run python -m src.ui.web --offline  # real graph, stub agents — no key, no tokens
uv run python -m scripts.preview_ui    # terminal timeline, stub data, no key
```

The web view streams the case over Server-Sent Events using only the Python
standard library — no server framework, nothing added to `requirements.txt`.
It shows four things at once:

- **why this role** — the week's postings for every candidate role, the
  viability floor, and the planner's own reason for the one it picked
- **the training plan** — the actual steps, each ticking off as its week
  arrives, and what a re-plan carried forward
- **agent activity** — every model call as it happens: which agent, what it was
  asked, how long it took, what it decided, and which parts of the system are
  deterministic Python instead
- **the postings chart** — each targeted role against the floor, so the week-10
  collapse that forces the pivot is visible rather than asserted

There is no speed control, because the pace comes from the run. Every frame
records when it landed, so a replay reproduces the real gaps — a long model
call is a real pause with the agent that caused it named on screen. `--pace 0.5`
scales those gaps for filming.

**Every live run records itself to `.last_run.json`**, and `--replay` re-streams
it with no key and no network. Get one good live run, then film the replay —
a take can't be spoilt by a rate limit. `--offline` records separately, to
`.offline_run.json`, so iterating on the UI can never overwrite the good take.

## Score it against the baseline

```bash
uv run python -m src.eval.harness
```

Runs the agent and the one-shot baseline over the same six personas and prints
the comparison — dead paths caught, months saved, training spend avoided, and
how many of each ended placed. This is where the benefits slide's numbers come
from; every one of them is computed here rather than asserted.

Needs a key, and it is a full case per persona, so run it on Bedrock rather
than Groq's free tier — six cases will not fit inside 8000 tokens a minute.

**The test suite still runs keyless, and always should.** `tests/conftest.py`
swaps the five model-calling agents for deterministic doubles, so the graph is
tested offline, in milliseconds, without spending tokens or failing because a
model phrased something differently. `tests/test_agent_doubles.py` fails if a
double drifts from the real signature it stands in for.

Use `pytest`, not `unittest discover` — the latter silently collects only the
`unittest`-style tests and skips the graph suite entirely.

## Providers — one environment variable

Groq's free tier is the build-time provider: rate limited, not billed, no
credentials to share. Bedrock is for the runs that get judged — the eval sweep
and the recorded demo — where a rate limit mid-run would cost us something.

```bash
uv sync --extra aws
export LLM_PROVIDER=bedrock
export AWS_DEFAULT_REGION=ap-southeast-1
```

Nothing else changes. `_common.chat_model()` returns a LangChain model for
whichever provider `LLM_PROVIDER` names, and both implement the same interface,
so `.invoke()`, `.bind_tools()` and `.with_structured_output()` behave the same
on either side.

**That only stays true if sub-agents call `_common.chat_model()` and never
`ChatGroq` directly.** Hardcode the provider into an agent and the switch is
gone. Bedrock model access is granted per model and per region and is off by
default — see [`PLAN.md`](PLAN.md) for the setup and the cost numbers.

## What it prints today

```
SIX-MONTH ADAPTATION TIMELINE
-----------------------------
Week  0 | TARGET      | target: Supply Chain Data Analyst
        Reason: hiring holds at 133 postings, and the reconciliation experience transfers
Week 10 | DRIFT       | Supply Chain Data Analyst postings fell to 12
        Reason: below the floor we set for a viable target
Week 10 | REPLAN      | switched to Customer Success Coordinator
        Reason: still hiring — and keeps the SQL, dashboarding work already done
Week 18 | APPLICATION | 3 applications sent
Week 19 | REPOSITION  | rewrote how we describe their experience
        Reason: the last 3 applications all died at resume screening
Week 21 | OFFER       | offer: Customer Success Coordinator
```

`DRIFT → REPLAN` and `REPOSITION` are the product. Everything else is
scaffolding around them. Both carry a `Reason:` line, because an adaptation
nobody can see the reason for may as well not have happened.

The role names come from the model reading a live market snapshot, so they vary
between runs. What does not vary is the shape: a target that stops hiring gets
abandoned, and a rejection pattern rewrites the pitch.

## The graph

```
START -> intake -> target -> plan -> advance_week <-------------+
                                          |                     |
                                      route()   <- triggers.py, pure Python
                                          |                     |
   +---------+-------------+--------------+---------+---------+ |
   |         |             |              |         |         | |
 drift   replan_gap    retarget      reposition   apply    continue
   |         |             |              |         |         |
 replan  replan_gap    retarget      reposition   apply       -+
   |         |             |              |         |
   |         |             |              +-> apply |
   |         |             |                   |    |
   +---------+-------------+-------------------+----+----------+
                                                                |
                                        every node returns here -+

                              route() -> END when an offer lands
                              or week 26 arrives
```

**The market moved** takes the `drift` edge. **The rejections share a shape**
takes one of three, depending on what the pattern says: dying at screening
means the pitch is wrong (`reposition`), losing at the technical round means
the plan missed a skill (`replan_gap`), and a rewrite that still cannot pass a
screen means the target itself is wrong (`retarget`).

A reposition goes straight to `apply` in the same week: a rewrite exists to
be tested, and the horizon can arrive before the next scheduled batch would.

`route()` has **no model call in it**. Control flow stays deterministic,
unit-testable without a key, and identical across every take of the demo video.

## The 5-day plan

[`PLAN.md`](PLAN.md) — day-by-day schedule, role split, gates, cut list, and the
Q&A to rehearse. Read it before Wednesday.

[`EXPLAINER.md`](EXPLAINER.md) — the same project with no jargon, for anyone
non-technical: what it does, why it matters, and who is building which part.

## Layout — one owner per directory

| Path | Owner | What |
|---|---|---|
| `src/contracts.py` | R2 | Shared types. **Frozen after the Day 1 meeting.** |
| `src/graph.py` | R2 | The LangGraph supervisor: nodes, edges, state |
| `src/triggers.py` | R2 | Routing decisions — pure Python |
| `src/agents/` | R3 | Archaeologist, planner, placement + prompts |
| `src/market/` | R4 | Synthetic postings, replay clock, drift events |
| `src/eval/` | R4 | Personas with ground truth, scoring harness |
| `src/signals/` | R1 | Rejection-pattern detection, outcome metrics |
| `src/baseline/` | R1 | Naive one-shot recommender, for A/B comparison |
| `src/ui/` | R5 | Timeline visualisation |

`contracts.py` is the only file more than one person depends on. Changing it
after Day 1 is a whole-team decision.

## Where the stubs are

Every sub-agent now makes a real model call. What is left is marked `TODO(Rn)`
with the owner — mostly tuning and numbers to record, not unwritten code:

```bash
grep -rn "TODO(R" src/
```

Replacing a stub never required touching the graph, and it did not: the five
agent functions were swapped one at a time behind fixed signatures, and
`graph.py` was not edited for any of them. That is the whole point of the shape.

## Pinned dependencies

`pyproject.toml` + `uv.lock` are the source of truth. `requirements.txt` is
generated from them, because it is a named submission deliverable — regenerate
it whenever dependencies change:

```bash
uv export --no-hashes --no-dev -o requirements.txt
```

## Never commit

`.env` is gitignored. Before submitting:

```bash
git log -p | grep -i "gsk_\|aws_secret"
```

All data in this repo is synthetic. No real candidates, no real postings.

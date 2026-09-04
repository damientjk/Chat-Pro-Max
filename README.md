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
  wk  0      found 3 capabilities
  wk  0      target: Supply Chain Data Analyst
  wk 10  !!  Supply Chain Data Analyst postings fell to 14
            because below the floor we set for a viable target
  wk 10  ->  switched to Logistics Systems Analyst
            because still hiring, and reuses the SQL work already done
  wk 18      3 applications sent
  wk 19  ->  rewrote how we describe their experience
            because the last 3 applications all died at resume screening
  wk 20  **  offer: Logistics Systems Analyst
```

Those two `->` lines are the product. Everything else is scaffolding around them.

## The graph

```
START -> intake -> target -> plan -> advance_week
                                         |
                                     route()          <- triggers.py, pure Python
                                         |
          +--------------+---------------+--------------+
          |              |               |              |
        drift        reposition        apply        continue --+
          |              |               |                     |
        replan       reposition      placement                 |
          |              |               |                     |
          +--------------+---------------+---------------------+
                                  back to advance_week
```

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

### R1 — signals and baseline

Built in this order, each one usable on its own:

1. `src/baseline/naive.py` — one-shot baseline recommender.
2. `src/signals/rejection.py` — repeated-rejection re-plan signal.
3. `src/signals/actions.py` — rejection-stage-specific re-plan guidance.
4. `src/signals/outcomes.py` — baseline-versus-agent benefit metrics.
5. `src/r1_workflow.py` — typed handoff of R1 evidence to R2.
6. `evidence.md` — source log for claims in the deck.

These now read the shared types from `src/contracts.py` — `SkillInventory`,
`TargetRole`, `ApplicationOutcome` and `Stage` — rather than the temporary
duck-typed shims they were written against. The baseline rule is unchanged: it
selects once and never re-plans.

```bash
uv run python -m scripts.r1_demo
```

## Where the stubs are

Every stub is marked `TODO(Rn)` with the owner. Find yours:

```bash
grep -rn "TODO(R" src/
```

Replacing a stub never requires touching the graph. That is the whole point of
the shape.

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

# Reskilling-to-Placement Agent

An agent that plans a mid-career transition, **re-plans when the job market moves**,
and places — treating every rejection as evidence that updates the plan.

> A recommender can suggest a course. It cannot notice in month three that the
> role you're training for stopped hiring — and rebuild the plan around what's
> still open.

## Run it

```bash
uv sync
uv run python -m src.run_demo
```

**No API key needed yet.** Every sub-agent is a stub and every routing decision
is ordinary Python, so the whole six-month simulation runs offline. That is
deliberate: the pipe is connected before anything is intelligent, so each person
replaces their own stub without waiting on anyone else.

When you start making real model calls:

```bash
cp .env.example .env      # then paste your Groq key
```

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

Every stub is marked `TODO(Rn)` with the owner. Find yours:

```bash
grep -rn "TODO(R" src/
```

Replacing a stub never requires touching the graph. That is the whole point of
the shape.

## Never commit

`.env` is gitignored. Before submitting:

```bash
git log -p | grep -i "gsk_\|aws_secret"
```

All data in this repo is synthetic. No real candidates, no real postings.

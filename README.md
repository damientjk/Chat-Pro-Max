# Reskilling-to-Placement Agent

An agent that plans a mid-career transition, **re-plans when the job market
moves**, and places, treating every rejection as evidence that updates the plan.

> A recommender can suggest a course. It cannot notice in month three that the
> role you're training for stopped hiring, and rebuild the plan around what's
> still open.

## The problem

14,400 people were retrenched in Singapore in 2025, and six months on, around
40% of them have not re-entered employment. For workers in their forties the
re-entry rate has historically fallen further still. The support exists: the
SkillsFuture Level-Up Programme puts a S$4,000 credit top-up in the hands of
mid-career workers over 40. But a credit only helps if it is spent on a role
that is still hiring when the training finishes.

Sources for every figure above, with publisher and date, are in
[`docs/evidence.md`](docs/evidence.md).

Six months is long enough for the target to disappear. That gap, between a plan
made in month one and a market that has moved by month four, is what this agent
exists to close.

## What it actually does

One candidate, twenty-six weeks, simulated in about a minute. The agent picks a
reachable target role, sequences training against the specific skills gap, and
then **keeps watching**. Two things make it change course:

**The market moved.** The role it is training toward drops below a viability
floor of 30 postings a week. The agent abandons it, picks a target that is still
hiring, and carries the finished training forward rather than starting over.

**The rejections share a shape.** Three applications dying at the same stage is a
signal, and which stage decides the fix. Dying at resume screening means the
pitch is wrong, losing at the technical round means the plan missed a skill, and
a rewritten pitch that still cannot pass a screen means the target itself is
wrong. Each takes a different edge in the graph.

Every adaptation is recorded with its reason. An adaptation nobody can see the
reason for may as well not have happened.

## Run it

```bash
uv sync
uv run pytest                          # 66 tests, no API key needed
uv run python -m src.ui.web            # the live run (needs a key)
```

The demo makes real model calls, so it needs a Groq key. Free, no card, from
[console.groq.com](https://console.groq.com):

```bash
cp .env.example .env                   # then paste the key in
```

`.env` sits at the repo root, is gitignored, and is read automatically.

**To see it without a key at all:**

```bash
uv run python -m src.ui.web --replay   # re-stream a recorded run
uv run python -m src.ui.web --offline  # the real graph, stub agents
uv run python -m src.run_demo          # the same case, in the terminal
```

## What you see

The web view streams the case to a browser over Server-Sent Events using only
the Python standard library: no server framework, no CDN, nothing added to the
dependency list. Four things are on screen at once:

- **why this role**: every candidate role's postings that week, the viability
  floor, and the planner's own stated reason for the one it picked
- **the training plan**: the actual steps, each ticking off as its week arrives
- **agent activity**: every model call, naming which agent, what it was asked,
  how long it took, and what it decided
- **the postings chart**: each targeted role against the floor, so the week-10
  collapse that forces the pivot is visible rather than asserted

There is no speed control, because the pace comes from the run itself. Every
frame records when it landed, so playback reproduces the real gaps: a long model
call becomes a pause of the same length rather than a step that never comes. Each
simulated week also holds the screen for at least a second, so six months reads
as six months. A full run plays in about a minute; `--pace` scales it.

Every live run records itself to `.last_run.json`, and `--replay` re-streams it
with no key and no network, so a rate limit cannot spoil a take.

## Does it beat just asking a model once?

```bash
uv run python -m src.eval.harness
```

Runs the agent and a one-shot baseline recommender over the same six personas and
prints the comparison: how many targets the baseline picked that were dead by
week 10, how many months and how much training spend the pivot saved, and how
many cases of each ended in a placement.

Every number on the benefits slide is computed here rather than asserted.

This is a full case per persona, so run it on Bedrock. Six cases will not fit
inside Groq's free tier of 8000 tokens a minute.

## A run that placed

```
Week  0 | INTAKE      | found 4 capabilities
Week  0 | TARGET      | target: Supply Chain Data Analyst
        Reason: aligns with the candidate's supply-chain and data-management
        experience, and has the highest hiring volume (133 postings)
Week 10 | DRIFT       | Supply Chain Data Analyst postings fell to 12
        Reason: below the floor we set for a viable target
Week 10 | REPLAN      | switched to Logistics Systems Analyst
        Reason: strong supply-chain operations skills combined with SQL and
        dashboarding — core requirements for the role, and 77 postings this
        week — and keeps the SQL, dashboarding work already done
Week 25 | REPOSITION  | rewrote how we describe their experience
        Reason: the last 3 applications all died at resume screening
Week 25 | OFFER       | offer: Logistics Systems Analyst
```

`DRIFT → REPLAN` and `REPOSITION` are the product. Everything else is scaffolding
around them.

Role names come from the model reading a live market snapshot, so they vary
between runs. What does not vary is the shape: a target that stops hiring gets
abandoned, and a rejection pattern rewrites the pitch.

## How it is built

```
START -> intake -> target -> plan -> advance_week <------------+
                                          |                    |
                                      route()  <- triggers.py, pure Python
                                          |                    |
        +-----------+------------+--------+-------+---------+  |
        |           |            |                |         |  |
      drift    replan_gap    retarget        reposition    apply
        |           |            |                |         |  |
      replan        |            |                +-> apply |  |
        |           |            |                     |    |  |
        +-----------+------------+---------------------+----+--+
                                                           |
                                      every node returns --+

                     route() -> END on an offer, or at week 26
```

LangGraph supervises; the sub-agents are the intelligence. **`route()` makes no
model call.** Control flow is deterministic, unit-testable without a key, and
identical across every take of the demo.

A reposition goes straight to `apply` in the same week. A rewrite exists to be
tested, and the horizon can arrive before the next scheduled batch would.

The test suite runs keyless by design: `tests/conftest.py` swaps the five
model-calling agents for deterministic doubles, so the graph is tested in
milliseconds without spending tokens or failing because a model phrased something
differently. `tests/test_agent_doubles.py` fails if a double drifts from the real
signature it stands in for.

### One environment variable switches provider

```bash
uv sync --extra aws
export LLM_PROVIDER=bedrock
```

Nothing else changes. Sub-agents call `_common.chat_model()` and never a provider
class directly, so `.invoke()`, `.bind_tools()` and `.with_structured_output()`
behave the same on either side.

### Who built what

| Path | What |
|---|---|
| `src/contracts.py` | Shared types, the one file everyone depends on |
| `src/graph.py`, `src/triggers.py` | The supervisor and its routing |
| `src/agents/` | Skill archaeologist, planner, placement |
| `src/market/`, `src/eval/` | Synthetic postings, personas, scoring harness |
| `src/signals/`, `src/baseline/` | Rejection detection, one-shot comparison |
| `src/ui/` | Terminal and web timelines |

## What is real and what is not

Being straight about this, because it is the first thing worth asking:

- **The job market is synthetic.** `src/market/clock.py` generates a reproducible
  26-week series so the drift event lands on the same week in every take. It is
  not live postings data.
- **The employer side is a model, not a job board.** `placement.apply()` has a
  model read the candidate's pitch the way a screener would and say how far each
  application got. That is what turns a rejection into a signal the graph can
  route on.
- **Nothing is ever submitted anywhere.** If this were wired to real postings,
  submission would go behind an explicit human gate. That is a product
  commitment, not a to-do.
- **All data in this repo is synthetic.** No real candidates, no real postings.

The adaptation logic, the routing, the contracts and the evaluation are real, and
would not change if the market feed were.

## Also in this repo

- [`docs/EXPLAINER.md`](docs/EXPLAINER.md): the same project with no jargon
- [`docs/evidence.md`](docs/evidence.md): every external figure, with publisher and date
- `pyproject.toml` + `uv.lock` are the source of truth for dependencies;
  `requirements.txt` is generated from them with
  `uv export --no-hashes --no-dev -o requirements.txt`

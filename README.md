# A reskilling plan that responds to market changes

**CP Max**: Yizhuo, Damien, Anjie, Donghua, Sean

An agent that plans a career transition, **re-plans when the job market moves**,
and treats every rejection as evidence that updates the plan.

> A recommender can suggest a course. It cannot notice in month three that the
> role you're training for stopped hiring, and rebuild the plan around what's
> still open.

## The problem

Job stability is a live problem in Singapore, for graduates who cannot find a
first job and for experienced workers who cannot get back in. 14,400 people were
retrenched in 2025, and six months on, around 40% of them had not re-entered
employment. For workers in their forties the re-entry rate has historically
fallen further still.

In theory this is covered. SkillsFuture funds the retraining, MyCareersFuture
and the job portals carry the vacancies, and the SkillsFuture Level-Up Programme
puts a S$4,000 credit top-up in the hands of mid-career workers over 40. The
support exists.

What none of it does is notice when the destination changes. Someone can spend
months on a course and find that demand for the role they were training toward
has moved.

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

### 1. Install, and pick a provider

**Groq**:

```bash
uv sync
cp .env.example .env    # then paste a key from console.groq.com
```

**Bedrock**:

```bash
uv sync --extra aws
export LLM_PROVIDER=bedrock
export AWS_DEFAULT_REGION=us-east-1
```

Two things about Bedrock that are easy to lose time on. It defaults to
`openai.gpt-oss-120b-1:0`, one of the OpenAI **open-weight** models Bedrock
hosts, not GPT-4 or GPT-5, which it does not host at all; `BEDROCK_MODEL`
selects the smaller `openai.gpt-oss-20b-1:0`. And model access is granted per
model *and* per region, with these enabled in `us-east-1`, so the same call
elsewhere fails on access rather than on a missing model.

`.env` sits at the repo root, is gitignored, and is read automatically.

### 2. Run it

```bash
uv run python -m src.ui.web            # one case, live, in a browser
uv run python -m src.run_demo          # the same case, in the terminal
uv run python -m src.eval.harness      # the six-persona evaluation (Bedrock)
```

**Nothing above works without a key. These need none:**

```bash
uv run pytest                          # 66 tests
uv run python -m src.ui.web --replay   # re-stream a recorded run
uv run python -m src.ui.web --offline  # the real graph, stub agents
uv run python -m scripts.preview_ui    # the terminal timeline, stub agents
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

Sub-agents call `_common.chat_model()` rather than a provider class, so the
whole graph moves between Groq and Bedrock on one environment variable.

### The model calls

Five functions make every model call in the system. Each asks for a Pydantic
type back through `with_structured_output`, so what comes out of the model is
validated before it reaches the graph rather than parsed out of prose.

| Agent | Called from | Asked to | Returns |
|---|---|---|---|
| Skill archaeologist | `intake` | read the CV for evidence of what they can already do | `SkillInventory` |
| Planner | `target`, and again on every re-plan | choose a target role against this week's hiring | `TargetRole` |
| Planner | `plan`, and again on every re-plan | sequence training against the specific gap | `Plan` steps |
| Positioner | `apply`, `reposition` | describe the candidate in the target role's vocabulary | headline, summary, proof points |
| Screener | `apply` | judge a batch of applications from the employer's side | stage reached, per application |

How many calls a case makes depends on how often it has to adapt: three to set
the case up, two more each time the plan is rebuilt, one per application batch,
and one whenever the pitch is rewritten. The recorded run in this repo made 11
over 26 weeks; a case that places earlier makes fewer.

Everything else is ordinary Python. `route()` picks one of seven edges,
`clock.has_drifted()` tests the market against the floor, and
`rejection.diagnose()` reads the pattern in the outcomes. None of them call a
model, so the control flow is the same on every run and the tests need no key.

The web view's **agent activity** panel lists these calls as they happen, with
what each one decided.

The test suite runs keyless by design: `tests/conftest.py` swaps the five
model-calling agents for deterministic doubles, so the graph is tested in
milliseconds without spending tokens or failing because a model phrased something
differently. `tests/test_agent_doubles.py` fails if a double drifts from the real
signature it stands in for.

### Who built what

| Path | What |
|---|---|
| `src/contracts.py` | Shared types, the one file everyone depends on |
| `src/graph.py`, `src/triggers.py` | The supervisor and its routing |
| `src/agents/` | Skill archaeologist, planner, placement |
| `src/market/`, `src/eval/` | Synthetic postings, personas, scoring harness |
| `src/signals/`, `src/baseline/` | Rejection detection, one-shot comparison |
| `src/ui/` | Terminal and web timelines |

## What this is, and what it is not

This is a **controlled synthetic replay**, not a claim about live labour-market
performance. It demonstrates a mechanism and a way of evaluating it. It does not
claim the figures predict real employment outcomes.

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

The adaptation logic, the routing, the contracts and the evaluation are real,
and would not change if the market feed were.

The evaluation's strength is that it is like-for-like: the baseline and the
agent start from identical information and run the same 26-week replay, so the
only difference is whether the plan can be revisited. Its limit is a small
synthetic cohort of six.

### What would come next

- **Validate with users.** Whether someone facing a transition can follow the
  plan, challenge its assumptions, and correct the skills and target roles it
  inferred. That needs informed consent and clear disclosure that the system is
  experimental.
- **Connect verified data.** Licensed vacancy data, an auditable definition of
  role viability, and a source-verified course catalogue, with freshness made
  visible, since stale job data would recreate the exact problem this addresses.
- **Measure outcomes properly.** Whether a target stays viable, whether a plan
  gets finished, whether a placement lasts. Never an offer alone: transitions
  involve wage quality, health, caregiving and local conditions that a single
  binary outcome hides.

Any deployment would have to preserve human approval, disclose uncertainty,
protect personal data, and never apply on someone's behalf.

## Also in this repo

- [`docs/EXPLAINER.md`](docs/EXPLAINER.md): the same project with no jargon
- [`docs/evidence.md`](docs/evidence.md): every external figure, with publisher and date
- `pyproject.toml` + `uv.lock` are the source of truth for dependencies;
  `requirements.txt` is generated from them with
  `uv export --no-hashes --no-dev -o requirements.txt`

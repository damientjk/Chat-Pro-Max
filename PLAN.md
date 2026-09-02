# 5-Day Build Plan — Reskilling-to-Placement Agent

**Submission: Monday 7 September.** One submission only — no re-uploads.
Build window: **Wed 2 Sep → Sun 6 Sep**. Monday is buffer and upload, not build time.

| Deliverable | Limit |
|---|---|
| Project files / workflow | 5 GB, **1 submission only** |
| Presentation deck | 10 slides max |
| Demo video | 5 minutes max |

Judging is 5 criteria at 20% each: benefits, originality, effectiveness, technical quality, presentation. **Only 20% is code.** Budget your time accordingly — this plan gives roughly equal weight to build and to narrative, on purpose.

Confirmed against the 24 Aug deck (Session 3, pp. 29–31). Each criterion is scored **0 / 1 / 2**, so there is no partial credit for nearly working: "functional prototype with minor work needed for production" is 1 point, "partially functional" is 0. Note also that **no criterion mentions AWS, Bedrock or any platform** — see the provider section below before anyone spends a day on infrastructure that earns nothing.

## Where we are

The repo is scaffolded and **already runs end to end** — 26 simulated weeks through a real LangGraph state machine, both adaptation events firing, with no API key needed. That was Day 1's original gate, so the schedule below starts a step ahead of where it would otherwise.

```bash
brew install uv
uv sync
uv run python -m src.run_demo
```

Everything that would call a model is a stub marked `TODO(Rn)`. Find yours:

```bash
grep -rn "TODO(R" src/
```

**Replacing a stub never requires touching the graph.** That is what the shape buys us, and it is why five people can work in parallel from the first morning.

---

## The product, in one paragraph

A 45-year-old is retrenched. Our agent works out what they can actually already do, picks a reachable adjacent role and costs it honestly, sequences the retraining — then **watches the job market weekly and re-plans when the target moves**. At the end it translates their experience into the new field's vocabulary, matches them to live openings, and treats every rejection as evidence that updates the plan.

**The sentence that wins the room:** *"A recommender can suggest a course. It cannot notice in month three that the role you're training for stopped hiring — and rebuild the plan around what's still open."*

---

## Models, providers and the AWS credits

**Build on Groq. Submit on Bedrock.**

Groq's free tier is *rate limited, not billed* — perfect for five people iterating all week, with no credentials to share and no setup to go wrong. R1 holds **$20 of AWS credits**, which at the published Haiku 4.5 rate ($1 in / $5 out per million tokens, Session 1 deck p39) is on the order of 500 full 26-week runs. A single run costs roughly **4 cents**. Money is not the constraint.

So spend the credits only where a rate limit would actually cost us something:

| Run | Provider | Why |
|---|---|---|
| Day-to-day development | Groq | Free, no credentials, no per-person setup |
| The eval sweep (6 personas × agent + baseline) | Bedrock | 12 runs back to back is exactly what a free tier throttles. ~$0.50 |
| The recorded demo takes (Day 4) | Bedrock | A rate-limit error mid-take is an expensive way to learn about free tiers |

There is also a quality argument for the runs that get judged: the Groq default is `openai/gpt-oss-20b`, a small model, and R3's targeting and archaeology depend on `.with_structured_output()` returning valid structured data every time. Small models are flakier at that. Use Haiku 4.5 for anything a judge sees.

**The rule that makes the switch real — agreed at the Day 1 meeting:**

> Sub-agents call `_common.chat_model()`. **Never `ChatGroq` directly.**

That factory returns a LangChain model for whichever provider `LLM_PROVIDER` names, and both sides implement the same interface — so `.invoke()`, `.bind_tools()` and `.with_structured_output()` behave identically. Hardcode `ChatGroq` into the three agent files and the credits become unusable no matter what is in the account. One line of agreement now, or a refactor on Day 4.

Switching, once the rule holds:

```bash
uv sync --extra aws
export LLM_PROVIDER=bedrock
export AWS_DEFAULT_REGION=ap-southeast-1
```

**The long pole is access, not money.** Bedrock model access is granted per model, per region, and is **off by default** (Session 1 deck p41) — Haiku 4.5 in `ap-southeast-1`. R1 must enable it and make one successful call **today**. An ungranted permission discovered on Day 4 is a lost afternoon; ruling it out tonight costs nothing.

Guardrails: R1 sets an AWS Budget alert at ~$15, and nobody shares AWS keys in a channel — `.env` is gitignored for this reason.

Free bonus for the deck: `_common.report_usage()` already prints per-call token counts, so R1 can put a **measured** cost-per-candidate on the Technical Quality slide. *"Each full six-month plan costs about four cents to produce"* is a claim judges cannot poke a hole in, because we measured it rather than estimated it.

---

## Roles

| | Role | Owns |
|---|---|---|
| **R1** | Lead / Baseline & Narrative | Baseline comparator, signals module, evidence, deck, presents on the day |
| **R2** | Agent Core | LangGraph case supervisor, state schema, re-plan trigger logic |
| **R3** | Sub-Agents | Skills archaeologist, path planner, placement agent, all prompts |
| **R4** | Data & Eval | Synthetic market, replay clock, drift events, eval harness |
| **R5** | Demo & Delivery | UI, timeline visualisation, video, README, packaging |

R2+R3 pair frequently. R4 unblocks everyone on Day 1 and must move first.

**Everyone codes.** R1 builds the baseline comparator and the signals module Days 1–3, then hands off and switches to narrative from Day 3 evening. R5 crosses over the other way — UI Days 1–3, then video and packaging Days 4–5.

### Directory ownership

One owner per directory. Only `contracts.py` is shared, which is why it is written in the Day 1 morning meeting and then frozen — an unannounced change to a shared type on Day 3 costs the whole team an afternoon.

```
src/
  contracts.py          R2   shared types. Written Day 1 AM, then FROZEN
  graph.py              R2   LangGraph supervisor: nodes, edges, state
  triggers.py           R2   re-plan trigger logic
  agents/               R3   archaeologist, planner, placement + prompts
  market/               R4   synthetic postings, replay clock, drift events
  eval/                 R4   personas, harness
  signals/              R1   rejection-pattern detection, outcome metrics
  baseline/             R1   naive one-shot recommender, for A/B comparison
  ui/                   R5   timeline visualisation
```

### Why R1 builds the baseline

The baseline is a deliberately dumb version of our product: a one-shot recommender that picks a course on day one and never re-plans. We run it against the same eval personas as the real agent.

That comparison produces the single number the benefits slide lives on — *"the naive version put N of 6 candidates on a path that had closed by month three; ours caught all of them."* It is also the answer to the question a judge will certainly ask, *"isn't this just a recommender?"*, and it is far stronger coming from a team that built the recommender and measured it losing.

It sits off the critical path — nothing else imports it — so if R1 gets pulled into deck work early, it can slip without blocking anyone.

---

## Do this TODAY (Tue 1 Sep), before Day 1

**Already done:** repo scaffolded, contracts drafted, graph wired, demo running, `uv.lock` committed.

**Still to do tonight:**

- **R2** — create the GitHub remote, push, add all five as collaborators. Decide public vs. private (check whether the submission wants a link or a zip — private is fine if it is a zip).
- **Everyone** — clone, `brew install uv`, `uv sync`, then confirm `uv run python -m src.run_demo` prints the timeline on **your own machine**. Five people, five machines; someone will have a broken Python or a permissions problem and you want that surfacing tonight, not in Wednesday's meeting.
- **Everyone** — read `src/contracts.py` before the meeting. It is a draft written to be argued with, and the meeting is faster if nobody is reading it for the first time.
- **R1** — **enable Bedrock model access** for the Haiku 4.5 model id pinned in `src/_common.py`, in `ap-southeast-1`, then prove it with one real call. It is off by default and is the one item here with a lead time we do not control. Set the AWS Budget alert at the same time.
- **R1** — pull the real numbers from source: MOM Labour Market Report (retrenchment volume, re-entry rate within 6 months by age band), SkillsFuture participation. **Verify against the primary source with a date — do not cite from memory in front of judges.**

Note: `~/.local/bin` is not on the PATH by default on macOS, so anyone installing uv via the curl script rather than Homebrew needs to add it.

**Note on evidence.** We are not running user interviews. That means our evidence comes entirely from published sources, so R1 must work harder to support the load-bearing claim — that people spend credits without a target role in mind. Secondary data proves retrenchment is hard; it does not prove our specific mechanism. Close the gap with first-person published accounts (news features on retrenched mid-career workers, workforce surveys from NTUC/e2i or recruitment firms, public forum threads) and quote them as such. **On the slide, say "published accounts" — never imply we spoke to anyone.**

---

## Day 1 — Wed 2 Sep — First real model call in the loop

**Goal: intake → target → plan running on genuine model output for one persona.** The scaffolding exists; today it stops being stubs.

**09:00–10:30 — Whole team, no laptops open**
Lock these and do not reopen them:
1. Final problem statement in POV format
2. The one candidate persona the demo follows
3. Scope frozen against the cut list below
4. **Review and freeze `src/contracts.py`** — it is drafted, so this is an editing job rather than a blank page. Change what is wrong, then freeze it. Every other module imports from it; an unannounced change on Day 3 costs the whole team an afternoon.
5. **The provider rule** — sub-agents call `_common.chat_model()`, never `ChatGroq` directly. Ten seconds to agree, and it is what keeps Bedrock one environment variable away all week. See the provider section above.

**Then split — everyone replaces their own stubs:**

- **R1** — `baseline/naive.py`: make the one-shot recommender real. Same inputs as the agent, picks once, never re-plans. Evening: MOM and SkillsFuture figures with sources and dates.
- **R2** — real state transitions and checkpointing. Make `replan` carry learning forward rather than restarting — a pivot that reuses completed training is what makes it feel like a plan.
- **R3** — archaeologist and targeting on real model calls, structured output via pydantic. **Targeting must also say what is NOT reachable** — that honesty is the product.
- **R4** — replace the step-function market with a generated series with noise (a cliff edge looks fake on the timeline); five more eval personas with expected targets.
- **R5** — the visual timeline, reading the real event log.

**Gate:** `run_demo` still prints both adaptation events, but intake, targeting and planning are now genuine model output for the demo persona.

---

## Day 2 — Thu 3 Sep — Make each phase real

**Goal: the placement half becomes real, so the whole loop runs on model output.**

- **R1** — tune `signals/rejection.py` against real outcomes: all dying at screening vs. losing at the technical round mean different fixes. Baseline runs across all six personas. Evening: core insight written as one sourced sentence.
- **R2** — the re-plan path carries prior progress forward; persistence between phases holds up over 26 weeks
- **R3** — `placement.translate` and `placement.apply` on real model calls. Keep the property that repositioning changes the outcome — if applications always succeed first try, the rejection loop never demonstrates itself.
- **R4** — the eval harness scores agent vs. baseline and produces a number
- **R5** — both adaptation events visibly annotated on the timeline with their reasons

**Evening checkpoint (20 min):** run it end to end for each other. Honest read on whether Day 3's gate is already met.

**Gate:** both adaptation events fire on genuine model output, not stubs.

---

## Day 3 — Fri 4 Sep — Close the loop ⚠ MAKE-OR-BREAK

**Goal: both adaptation events fire end to end on real model output.** This is the day the project either has a spine or doesn't.

If Day 2's gate passed, today is buffer — spend it on eval numbers, hardening and the deck rather than new features. That slack is the dividend from having the scaffolding built before Day 1.

- **R2 + R3 (pair all day)** — the monitor/adapt phase. Market drift triggers a re-plan with a stated reason. Then the placement agent: translation, matching, and **rejection patterns feeding back into the plan**.
- **R4** — eval runs against all 6 personas; first real numbers
- **R1 (AM)** — `signals/outcomes.py`: compute the benefit metrics — months saved, wasted training spend avoided, dead paths caught. Run baseline vs. agent across all 6 personas and record the comparison.
- **R1 (from evening)** — **handover point.** Code is done; hand `signals/` to R2 and switch to narrative for the rest of the hackathon. Deck v1 skeleton, all 10 slides.
- **R5** — full timeline visualisation; both adaptation events visible on screen

**Gate — non-negotiable:** the demo timeline shows (a) month-3 market drift → agent kills path A, pivots to B, explains why, and (b) a rejection pattern → agent rewrites positioning.

**If this gate fails, cut scope tomorrow at 09:00.** Go to the cut list. Do not spend Saturday hoping.

---

## Day 4 — Sat 5 Sep — Harden and film

**Feature freeze at 12:00.** No new features after noon, no exceptions. Anything not working by then is cut, not fixed.

- **AM, everyone** — bug bash on the demo path only. Ignore bugs off the happy path.
- **12:00** — freeze.
- **R5 + R1 (PM)** — record the video, running on **Bedrock** so a free-tier rate limit cannot spoil a take. Structure: hook 0:30 → problem 0:30 → solution 0:30 → **demo 2:00** → impact 0:45 → close 0:45. Shoot more takes than you think you need.
- **R2 + R3** — README: how to run, what each file does, `.env` for secrets. In-line comments where the methodology shows up in code — judges check that the presented method is visible at code level. Regenerate the pinned requirements once dependencies have settled:
  ```bash
  uv export --no-hashes --no-dev -o requirements.txt
  ```
  `requirements.txt` is a named deliverable (24 Aug deck p32), not a nicety — judges are told to look for it.
- **R4** — final eval numbers, run on **Bedrock** → hand to R1 for the benefits slide. Record the token counts from `report_usage()` while you are there; that is the cost-per-candidate figure for the Technical Quality slide.
- **R1** — deck v2 with real screenshots, real eval numbers, and the baseline comparison on the benefits slide

**Gate:** raw footage captured; repo runs clean from a fresh clone.

---

## Day 5 — Sun 6 Sep — Polish, rehearse, package

- **R5** — edit video to under 5:00 with captions. Export, watch it end to end, check the audio.
- **R1** — deck final. One core message per slide. Every slide tied to a judging criterion.
- **R1 + team** — rehearse twice, timed. Then rehearse the Q&A below.
- **R2/R3/R4** — **fresh-clone test on a machine that has never run this project.** New venv, new `.env`. This is where submissions die.
- **Everyone, evening** — assemble the package, check it's under 5 GB, confirm no secrets committed (`git log -p | grep -i key`), and dry-run the upload path.

**Gate:** the three deliverables sit in one folder, complete.

---

## Mon 7 Sep — Submit

Submit in the **morning**. One submission only, so treat the afternoon as insurance against upload failure, not as extra polish time. Re-read the deliverable checklist before you press send.

---

## Daily rhythm

- **09:00 standup, 15 min** — what shipped, what's blocked, what's at risk
- **21:00 checkpoint, 20 min** — demo working code to each other, then decide if tomorrow's gate is still reachable

Anyone blocked for more than 90 minutes says so at once. Silent blockage is the main way a 5-day build fails.

---

## Cut list — agree this now, use it without debate

Descope in this order. Pre-agreeing it means you cut the right thing at 2am instead of the thing someone is attached to.

1. Real course-catalogue integration → hardcode a plausible plan object
2. Multiple candidate personas in the demo → one persona, told well
3. Live job data → synthetic snapshot (do this from the start anyway)
4. Interview-prep sub-agent → mention on the roadmap slide
5. AgentCore deployment → run locally, show the architecture slide
6. Polished UI → clean terminal output with a readable trace

**Never cut:** the two adaptation events, the eval numbers, the video.

---

## Risks

| Risk | Mitigation |
|---|---|
| Adaptation isn't visible in 5 min | Replay clock built Day 1; two dated events on screen |
| Video left to the last day | Filmed Day 4, edited Day 5 |
| Only works on one laptop | Fresh-clone test Day 5 |
| Evidence reads as assumption | Every claim carries a named source and date; insight backed by published first-person accounts |
| ~~Integration collapses at the end~~ | Retired — the pipe was connected before Day 1 and every stub swaps out behind a fixed interface |
| One submission burned early | Nobody uploads until the Day 5 gate passes |
| Bedrock access not granted when we need it | R1 enables it and makes one real call on Tue 1 Sep, four days before it matters |
| Provider hardcoded, credits unusable | Day 1 rule: sub-agents call `_common.chat_model()`, never `ChatGroq` |
| Deck rushed because R1 coded too long | Handover is fixed at Day 3 evening and does not move |

---

## Q&A to rehearse

- *"Isn't this LinkedIn?"* — LinkedIn matches you to jobs you already qualify for today. It doesn't plan a six-month path or notice the path broke.
- *"Isn't this a course recommender?"* — Those are one-shot. Show the re-plan.
- *"How do you know the target role is right?"* — Point at the eval numbers.
- *"What if it's wrong? This is someone's livelihood."* — Calibrated confidence, human confirms every consequential action, never auto-submits an application, and it says out loud when it doesn't know.
- *"Where does the job data come from?"* — Synthetic replay, stated plainly.
- *"Did you speak to any of these people?"* — Answer honestly: we worked from published accounts and labour market data, and name them. Do not bluff this one.

---

## Submission checklist

- [ ] Project files — README with run instructions, `requirements.txt`, `.env.example`, no secrets committed
- [ ] Deck — 10 slides or fewer
- [ ] Video — under 5:00, captions, audio checked
- [ ] Fresh-clone test passed on a clean machine
- [ ] Package under 5 GB
- [ ] Submitted Monday morning

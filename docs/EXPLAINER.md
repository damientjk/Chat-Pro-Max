# What this project is, in plain English

*Written for people who have never written a line of code. No technical background assumed. If you hit a word that seems like jargon, it should be explained in the sentence next to it — if it isn't, that's our mistake, not yours.*

---

## The person we built this for

Imagine someone who is 45 years old. They have spent nineteen years in warehouse and logistics operations — scheduling incoming shipments, chasing delivery companies when things went wrong, reconciling stock figures every month. They were good at it. In July, they were retrenched.

Now they are told to "reskill." So they go and look at the available courses, and they face a genuinely hard question that nobody helps them answer:

**Which course? Training for what job, exactly? And how do they know that job will still be hiring in six months, when the course finishes?**

That last part is the one everybody skips. Courses take months. Job markets move faster than courses do. It is entirely possible — common, even — to spend six months and a few thousand dollars training for a role that stopped hiring while you were studying for it. You find out at the end, when you start applying and nothing comes back.

That is the problem this project attacks.

---

## What we are building

A piece of software that acts like a career advisor who is unusually thorough, and — crucially — **who keeps paying attention after giving the advice**.

It does five things:

1. **Works out what the person can already do.** Not their job title. What they can *actually* do, and the line in their history that proves it. "Managed carrier SLAs" isn't a job title — it's evidence that this person can handle vendor contracts and negotiate with suppliers under pressure. Job titles hide capability. We dig for the capability.

2. **Picks a realistic destination — and says what is unrealistic.** It suggests roles that are genuinely reachable from where the person stands, with an honest price tag and time estimate. It will also say *"not this one, not in six months, not from here."* That refusal is deliberate. It is the advice nobody gives, and it is what protects someone's savings and their retraining credits.

3. **Builds a training plan** — a sequence of steps aimed at the specific gaps between what they have and what the target job needs.

4. **Watches the job market every week and changes the plan when it needs to.** This is the heart of it. More below.

5. **Helps them actually apply** — rewriting their experience in the new field's vocabulary — and then **treats every rejection as information rather than as a dead end.**

---

## The one thing that makes it different

Here is the sentence the team uses to explain the project in a single breath:

> **A recommender can suggest a course. It cannot notice in month three that the role you're training for stopped hiring — and rebuild the plan around what's still open.**

Recommendation tools — the kind that suggest a course, a job, a film — give you an answer once and then stop. They have no memory of having advised you and no awareness of what happened next. If the world changes, that is your problem to discover.

This system stays in the loop for the whole six months. It notices things and it responds. Two moments in particular.

### Moment one: the target job stops hiring

Around month three, the number of job openings for the target role collapses — from 120 postings a week down to 14. A recommendation tool would never see this, because it stopped paying attention the day it made its suggestion.

Our system notices, and it does something about it: it **abandons that target and picks a different one that is still hiring** — deliberately choosing a role where the training already completed still counts. It's a pivot, not a restart. And it states the reason out loud, so the person understands what happened and why, rather than being handed a new plan with no explanation.

### Moment two: the applications keep failing the same way

Later, the person starts applying and gets rejected three times in a row. Here's the important detail: **all three rejections happened at the same point** — the initial CV screen. Nobody ever spoke to them.

That pattern is a diagnosis. Being rejected after a technical interview means the skills aren't there yet. Being rejected before anyone has a conversation with you means **the skills may well be there, but the CV isn't communicating them**. Different problem, different fix.

So the system rewrites how the person is presented — same experience, described in the language the new industry actually uses — and tries again. The next application produces an offer.

Both of those moments are visible on screen in the demo. They are the product. Everything else is scaffolding around them.

---

## What it looks like when it runs

Today the whole six-month story is simulated and compressed into a couple of seconds of output. Each line is one week:

```
  wk  0      found 3 capabilities
  wk  0      target: Supply Chain Data Analyst
  wk  0      2-step plan to Supply Chain Data Analyst
  wk 10  !!  Supply Chain Data Analyst postings fell to 14
            because below the floor we set for a viable target
  wk 10  ->  switched to Logistics Systems Analyst
            because still hiring, and reuses the SQL work already done
  wk 18      3 applications sent
  wk 19  ->  rewrote how we describe their experience
            because the last 3 applications all died at resume screening
  wk 20  **  offer: Logistics Systems Analyst
```

Read it top to bottom and it's a story. Week 0: work out what they can do, pick a target, make a plan. Week 10: that target collapses, so switch. Week 18: start applying. Week 19: the applications are failing in a specific way, so fix that specific thing. Week 20: offer.

Notice that every significant decision has a **because** line under it. That is a deliberate design rule, not a nicety. This system is making consequential recommendations about someone's livelihood — if it cannot say why it did something, it has no business doing it.

---

## Two things that surprise people

**The job market in the demo is invented.** Not scraped from a real jobs website — written by us. This sounds like cheating and isn't. A demo has to do the same thing every single time it's run, including during a recorded video and in front of judges. Real job listings change hourly, so the dramatic month-three collapse might simply not happen during the two minutes that matter. So we built a controlled replay of a market — realistic in shape, but scripted, so the moment we need to demonstrate arrives on cue, every time. The team says so openly rather than implying the data is live.

**We are also building a deliberately worse version of our own product.** One of the five people is building a "dumb" version: it picks a course on day one and never looks again — exactly what today's tools do. Then we run both against the same six people and compare.

That gives us something much stronger than a claim. It gives us a measurement: *the naive version left N out of 6 people training for jobs that had closed by month three; ours caught every one.* It is also the honest answer to the question someone will inevitably ask — *"isn't this just a recommender?"* — and that answer lands far harder coming from a team that built the recommender themselves and measured it losing.

---

## What this is for

This is an entry in SimplifyNext's IGNITE Agentic AI Hackathon. Teams were given a deliberately open brief — build something that helps people through a period of change, and that *"plans, acts, and adapts over time"* rather than answering once and stopping. Each team picks its own problem and decides who it serves. This team picked mid-career retrenchment.

Three things get handed in: the working software, a slide deck of ten slides or fewer, and a demo video of five minutes or less.

Judging is five things, **weighted equally at 20% each**:

| What the judges score | In plain terms |
|---|---|
| **Benefits** | Does it actually make someone's life better, and can you show it? |
| **Originality** | Is this genuinely different from what already exists? |
| **Effectiveness** | Does it really solve the problem, or only part of it? |
| **Technical quality** | Does the thing work, and is it well built? |
| **Presentation** | Can the team explain it clearly in the room? |

That table explains a lot about how the team is spending its week. **Only one of those five is the code.** A brilliant piece of software that nobody can explain in five minutes scores 20% and loses. So roughly half the effort goes into the software and half into being able to show it, argue for it, and prove it works — which is why one of the five people stops writing code halfway through the week and switches to the story full time.

Each criterion is scored 0, 1 or 2 — and 1 point is described as *"functional prototype with minor work needed for production."* There is no credit for nearly working. That is the reason for the hard rules in the team's plan: no new features after Saturday noon, and a rehearsed list of what gets cut first if time runs out.

---

## Who is doing what

Five people. Each owns a separate part, so nobody is stuck waiting on anybody else.

| | Their part | In plain terms |
|---|---|---|
| **R1** | Baseline, signals, narrative | Builds the deliberately-dumb comparison version, and writes the code that reads *patterns* in rejections — three failures at the CV stage means something different from three failures at the interview stage. Later switches to telling the story: the slides, the argument, presenting on the day. |
| **R2** | The core loop | The dispatcher. Their code runs the week-by-week cycle and decides, each week, what should happen next: keep training, change target, start applying, or stop. They also own the shared vocabulary the other four write against. |
| **R3** | The three specialists | Writes the parts that actually think. One reads a person's history and extracts what they can do; one picks the destination and plans the route; one writes applications and handles rejection. This is where the AI models get used. |
| **R4** | The world, and the report card | Builds the simulated job market — including the month-three collapse — and the six test candidates. Also builds the scoring: running both versions against all six and producing the number that proves ours is better. |
| **R5** | Making it visible | Turns the event log into something a person can look at and immediately understand, then films and edits the demo video. If the adaptation isn't visible on screen with its reason, as far as the audience is concerned it didn't happen. |

### Why the split works

There's one shared file — a kind of dictionary that defines the common vocabulary everyone's code uses. What a "candidate" is. What a "target role" is. What a "rejection" is.

Everyone agrees on that dictionary on day one and then it is **frozen**. Because it's fixed, the five people can build their pieces separately and in parallel, confident the pieces will fit when connected — and they can each swap their own piece out later without breaking anyone else's.

That's why the project already runs end to end today, even though the intelligent parts haven't been written yet. Every one of those parts is currently a placeholder that returns a canned answer. The plumbing is connected first; the intelligence gets filled in behind it, one piece at a time, without anything having to be rewired.

---

## Where it stands right now

- The full six-month cycle **runs today**, start to finish, with both adaptation moments firing.
- Running it now needs a free Groq account and an internet connection, because the thinking parts are real as of Day 2. It ran on any of the five laptops with no account at all while they were still placeholders.
- Over the build week, each person replaces their own placeholder with the real thing. The structure around it doesn't change when they do.

The deadline is **Monday 7 September**, with one submission allowed — no second attempt, so nothing gets uploaded until it is genuinely finished. Semi-finals follow on 9–11 September and the final is on 18 September. The build window is Wednesday to Sunday, and [`PLAN.md`](PLAN.md) has the day-by-day schedule, including which features get cut first if time runs short. Deciding that in advance, calmly, is much better than deciding it at 2am on the Saturday.

**What it costs to run.** The system has to consult an AI model to do its thinking — reading someone's history, choosing a target, writing applications — and that is charged by the amount of text going in and out. Working it out honestly: producing one person's complete six-month plan, including reacting to the market collapse and rewriting their applications, costs **about four cents**. The team uses a free service while building and a paid one for the runs that get recorded and judged, where reliability matters more than saving pennies. That number is worth stating plainly, because "helpful, and costs four cents a head" is a very different proposition from "helpful, in principle, at some unknown price."

---

## The honesty rules

These are constraints the team set on itself, because the subject matter is someone's livelihood and getting it wrong has a real cost:

- **It says when it doesn't know.** Every recommendation carries a confidence level, and that level is shown rather than hidden.
- **It says what isn't achievable.** A tool that only ever tells you good news is not advice.
- **It never applies for a job on someone's behalf without them seeing it first.** A person confirms every consequential action.
- **Nothing is dressed up as real when it isn't.** The job market is synthetic and we say so. There are no real candidates and no real job postings anywhere in this project. Where the team cites evidence about retrenchment, it's from published sources with names and dates — and the team never implies they interviewed anyone, because they didn't.

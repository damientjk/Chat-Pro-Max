# Chat-Pro-Max

Reskilling-to-placement agent hackathon project.

## R1 checkpoint: run locally

In the VS Code terminal:

```bash
cd "/Users/yizhuo/Desktop/Agentic AI/Chat-Pro-Max"
python3 -m unittest discover -s tests -v
python3 -m scripts.r1_demo
```

## R1 build order

1. `src/baseline/naive.py` - one-shot baseline recommender.
2. `src/signals/rejection.py` - repeated-rejection re-plan signal.
3. `src/signals/outcomes.py` - baseline-versus-agent benefit metrics.
4. `src/r1_workflow.py` - typed handoff of R1 evidence to R2.
5. `evidence.md` - source log for claims in the deck.

When R2 publishes `src/contracts.py`, replace the temporary demo classes with
the shared `SkillInventory`, `TargetRole`, and `ApplicationOutcome` types. Do
not change the baseline rule: it selects once and never re-plans.

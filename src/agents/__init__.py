"""Sub-agents. Owner: R3.

Every function here makes a real model call through `_common.structured()` and
returns a structured-output shape from contracts.py. Go through that helper
rather than `chat_model().with_structured_output(...)` — it retries the
malformed tool call that otherwise kills a whole run. **A key is required to run
the graph** — see the Run section in README.md.

None of them talks to a provider directly. That is what keeps LLM_PROVIDER a
one-line switch, and it is the rule to check first when reviewing changes here.
"""

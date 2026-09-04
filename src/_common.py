"""
Shared setup for every lab script: which model, which provider, and the two
helpers (banner, report_usage) that every file prints with.

  ==================================================================
  ONE LINE decides which provider every lab talks to:

      PROVIDER = "groq"      <- Session 1. Free tier, no AWS, no cost.
      PROVIDER = "bedrock"   <- Session 2, Demo A. Same files, same output.

  No lab file below this one mentions a provider. That is deliberate, and
  it is the point of Demo A: the agent you write on Day 1 is the agent that
  runs on Bedrock on Day 2, and the diff is this line.
  ==================================================================

Import this first in each lab file. It does no network I/O on import, and on
the Groq path it never imports boto3 — so Session 1 runs with no AWS anything
installed.
"""

import os
import sys
from pathlib import Path


def _load_dotenv() -> None:
    """Read the repo root's .env into the environment, if it exists.

    `export GROQ_API_KEY=...` lasts until you close the terminal, which is how
    people end up keyless halfway through a session. A .env file at the repo
    root survives new tabs, editor restarts and Windows.

    A real env var always wins — this only fills in what is missing. Deliberately
    hand-rolled rather than pulling in python-dotenv: one less thing to install
    at the start of a session, and it is eight lines.
    """
    path = Path(__file__).resolve().parent.parent / ".env"
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


_load_dotenv()

# The one line. Override without editing the file:  export LLM_PROVIDER=bedrock
PROVIDER = os.environ.get("LLM_PROVIDER", "groq")

# --------------------------------------------------------------------------
# Model ids. Never string-build a model id — copy it from the provider's
# console or a constant like these. At least one Bedrock id in our own tree
# breaks the usual -YYYYMMDD-vN:0 convention, so a "helpful" f-string that
# assembles ids will work for months and then fail on one model.
# --------------------------------------------------------------------------

GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")

# Seconds before a Groq request is abandoned. ChatGroq defaults to None, which
# means no timeout at all: a stalled connection blocks the caller forever, with
# no CPU used and nothing printed. A demo run that hangs indefinitely is worse
# than one that fails, because nobody knows which is happening. The Bedrock path
# below has always set its own timeouts; this is the Groq equivalent.
# The longest successful call observed on this project was 24s.
GROQ_TIMEOUT = float(os.environ.get("GROQ_TIMEOUT", "60"))

# Kept as MODEL_ID because labs 01-08 (Session 2 and take-home) import that name.
MODEL_ID = os.environ.get(
    "BEDROCK_MODEL", "global.anthropic.claude-haiku-4-5-20251001-v1:0"
)
REGION = os.environ.get("AWS_DEFAULT_REGION") or os.environ.get(
    "AWS_REGION", "ap-southeast-1"
)


def model_label() -> str:
    """What to print at the top of a lab, so the trace says what produced it."""
    return f"{PROVIDER}:{GROQ_MODEL if PROVIDER == 'groq' else MODEL_ID}"


# --------------------------------------------------------------------------
# Groq — the Session 1 path.
# --------------------------------------------------------------------------

def require_groq_key() -> None:
    """Exit with a sentence instead of a stack trace if the key is missing."""
    if not os.environ.get("GROQ_API_KEY"):
        sys.exit(
            "No GROQ_API_KEY found.\n\n"
            "  1. Sign in at https://console.groq.com  (free, no card)\n"
            "  2. API Keys -> Create API Key -> copy it NOW (shown once)\n"
            "  3. either:\n"
            "       export GROQ_API_KEY=gsk_...        (this terminal only)\n"
            "     or, better, at the repo root:\n"
            "       cp .env.example .env    then put the key in it\n\n"
            "  The .env file survives new terminal tabs. It is gitignored —\n"
            "  do not commit a key, and do not paste one in the chat."
        )


def groq_client():
    """The raw Groq SDK client. Lab 1 uses this to see the wire format."""
    require_groq_key()
    from groq import Groq

    return Groq()


# --------------------------------------------------------------------------
# Bedrock — the Session 2 path. boto3 is imported inside the functions so the
# Groq path never needs it installed.
# --------------------------------------------------------------------------

def require_aws_credentials() -> None:
    import boto3

    creds = boto3.Session().get_credentials()
    if creds is None or not creds.access_key:
        sys.exit(
            "No AWS credentials found.\n\n"
            "  boto3 looked at: AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY,\n"
            "  ~/.aws/credentials, and any SSO or instance role.\n\n"
            "  Fix with ONE of:\n"
            "    export AWS_ACCESS_KEY_ID=...  AWS_SECRET_ACCESS_KEY=...\n"
            "    aws sso login --profile <your-profile>\n\n"
            f"  Region currently resolves to: {REGION}\n"
            "  Set it with: export AWS_DEFAULT_REGION=ap-southeast-1\n\n"
            "  Session 1 needs none of this. If you are on Day 1, you have\n"
            "  LLM_PROVIDER=bedrock set by mistake — unset it."
        )


# Kept for labs 01-08, which were written against boto3 directly.
def bedrock_runtime():
    import boto3
    from botocore.config import Config

    require_aws_credentials()
    # read_timeout=300 because a long generation blows through the 60s default
    # and fails after you have already paid for the tokens. max_attempts=1 so
    # throttling reaches our own retry logic instead of being retried (and
    # hidden) down at the botocore layer.
    return boto3.client(
        "bedrock-runtime",
        config=Config(
            region_name=REGION,
            read_timeout=300,
            connect_timeout=120,
            retries={"max_attempts": 1},
        ),
    )


# --------------------------------------------------------------------------
# The one factory every LangChain lab calls.
# --------------------------------------------------------------------------

def chat_model(temperature: float = 0.0, **kwargs):
    """A LangChain chat model for whichever provider PROVIDER names.

    Both objects implement the same BaseChatModel interface, which is the
    entire argument for using LangChain at all: .invoke(), .bind_tools(),
    .with_structured_output() work identically on either side of this if.
    """
    if PROVIDER == "groq":
        require_groq_key()
        from langchain_groq import ChatGroq

        # setdefault, so an explicit value from a caller still wins.
        kwargs.setdefault("request_timeout", GROQ_TIMEOUT)
        # The SDK's own retries sit UNDER the timeout, so they multiply it:
        # at the default max_retries=2 a stalled call costs 3 x GROQ_TIMEOUT
        # before it raises. A 219s call was measured that way. One retry is
        # enough to ride out a dropped connection without a four-minute stall.
        kwargs.setdefault("max_retries", 1)
        return ChatGroq(model=GROQ_MODEL, temperature=temperature, **kwargs)

    if PROVIDER == "bedrock":
        from langchain_aws import ChatBedrockConverse

        return ChatBedrockConverse(
            model_id=MODEL_ID,
            client=bedrock_runtime(),
            temperature=temperature,
            **kwargs,
        )

    # Restored: this guard used to live here and was moved into structured()
    # below, where it sits after a return and can never run. Without it a typo
    # in LLM_PROVIDER returns None, and the failure surfaces as
    # `AttributeError: 'NoneType' has no attribute 'with_structured_output'`
    # somewhere else entirely.
    sys.exit(f"Unknown PROVIDER {PROVIDER!r}. Use 'groq' or 'bedrock'.")


def structured(schema, temperature: float = 0.0, attempts: int = 3, **kwargs):
    """A chat model bound to `schema`, that retries a malformed tool call.

    Small models sometimes emit invalid JSON for a structured-output call —
    Groq rejects it with 400 `tool_use_failed` and the whole graph run dies at
    whichever node was unlucky. It is stochastic and length-dependent: with a
    ~800-character positioning to reason about, placement's screening batch
    failed about 2 runs in 5, which is more often than not across a full case.
    A second attempt nearly always parses.

    Use this rather than `chat_model(...).with_structured_output(...)` anywhere
    a failure would take a whole run down with it.

    The retry is deliberately on the broad BadRequestError rather than only the
    tool_use_failed code, because with_retry matches exception TYPES and cannot
    take a predicate. A genuinely bad request — wrong model id, bad schema —
    therefore costs three attempts before it surfaces, with the same error at
    the end. That is a development-time mistake you see immediately; a run that
    dies at week 19 of a recorded demo is not.

    RateLimitError is retried too, and it is a DIFFERENT branch of the SDK's
    exception tree — it descends from APIStatusError, not BadRequestError, so
    listing BadRequestError alone never caught it. The free tier allows 8000
    tokens per minute and a full case spends roughly twice that, so a 429
    partway through is the normal case rather than the unlucky one. The window
    slides, so the wait is short and backing off is all that is needed; a run
    died at week 20 for want of a 1.6-second pause.
    """
    runnable = chat_model(temperature=temperature, **kwargs).with_structured_output(schema)

    if PROVIDER != "groq":
        # Bedrock is the path we run when it matters, and it has not shown this
        # failure. Left unwrapped rather than guessing at its error taxonomy.
        return runnable

    from groq import APIConnectionError, BadRequestError, InternalServerError, RateLimitError

    return runnable.with_retry(
        retry_if_exception_type=(
            BadRequestError,      # 400 tool_use_failed — malformed structured output
            RateLimitError,       # 429 — free-tier TPM, clears on its own
            InternalServerError,  # 5xx — transient on the provider's side
            APIConnectionError,   # the connection dropped before a reply
        ),
        # A rate limit needs a longer, growing pause than a reparse does; the
        # jittered backoff covers both, and attempts is raised to match because
        # the first two retries of a 429 can still land inside the same window.
        wait_exponential_jitter=True,
        exponential_jitter_params={"initial": 2, "max": 30},
        stop_after_attempt=max(attempts, 5),
    )


# --------------------------------------------------------------------------
# Printing.
# --------------------------------------------------------------------------

def report_usage(label: str, usage) -> None:
    """Print token usage from any of the three shapes the labs encounter.

    Measure from day one. It is the only cost number that means anything for
    YOUR workload — multiply by the rate on the provider's pricing page, and
    do not trust a number in someone's comment (including this one).

      raw Groq / OpenAI-compatible   usage.prompt_tokens / .completion_tokens
      raw Bedrock                    inputTokens / outputTokens
      LangChain usage_metadata       input_tokens / output_tokens
    """
    if usage is None:
        return
    if not isinstance(usage, dict):                     # the raw Groq object
        usage = getattr(usage, "model_dump", lambda: vars(usage))()

    def pick(*names):
        for n in names:
            if usage.get(n):
                return usage[n]
        return 0

    inp = pick("input_tokens", "inputTokens", "prompt_tokens")
    out = pick("output_tokens", "outputTokens", "completion_tokens")
    cr = pick("cache_read_input_tokens")
    cc = pick("cache_creation_input_tokens")
    extra = f"  cache_read={cr} cache_write={cc}" if (cr or cc) else ""
    print(f"  [{label}] input={inp} output={out} total={inp + out}{extra}")


def banner(title: str) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")

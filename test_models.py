"""Stage 1 probe: can each candidate model drive a tool call through its provider?

This checks connectivity + function-calling for every (provider, model) we plan
to assign to a committee seat -- WITHOUT Band or the committee running. Each model
gets one tiny FORCED tool call; we verify it comes back well-formed with a string
argument. That isolates the model-level risks (bad id, no tool support, object-
instead-of-string args, params the model rejects) in seconds, for a fraction of a
cent, before we wire anything into prompts.py.

Run from the quorum/ folder:
    uv run python test_models.py

Note: this uses a plain .invoke() (non-streaming). Band runs models under
streaming, so Stage 2/3 (the real meeting) is what confirms behavior under load.
"""

import os
import time

from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

load_dotenv()

# provider -> (base_url, api_key), straight from .env. PROVIDER_OVERRIDE is
# intentionally ignored here -- we want to test these exact models.
PROVIDERS = {
    "aiml": (
        os.getenv("AIML_BASE_URL", "https://api.aimlapi.com/v1"),
        os.getenv("AIML_API_KEY", ""),
    ),
    "featherless": (
        os.getenv("FEATHERLESS_BASE_URL", "https://api.featherless.ai/v1"),
        os.getenv("FEATHERLESS_API_KEY", ""),
    ),
}

# (seat, provider, model) -- the frontier mapping we want to verify.
# Research stays on Featherless's confirmed Qwen2.5-72B (qwen3.7-max is an AI/ML
# id, not necessarily hosted by Featherless -- we'd check their catalog to upgrade).
CANDIDATES = [
    ("portfolio_manager",  "aiml",        "gpt-5.2-chat-latest"),
    ("bull_analyst",       "aiml",        "deepseek-v4-pro"),
    ("bear_analyst",       "aiml",        "x-ai/grok-4-3"),
    ("risk_officer",       "aiml",        "o3-2025-04-16"),
    ("chief_risk_officer", "aiml",        "gemini-2.5-pro"),
    ("research_analyst",   "featherless", "Qwen/Qwen2.5-72B-Instruct"),
]


@tool
def submit(text: str) -> str:
    """Submit a single short string. Call this with the word OK."""
    return text


PROMPT = "Call the submit tool with the word OK. Do not reply with plain text."


def probe(provider: str, model: str) -> tuple[str, str]:
    """Return (status, detail). status is 'PASS' or 'FAIL'."""
    base_url, api_key = PROVIDERS[provider]
    if not api_key:
        return "FAIL", f"no API key for provider '{provider}' in .env"

    def make(temp):
        # Mirrors committee.py's client. temperature=0.3 matches the real agents;
        # some reasoning models only allow the default, so we retry without it.
        # timeout so a hanging model reports FAIL instead of freezing the run;
        # max_retries=0 so we see the first error immediately (no silent retries).
        kwargs = dict(model=model, api_key=api_key, base_url=base_url,
                      timeout=30, max_retries=0)
        if temp is not None:
            kwargs["temperature"] = temp
        return ChatOpenAI(**kwargs).bind_tools([submit])

    for temp in (0.3, None):
        try:
            resp = make(temp).invoke(PROMPT)
        except Exception as e:  # noqa: BLE001 -- we want the message, whatever it is
            msg = str(e).splitlines()[0][:160]
            if temp == 0.3 and ("temperature" in msg.lower() or "unsupported" in msg.lower()):
                continue  # likely a temperature restriction -> retry on default
            return "FAIL", msg

        calls = getattr(resp, "tool_calls", None) or []
        if not calls:
            return "FAIL", "no tool call returned (model answered with text)"
        arg = calls[0].get("args", {}).get("text")
        if not isinstance(arg, str):
            return "FAIL", f"tool arg not a string: got {type(arg).__name__}"
        suffix = "" if temp == 0.3 else "  [needs default temperature]"
        return "PASS", f"arg={arg!r}{suffix}"

    return "FAIL", "exhausted attempts"


def main() -> None:
    header = f"{'SEAT':20} {'PROVIDER':12} {'MODEL':26} {'STATUS':6} {'TIME':>6}  DETAIL"
    print(header)
    print("-" * len(header))
    passed = 0
    for seat, provider, model in CANDIDATES:
        t0 = time.time()
        status, detail = probe(provider, model)
        dt = time.time() - t0
        passed += status == "PASS"
        print(f"{seat:20} {provider:12} {model:26} {status:6} {dt:5.1f}s  {detail}")
    print("-" * len(header))
    print(f"{passed}/{len(CANDIDATES)} passed")


if __name__ == "__main__":
    main()

"""Run one Quorum committee member as a Band agent.

Usage:
    uv run python committee.py portfolio_manager
    uv run python committee.py research_analyst
    ... (any role key from prompts.ROLES)

Each role needs its Band credentials in agent_config.yaml under the same key.
Set PROVIDER_OVERRIDE=groq in .env to smoke-test every agent on the free Groq
key before spending sponsor credits.
"""

import asyncio
import logging
import os
import sys

from dotenv import load_dotenv

from band import Agent
from band.config import load_agent_config
from prompts import ROLES

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("quorum")

PROVIDERS = {
    "aiml": {
        "base_url_env": ("AIML_BASE_URL", "https://api.aimlapi.com/v1"),
        "model_env": ("AIML_MODEL", "gpt-4o"),
        "key_env": "AIML_API_KEY",
    },
    "featherless": {
        "base_url_env": ("FEATHERLESS_BASE_URL", "https://api.featherless.ai/v1"),
        "model_env": ("FEATHERLESS_MODEL", "Qwen/Qwen2.5-72B-Instruct"),
        "key_env": "FEATHERLESS_API_KEY",
    },
    "groq": {
        "base_url_env": ("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
        "model_env": ("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "key_env": "GROQ_API_KEY",
    },
}


def provider_config(provider: str, role_model: str | None = None) -> tuple[str, str, str]:
    """Resolve (base_url, model, api_key) for a provider, honoring PROVIDER_OVERRIDE.

    role_model: per-role model id from prompts.ROLES — applied only when no
    PROVIDER_OVERRIDE is active (override providers won't host the same ids).
    """
    override = os.getenv("PROVIDER_OVERRIDE", "").strip().lower()
    if override:
        # Any override forces a uniform, cheap test: every seat drops its per-role
        # frontier model and uses the override provider's default (e.g.
        # AIML_MODEL=gpt-4o-mini). Set PROVIDER_OVERRIDE empty for the real run.
        role_model = None
        provider = override
    spec = PROVIDERS[provider]
    base_url = os.getenv(*spec["base_url_env"])
    model = role_model or os.getenv(*spec["model_env"])
    api_key = os.getenv(spec["key_env"], "")
    if not api_key:
        raise SystemExit(
            f"{spec['key_env']} is empty in .env (role wants provider '{provider}'). "
            "Add the key, or set PROVIDER_OVERRIDE=groq to smoke-test."
        )
    return base_url, model, api_key


def build_adapter(role_key: str):
    spec = ROLES[role_key]
    base_url, model, api_key = provider_config(spec["provider"], spec.get("model"))

    additional_tools = []
    if spec.get("company_data_tool"):
        from company_data import get_company_data
        additional_tools.append(get_company_data)

    if spec["framework"] == "pydantic_ai":
        # Cross-framework member: runs on Pydantic AI while the rest use LangGraph.
        from band.adapters import PydanticAIAdapter
        from pydantic_ai.providers.openai import OpenAIProvider
        try:
            from pydantic_ai.models.openai import OpenAIChatModel as _OpenAIModel
        except ImportError:  # older pydantic-ai naming
            from pydantic_ai.models.openai import OpenAIModel as _OpenAIModel

        pyd_model = _OpenAIModel(model, provider=OpenAIProvider(base_url=base_url, api_key=api_key))
        return PydanticAIAdapter(model=pyd_model, custom_section=spec["prompt"])

    from langchain_openai import ChatOpenAI
    from langgraph.checkpoint.memory import InMemorySaver

    from reliable_adapter import ReliableLangGraphAdapter

    # temperature: per-role override via spec["temperature"]. Default 0.3 for
    # determinism; None -> omit entirely (some models, e.g. claude-opus-4-8 on
    # AI/ML, reject a custom temperature).
    temperature = spec.get("temperature", 0.3)
    llm_kwargs = dict(model=model, api_key=api_key, base_url=base_url)
    if temperature is not None:
        llm_kwargs["temperature"] = temperature
    llm = ChatOpenAI(**llm_kwargs)
    return ReliableLangGraphAdapter(
        llm=llm,
        checkpointer=InMemorySaver(),
        custom_section=spec["prompt"],
        additional_tools=additional_tools,
    )


async def main() -> None:
    load_dotenv()
    if len(sys.argv) != 2 or sys.argv[1] not in ROLES:
        raise SystemExit(f"Usage: python committee.py <role>\nRoles: {', '.join(ROLES)}")
    role_key = sys.argv[1]

    agent_id, api_key = load_agent_config(role_key)
    agent = Agent.create(adapter=build_adapter(role_key), agent_id=agent_id, api_key=api_key)

    logger.info("Starting %s (%s)... Ctrl+C to stop.", ROLES[role_key]["name"], role_key)
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())

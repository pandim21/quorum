"""Run the WHOLE committee in ONE process (all 10 agents, concurrently).

The live demo spawns this once per evaluation with the visitor's AI/ML key in the
environment, so every LLM call is billed to THEM — your AI/ML credits are never
touched. Featherless (Research) and the Band agent tokens stay on your keys
(Featherless is flat-rate; Band is free via the hackathon).

Writes live/ready when every agent is connected, so the orchestrator knows it can
convene. Env it expects: AIML_API_KEY (visitor), FEATHERLESS_API_KEY + Band agent
creds (yours), all already wired through committee.build_adapter / agent_config.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from dotenv import load_dotenv

from band import Agent
from band.config import load_agent_config
from committee import build_adapter
from prompts import ROLES

READY = Path(__file__).parent / "live" / "ready"


async def main() -> None:
    load_dotenv()
    READY.parent.mkdir(exist_ok=True)
    READY.unlink(missing_ok=True)

    agents = []
    for role in ROLES:
        agent_id, api_key = load_agent_config(role)
        agents.append(Agent.create(adapter=build_adapter(role), agent_id=agent_id, api_key=api_key))

    for a in agents:  # connect each agent's WebSocket before we signal readiness
        await a.start()
    READY.write_text("ready")

    try:
        await asyncio.gather(*[a.run_forever() for a in agents])
    finally:
        READY.unlink(missing_ok=True)
        for a in agents:
            await a.stop(timeout=5)


if __name__ == "__main__":
    asyncio.run(main())

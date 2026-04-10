"""Configure the OpenAI Agents SDK default client (shared by chat and one-shot agents)."""

from __future__ import annotations

from app.core.config import settings
from app.llm._sdk import async_openai_client

_agents_sdk_client_configured = False


def ensure_agents_openai_configured() -> None:
    """Point the Agents SDK at the same AsyncOpenAI client as the rest of the app."""
    global _agents_sdk_client_configured
    if _agents_sdk_client_configured or not settings.openai.api_key:
        return
    from agents import set_default_openai_client

    set_default_openai_client(async_openai_client(), use_for_tracing=False)
    _agents_sdk_client_configured = True


# Small cap for structured one-shot agents (no tool loops).
ONE_SHOT_AGENT_MAX_TURNS = 5

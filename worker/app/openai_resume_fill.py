from __future__ import annotations

import copy
import json
from typing import Any

import structlog
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

log = structlog.get_logger()


def _client() -> AsyncOpenAI:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return AsyncOpenAI(api_key=settings.openai_api_key)


def _schema_for_api(schema: dict[str, Any]) -> dict[str, Any]:
    """OpenAI structured outputs reject some meta keys."""
    s = copy.deepcopy(schema)
    s.pop("$schema", None)
    return s


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=1, max=8))
async def generate_resume_fill_json(
    *,
    schema: dict[str, Any],
    resume_context: str,
    job_description_context: str | None,
) -> dict[str, Any]:
    """
    Chat Completions + Structured Outputs (json_schema) per OpenAI docs.
    """
    client = _client()
    api_schema = _schema_for_api(schema)
    user_parts: list[str] = [
        "Produce resume content as JSON matching the given schema exactly.",
        "Use professional, ATS-friendly wording.",
    ]
    if resume_context.strip():
        user_parts.append("--- Existing resume / profile data (may be partial) ---\n" + resume_context)
    if job_description_context and job_description_context.strip():
        user_parts.append("--- Target job description ---\n" + job_description_context)
    user_parts.append(
        "Return only JSON that validates against the schema (no markdown, no commentary)."
    )
    user_message = "\n\n".join(user_parts)

    completion = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {
                "role": "system",
                "content": "You fill resume templates with structured JSON only.",
            },
            {"role": "user", "content": user_message},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "resume_fill",
                "strict": True,
                "schema": api_schema,
            },
        },
    )
    choice = completion.choices[0].message.content
    if not choice:
        raise RuntimeError("OpenAI returned empty completion")

    try:
        return json.loads(choice)
    except json.JSONDecodeError as e:
        log.error("openai_json_parse_failed", content=choice[:500])
        raise RuntimeError("OpenAI returned non-JSON content") from e

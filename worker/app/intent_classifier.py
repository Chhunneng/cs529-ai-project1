from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings


IntentLabel = Literal[
    "job_description",
    "tailor_resume",
    "improve_resume",
    "score_resume",
    "generic_chat",
]


@dataclass(frozen=True)
class IntentResult:
    intent: IntentLabel
    confidence: float
    rationale: str


def _client() -> AsyncOpenAI:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return AsyncOpenAI(api_key=settings.openai_api_key)


_INTENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "intent": {
            "type": "string",
            "enum": [
                "job_description",
                "tailor_resume",
                "improve_resume",
                "score_resume",
                "generic_chat",
            ],
        },
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "rationale": {"type": "string"},
    },
    "required": ["intent", "confidence", "rationale"],
}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=1, max=8))
async def classify_intent(*, user_text: str) -> IntentResult:
    """
    Phase 1: small LLM-based intent classifier.

    Output is strict JSON so downstream routing is deterministic.
    """
    client = _client()
    resp = await client.responses.create(
        model=settings.openai_model,
        input=[
            {
                "role": "system",
                "content": (
                    "Classify the user's message into a single intent for a resume assistant.\n"
                    "Return JSON only, matching the provided schema."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Decide the intent.\n\n"
                    "Guidelines:\n"
                    "- job_description: the message is primarily a pasted job description.\n"
                    "- tailor_resume: user asks to tailor to a JD.\n"
                    "- improve_resume: user asks for improvements/rewrites.\n"
                    "- score_resume: user asks for a score/ATS score.\n"
                    "- generic_chat: everything else.\n\n"
                    f"User message:\n{user_text}"
                ),
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "intent",
                "strict": True,
                "schema": _INTENT_SCHEMA,
            }
        },
    )

    raw = getattr(resp, "output_text", None) or ""
    if not raw.strip():
        return IntentResult(intent="generic_chat", confidence=0.0, rationale="empty_model_output")

    data = json.loads(raw)
    intent = data.get("intent") or "generic_chat"
    confidence = float(data.get("confidence") or 0.0)
    rationale = str(data.get("rationale") or "")
    return IntentResult(intent=intent, confidence=confidence, rationale=rationale)


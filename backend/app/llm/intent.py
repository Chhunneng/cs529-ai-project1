from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from agents import Agent, Runner
from pydantic import BaseModel, ConfigDict, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.llm.agents_bootstrap import ONESHOT_AGENT_MAX_TURNS, ensure_agents_openai_configured

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


class IntentClassification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: Literal[
        "job_description",
        "tailor_resume",
        "improve_resume",
        "score_resume",
        "generic_chat",
    ]
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str


_INTENT_INSTRUCTIONS = (
    "Classify the user's message into a single intent for a resume assistant. "
    "Return only the structured output fields."
)


def _intent_agent() -> Agent[Any]:
    return Agent[Any](
        name="IntentClassifier",
        instructions=_INTENT_INSTRUCTIONS,
        model=settings.openai.model,
        output_type=IntentClassification,
        tools=[],
    )


def _user_message_for_intent(user_text: str) -> str:
    return "\n\n".join(
        [
            "Decide the intent.",
            "",
            "Guidelines:",
            "- job_description: the message is primarily a pasted job description.",
            "- tailor_resume: user asks to tailor to a JD.",
            "- improve_resume: user asks for improvements/rewrites.",
            "- score_resume: user asks for a score/ATS score.",
            "- generic_chat: everything else.",
            "",
            f"User message:\n{user_text}",
        ]
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=1, max=8))
async def classify_intent(*, user_text: str) -> IntentResult:
    ensure_agents_openai_configured()
    result = await Runner.run(
        _intent_agent(),
        _user_message_for_intent(user_text),
        context=None,
        session=None,
        max_turns=ONESHOT_AGENT_MAX_TURNS,
    )
    final = result.final_output
    if isinstance(final, IntentClassification):
        return IntentResult(
            intent=final.intent,
            confidence=final.confidence,
            rationale=final.rationale,
        )
    return IntentResult(intent="generic_chat", confidence=0.0, rationale="unexpected_model_output")

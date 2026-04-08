from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.openai._sdk import async_openai_client

log = structlog.get_logger()


@dataclass(frozen=True)
class ResumeScopeResult:
    is_related_to_resume_job: bool
    reason: str
    response_id: str | None


_SCOPE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "is_related_to_resume_job": {"type": "boolean"},
        "reason": {"type": "string"},
    },
    "required": ["is_related_to_resume_job", "reason"],
}

_SCOPE_SYSTEM = (
    "You are a scope checker for a resume and job-description assistant.\n"
    "Answer ONLY in JSON matching the provided schema.\n"
    "Return is_related_to_resume_job=true for: editing a resume (including name/contact/header), "
    "job descriptions, tailoring, ATS tips, interview prep tied to a job, and short follow-ups "
    "that continue those tasks.\n"
    "Return false for unrelated chit-chat, unrelated coding/homework, or anything not about "
    "resume/JD/career documents.\n"
    "When uncertain, prefer true if the message could reasonably be a continuation of resume work."
)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=1, max=8))
async def check_resume_scope(
    *,
    user_text: str,
    previous_response_id: str | None,
) -> ResumeScopeResult:
    client = async_openai_client()
    kwargs: dict[str, Any] = {
        "model": settings.openai.model,
        "input": [
            {"role": "system", "content": _SCOPE_SYSTEM},
            {"role": "user", "content": f"User message:\n{user_text}"},
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "resume_scope",
                "strict": True,
                "schema": _SCOPE_SCHEMA,
            }
        },
    }
    if previous_response_id:
        kwargs["previous_response_id"] = previous_response_id

    resp = await client.responses.create(**kwargs)
    raw = getattr(resp, "output_text", None) or ""
    response_id = getattr(resp, "id", None)
    if not raw.strip():
        log.warning("resume_scope_empty_output")
        return ResumeScopeResult(
            is_related_to_resume_job=True,
            reason="empty_model_output_default_allow",
            response_id=str(response_id) if response_id else None,
        )
    data = json.loads(raw)
    return ResumeScopeResult(
        is_related_to_resume_job=bool(data.get("is_related_to_resume_job")),
        reason=str(data.get("reason") or ""),
        response_id=str(response_id) if response_id else None,
    )


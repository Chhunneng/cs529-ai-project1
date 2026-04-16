"""Crew execution for interview generate/refine (shared by HTTP API and Redis consumer)."""

from __future__ import annotations

import json
import re
from typing import Any, Literal

from fastapi import HTTPException
from pydantic import BaseModel, Field, model_validator

from app.generate_crew.crew import InterviewGenerateCrew
from app.refine_crew.crew import InterviewRefineCrew

InterviewSource = Literal["jd", "resume", "both"]
InterviewQuestionStyle = Literal["random", "technical", "behavioral", "domain", "language", "other"]
InterviewQuestionLevel = Literal["random", "easy", "medium", "hard"]


class GenerateBody(BaseModel):
    source: InterviewSource
    count: int = Field(default=8, ge=1, le=25)
    job_description_text: str | None = None
    resume_text: str | None = None
    question_style: InterviewQuestionStyle = "random"
    level: InterviewQuestionLevel = "random"
    focus_detail: str | None = None

    @model_validator(mode="after")
    def _require_focus_detail(self) -> GenerateBody:
        if self.question_style in ("domain", "language", "other"):
            if not (self.focus_detail or "").strip():
                raise ValueError("focus_detail is required when question_style is domain, language, or other")
        return self


class RefineBody(BaseModel):
    question: str
    ideal_answer: str
    user_answer: str


def _enforce_style_and_level(
    meta: dict[str, Any],
    *,
    question_style: str,
    level: str,
    focus_detail: str,
) -> None:
    if question_style == "technical":
        meta["type"] = "technical"
    elif question_style == "behavioral":
        meta["type"] = "behavioral"
    elif question_style == "random":
        pass
    else:
        meta.setdefault("type", "mixed")

    if level in ("easy", "medium", "hard"):
        meta["difficulty"] = level

    if question_style in ("domain", "language", "other") and focus_detail:
        meta.setdefault("focus", focus_detail.strip())


def _extract_json(text: str) -> Any:
    text = text.strip()
    if not text:
        raise ValueError("Empty output")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)
    if match:
        return json.loads(match.group(1))
    match2 = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
    if match2:
        return json.loads(match2.group(1))
    raise ValueError("Could not parse JSON")


def run_generate(body: GenerateBody) -> dict[str, Any]:
    """Run generate crew; returns ``{"questions": [...]}`` or raises."""
    if body.source in ("jd", "both") and not (body.job_description_text or "").strip():
        raise HTTPException(status_code=400, detail="job_description_text is required for source=jd|both")
    if body.source in ("resume", "both") and not (body.resume_text or "").strip():
        raise HTTPException(status_code=400, detail="resume_text is required for source=resume|both")

    focus_detail_stripped = (body.focus_detail or "").strip()
    context = {
        "source": body.source,
        "count": body.count,
        "job_description_text": body.job_description_text or "",
        "resume_text": body.resume_text or "",
        "question_style": body.question_style,
        "level": body.level,
        "focus_detail": focus_detail_stripped,
    }

    result = InterviewGenerateCrew().crew().kickoff(inputs=context)

    try:
        parsed = _extract_json(getattr(result, "raw", str(result)))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Invalid model output: {type(exc).__name__}: {exc}") from exc

    questions = parsed.get("questions") if isinstance(parsed, dict) else None
    if not isinstance(questions, list):
        raise HTTPException(status_code=502, detail="Model output missing questions list")

    cleaned: list[dict[str, Any]] = []
    for item in questions[: body.count]:
        if not isinstance(item, dict):
            continue
        prompt = str(item.get("prompt") or "").strip()
        sample_answer = str(item.get("sample_answer") or "").strip()
        meta = dict(item.get("metadata")) if isinstance(item.get("metadata"), dict) else {}
        if not prompt or not sample_answer:
            continue
        _enforce_style_and_level(
            meta,
            question_style=body.question_style,
            level=body.level,
            focus_detail=focus_detail_stripped,
        )
        cleaned.append({"prompt": prompt, "sample_answer": sample_answer, "metadata": meta})

    if len(cleaned) < 1:
        raise HTTPException(status_code=502, detail="Model output produced no valid questions")

    return {"questions": cleaned}


def run_refine(body: RefineBody) -> dict[str, Any]:
    """Run refine crew; returns feedback payload or raises."""
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="question is required")
    if not body.user_answer.strip():
        raise HTTPException(status_code=400, detail="user_answer is required")

    context = {
        "question": body.question,
        "ideal_answer": body.ideal_answer,
        "user_answer": body.user_answer,
    }

    result = InterviewRefineCrew().crew().kickoff(inputs=context)

    try:
        parsed = _extract_json(getattr(result, "raw", str(result)))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Invalid model output: {type(exc).__name__}: {exc}") from exc

    if not isinstance(parsed, dict):
        raise HTTPException(status_code=502, detail="Model output was not an object")

    feedback = str(parsed.get("feedback") or "").strip()
    refined = str(parsed.get("refined_answer") or "").strip()
    scores = parsed.get("scores") if isinstance(parsed.get("scores"), dict) else {}

    if not feedback or not refined:
        raise HTTPException(status_code=502, detail="Model output missing feedback/refined_answer")

    return {"feedback": feedback, "refined_answer": refined, "scores": scores}

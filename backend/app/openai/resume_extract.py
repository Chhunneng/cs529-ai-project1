from __future__ import annotations

import json
from typing import Any

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.openai._sdk import async_openai_client
from app.openai.resume_fill import _schema_for_api

log = structlog.get_logger()

# Resume profile v1: pattern-agnostic outline rows (depth + text) + contact + summary + sections_flat.
RESUME_PROFILE_V1_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "_schema_version": {"type": "integer"},
        "summary": {"type": "string"},
        "contact": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "value": {"type": "string"},
                },
                "required": ["label", "value"],
                "additionalProperties": False,
            },
        },
        "outline": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "depth": {"type": "integer"},
                    "text": {"type": "string"},
                },
                "required": ["depth", "text"],
                "additionalProperties": False,
            },
        },
        "sections_flat": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["title", "content"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["_schema_version", "summary", "contact", "outline", "sections_flat"],
    "additionalProperties": False,
}


def _truncate_for_model(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n\n[…truncated for model input…]"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=1, max=8))
async def extract_resume_profile_json(*, resume_text: str) -> dict[str, Any]:
    """Stateless Responses API call: only ``input`` messages; no conversation parameter."""
    raw = resume_text.strip()
    if not raw:
        raise ValueError("resume_text is empty")

    truncated = _truncate_for_model(raw, settings.openai.resume_extract_max_input_chars)
    client = async_openai_client()
    api_schema = _schema_for_api(RESUME_PROFILE_V1_SCHEMA)

    user_message = "\n\n".join(
        [
            "Parse the resume plain text into JSON matching the schema exactly. Prioritize clean grouping: "
            "each job, school, or project should read as one unit; do not repeat the same fact on back-to-back rows.",
            "",
            "Contact: label/value pairs only (Name, Location, Phone, Email, LinkedIn, GitHub, etc.). "
            "Values are plain text; keep URLs short without extra prose.",
            "",
            "Summary: at most 3 sentences or ~120 words. If the resume has no summary, use \"\". "
            "Do not paste the entire Experience section into summary.",
            "",
            "Outline: ordered `outline` rows with integer `depth` and string `text`.",
            "depth 0 = section heading only (Experience, Education, Projects, Awards, Skills, …).",
            "depth 1–5 = content under that section. Do not exceed depth 5.",
            "",
            "EXPERIENCE (under an Experience depth-0 heading):",
            "- For each employer/role block, use this pattern so readers see one coherent job:",
            "  • depth 1: ONE line that already includes job title, company, location, and date range, e.g. "
            "\"Software Engineer — Kirirom Digital Inc — Japan — May 2023 – Jan 2026\".",
            "  • Then depth 3 only for bullet achievements (one bullet = one outline row).",
            "- Do NOT add a separate depth-2 row that only repeats the job title if it is already in the depth-1 line.",
            "- If the source resume splits title and company on different lines, you may use depth 1 = company + dates + location "
            "and depth 2 = title, but never duplicate the same title on both rows.",
            "- Each bullet: one accomplishment per row; keep under ~240 characters when possible; preserve key numbers.",
            "",
            "EDUCATION:",
            "- Prefer depth 1 = \"Degree, Field — Institution — years\" on one line when it fits.",
            "- Use depth 2 only for a second line (e.g. honors) when needed. Avoid extra depth for empty structure.",
            "",
            "PROJECTS:",
            "- depth 1 = project name.",
            "- depth 2 = one short description (1–2 sentences), OR depth-3 rows if the resume lists separate bullets.",
            "",
            "AWARDS:",
            "- depth 1 = award name + year.",
            "- depth 2 = at most one short clarifying sentence; do not paste long competition essays.",
            "",
            "SKILLS:",
            "- depth 1 = category name (e.g. Programming Languages).",
            "- depth 2 = one comma-separated line for that category only. Do not split one category across multiple depth-2 rows.",
            "",
            "GLOBAL:",
            "- Follow the resume's section order top-to-bottom.",
            "- Do not invent employers, dates, or metrics; only use what the text supports.",
            "- Avoid noisy rows: every row should add new information.",
            "",
            "sections_flat: [] unless a block truly cannot be represented; then one {title, content} per odd block.",
            "",
            "Use `_schema_version`: 1.",
            "If the text was truncated, work from what is present.",
            "--- Resume text ---",
            truncated,
        ]
    )

    resp = await client.responses.create(
        model=settings.openai.model,
        input=[
            {
                "role": "system",
                "content": (
                    "You extract resume structure into JSON only. No markdown or commentary. "
                    "Fill every required field; use empty string or empty arrays where nothing applies. "
                    "Group related facts together; never repeat the same job title or company line on consecutive rows."
                ),
            },
            {"role": "user", "content": user_message},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "resume_profile_v1",
                "strict": True,
                "schema": api_schema,
            }
        },
    )
    out = getattr(resp, "output_text", None) or ""
    if not out.strip():
        raise RuntimeError("OpenAI returned empty completion")

    try:
        data = json.loads(out)
    except json.JSONDecodeError as e:
        log.error("resume_extract_json_parse_failed", content=out[:500])
        raise RuntimeError("OpenAI returned non-JSON content") from e

    if isinstance(data, dict):
        data.setdefault("_schema_version", 1)
    return data

from __future__ import annotations

from typing import Any

import structlog
from agents import Runner
from tenacity import retry, stop_after_attempt, wait_exponential

from app.llm.agents_bootstrap import ONE_SHOT_AGENT_MAX_TURNS
from backend.app.llm.agents import RESUME_EXTRACT_AGENT
from backend.app.llm.schema import ResumeProfileV1

log = structlog.get_logger()


def _user_message_for_extract(truncated_resume: str) -> str:
    return "\n\n".join(
        [
            "Parse the resume plain text following these rules. Prioritize clean grouping: "
            "each job, school, or project should read as one unit; do not repeat the same fact on back-to-back rows.",
            "",
            "Contact: label/value pairs only (Name, Location, Phone, Email, LinkedIn, GitHub, etc.). "
            "Values are plain text; keep URLs short without extra prose.",
            "",
            'Summary: at most 3 sentences or ~120 words. If the resume has no summary, use "". '
            "Do not paste the entire Experience section into summary.",
            "",
            "Outline: ordered `outline` rows with integer `depth` and string `text`.",
            "depth 0 = section heading only (Experience, Education, Projects, Awards, Skills, …).",
            "depth 1–5 = content under that section. Do not exceed depth 5.",
            "",
            "EXPERIENCE (under an Experience depth-0 heading):",
            "- For each employer/role block, use this pattern so readers see one coherent job:",
            "  • depth 1: ONE line that already includes job title, company, location, and date range, e.g. "
            '"Software Engineer — Company Name Inc — USA — May 2023 – Jan 2026".',
            "  • Then depth 3 only for bullet achievements (one bullet = one outline row).",
            "- Do NOT add a separate depth-2 row that only repeats the job title if it is already in the depth-1 line.",
            "- If the source resume splits title and company on different lines, you may use depth 1 = company + dates + location "
            "and depth 2 = title, but never duplicate the same title on both rows.",
            "- Each bullet: one accomplishment per row; keep under ~240 characters when possible; preserve key numbers.",
            "",
            "EDUCATION:",
            '- Prefer depth 1 = "Degree, Field — Institution — years" on one line when it fits.',
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
            "--- Resume text ---",
            truncated_resume,
        ]
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=1, max=8))
async def extract_resume_profile_json(*, resume_text: str) -> dict[str, Any]:
    """One-shot agent run: structured resume profile, no conversation state."""
    raw = resume_text.strip()
    if not raw:
        raise ValueError("resume_text is empty")

    user_message = _user_message_for_extract(raw)

    result = await Runner.run(
        RESUME_EXTRACT_AGENT,
        user_message,
        max_turns=ONE_SHOT_AGENT_MAX_TURNS,
    )
    final = result.final_output
    if not isinstance(final, ResumeProfileV1):
        log.error("resume_extract_unexpected_output", output_type=type(final).__name__)
        raise RuntimeError("OpenAI agent returned unexpected output type for resume extract")

    data = final.model_dump(by_alias=True)
    if isinstance(data, dict):
        data.setdefault("_schema_version", 1)
    return data

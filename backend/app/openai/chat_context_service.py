from __future__ import annotations

import json
import re
import uuid
from sqlalchemy import select

from app.db.session import AsyncSessionMaker
from app.models.job_description import JobDescription
from app.models.resume import Resume


def _clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


async def load_resume_row(*, resume_id: uuid.UUID) -> Resume | None:
    async with AsyncSessionMaker() as db:
        return await db.get(Resume, resume_id)


async def load_job_description_row(*, session_id: uuid.UUID, jd_id: uuid.UUID) -> JobDescription | None:
    async with AsyncSessionMaker() as db:
        return await db.scalar(
            select(JobDescription).where(
                JobDescription.id == jd_id,
                JobDescription.session_id == session_id,
            )
        )


def resume_source_text(resume: Resume) -> str:
    if resume.parsed_json is not None:
        try:
            return json.dumps(resume.parsed_json, ensure_ascii=False)
        except Exception:
            pass
    return (resume.content_text or "").strip()


def build_resume_overview_text(*, resume: Resume, max_chars: int) -> str:
    """Short, tool-friendly summary: structured hints or start of plain text."""
    parsed = resume.parsed_json
    if isinstance(parsed, dict) and parsed:
        lines: list[str] = []
        summary = parsed.get("summary")
        if isinstance(summary, str) and summary.strip():
            lines.append("Summary (from parsed resume): " + _clip(summary.strip(), 400))
        outline = parsed.get("outline")
        if isinstance(outline, list):
            for row in outline[:25]:
                if not isinstance(row, dict):
                    continue
                depth = row.get("depth")
                text = row.get("text")
                if isinstance(text, str) and text.strip():
                    prefix = "  " * int(depth) if isinstance(depth, int) else "- "
                    lines.append(f"{prefix}{text.strip()}")
        contact = parsed.get("contact")
        if isinstance(contact, list):
            pairs: list[str] = []
            for item in contact[:12]:
                if isinstance(item, dict):
                    lab = item.get("label")
                    val = item.get("value")
                    if isinstance(lab, str) and isinstance(val, str):
                        pairs.append(f"{lab}: {val}")
            if pairs:
                lines.append("Contact: " + "; ".join(pairs))
        body = "\n".join(lines) if lines else json.dumps(parsed, ensure_ascii=False)[:max_chars]
        return _clip(body, max_chars)

    raw = (resume.content_text or "").strip()
    if not raw:
        return "(Resume record exists but has no parseable text yet.)"
    return _clip(raw, max_chars)


def resume_excerpt(*, resume: Resume, start_char: int, length: int, max_length: int) -> str:
    src = resume_source_text(resume)
    if not src:
        return "(No resume text available.)"
    start = max(0, int(start_char))
    take = min(max(1, int(length)), max_length)
    chunk = src[start : start + take]
    if not chunk:
        return f"(No text at offset {start}; resume source length is {len(src)} characters.)"
    header = f"[excerpt start={start} len={len(chunk)} of total {len(src)}]\n"
    return header + chunk


def search_resume_text(
    *,
    resume: Resume,
    needle: str,
    max_matches: int,
    context_chars: int,
    max_scan_chars: int,
) -> str:
    needle_clean = needle.strip()
    if len(needle_clean) < 2:
        return "Search text must be at least 2 characters."
    src = resume_source_text(resume)
    if not src:
        return "(No resume text to search.)"
    scan = src[:max_scan_chars]
    if len(src) > max_scan_chars:
        note = f"(Searched first {max_scan_chars} characters of {len(src)} total.)\n"
    else:
        note = ""
    lower_scan = scan.lower()
    lower_needle = needle_clean.lower()
    spans: list[tuple[int, int]] = []
    pos = 0
    while len(spans) < max_matches:
        idx = lower_scan.find(lower_needle, pos)
        if idx < 0:
            break
        spans.append((idx, idx + len(needle_clean)))
        pos = idx + 1
    if not spans:
        return note + f"No matches for {needle_clean!r}."
    parts: list[str] = []
    for i, (a, b) in enumerate(spans, start=1):
        lo = max(0, a - context_chars)
        hi = min(len(scan), b + context_chars)
        snippet = scan[lo:hi]
        snippet = re.sub(r"\s+", " ", snippet)
        parts.append(f"Match {i} around char {a}: …{snippet}…")
    return note + "\n".join(parts)


async def fetch_job_description_excerpt(
    *, session_id: uuid.UUID, jd_id: uuid.UUID, max_chars: int
) -> str | None:
    jd = await load_job_description_row(session_id=session_id, jd_id=jd_id)
    if jd is None:
        return None
    raw = str(jd.raw_text or "").strip()
    if not raw:
        return "(Job description record is empty.)"
    return _clip(raw, max_chars)

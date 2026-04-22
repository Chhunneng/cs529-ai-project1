from __future__ import annotations

import re
from collections import Counter

from fastmcp import FastMCP

mcp = FastMCP("InterviewTools")

import logging
logging.basicConfig(level=logging.INFO)


_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "for",
    "from",
    "has",
    "have",
    "i",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "we",
    "with",
    "you",
    "your",
}


def _tokens(text: str) -> list[str]:
    raw = re.findall(r"[a-zA-Z][a-zA-Z0-9+.#_-]{1,}", (text or "").lower())
    return [t for t in raw if t not in _STOPWORDS and len(t) >= 2]


@mcp.tool()
def extract_keywords(text: str, max_keywords: int = 20) -> dict:
    """Extract simple keywords from text.

    This is intentionally lightweight and deterministic (no LLM).
    """
    print(">>> MCP TOOL CALLED: extract_keywords")
    logging.info("MCP TOOL CALLED: extract_keywords")
    max_k = max(3, min(int(max_keywords), 60))
    counts = Counter(_tokens(text))
    keywords = [w for w, _ in counts.most_common(max_k)]
    return {"keywords": keywords}


@mcp.tool()
def keyword_alignment(keywords: list[str], answer_text: str) -> dict:
    """Check which keywords appear in the answer."""
    print(">>> MCP TOOL CALLED: keyword_alignment")
    logging.info("MCP TOOL CALLED: keyword_alignment")
    kws = [str(k).strip().lower() for k in (keywords or []) if str(k).strip()]
    kws = list(dict.fromkeys(kws))  # de-dupe, preserve order
    ans = (answer_text or "").lower()
    matched = [k for k in kws if k and k in ans]
    missing = [k for k in kws if k and k not in ans]
    score = 0.0 if not kws else round(len(matched) / len(kws) * 100.0, 1)
    return {"score": score, "matched": matched, "missing": missing}


@mcp.tool()
def answer_rubric_score(question: str, ideal_answer: str, user_answer: str) -> dict:
    """Heuristic rubric score based on overlap with ideal answer keywords."""
    print(">>> MCP TOOL CALLED: answer_rubric_score")
    logging.info("MCP TOOL CALLED: extract_keywords")
    ideal_kws = extract_keywords(ideal_answer, max_keywords=18).get("keywords", [])
    align = keyword_alignment(ideal_kws, user_answer)
    base = float(align.get("score") or 0.0)

    # Small boosts/penalties:
    ua = (user_answer or "").strip()
    if len(ua) < 60:
        base -= 10.0
    if len(ua) > 1200:
        base -= 5.0

    # Clamp 0-100
    score = max(0.0, min(100.0, round(base, 1)))
    return {
        "score": score,
        "reasons": {
            "matched_keywords": align.get("matched", []),
            "missing_keywords": align.get("missing", []),
            "note": "Heuristic score based on ideal-answer keyword overlap and length.",
            "question_hint": (question or "")[:200],
        },
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8080)


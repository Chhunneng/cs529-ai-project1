from __future__ import annotations

import logging
import re
from collections import Counter

from fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)

mcp = FastMCP("InterviewTools")


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


_LABEL_PREFIX_RE = re.compile(
    r"(?im)^\s*(interview\s*question|question|ideal\s*answer|user\s*answer|answer)\s*:\s*"
)

_JUNK_KEYWORDS = {
    # common prompt/metadata leaks
    "ideal",
    "user",
    "answer",
    "question",
    "text",
    "shown",
    "missing",
    "matched",
    "score",
    "reasons",
    "rubric",
    # json/punctuation-ish tokens often leaked into lists
    "json",
    "object",
    "array",
    "dict",
    "list",
}


def _tokens(text: str) -> list[str]:
    raw = re.findall(r"[a-zA-Z][a-zA-Z0-9+.#_-]{1,}", (text or "").lower())
    return [t for t in raw if t not in _STOPWORDS and len(t) >= 2]


def _strip_prompt_labels(text: str) -> str:
    """Remove common leading prompt labels like 'IDEAL ANSWER:' from multi-line text."""
    if not text:
        return ""
    cleaned_lines: list[str] = []
    for line in str(text).splitlines():
        cleaned_lines.append(_LABEL_PREFIX_RE.sub("", line).strip())
    return "\n".join([ln for ln in cleaned_lines if ln])


def _normalize_keywords_input(expected_keywords) -> tuple[list[str], dict]:
    """Coerce messy keyword inputs into a clean keyword list (agent-proofing)."""
    debug: dict = {
        "input_type": type(expected_keywords).__name__,
        "discarded": [],
        "coerced_from_text": False,
    }

    # Allow keyword_alignment to accept either list[str] or a single string blob.
    if expected_keywords is None:
        return [], debug

    kws_raw: list[str]
    if isinstance(expected_keywords, str):
        debug["coerced_from_text"] = True
        kws_raw = _tokens(_strip_prompt_labels(expected_keywords))
    elif isinstance(expected_keywords, (list, tuple, set)):
        kws_raw = []
        for k in expected_keywords:
            if k is None:
                continue
            s = str(k).strip().lower()
            if not s:
                continue
            # If the agent mistakenly passes a long prompt chunk as one "keyword"
            # (e.g., contains spaces/newlines), tokenize it instead of keeping as-is.
            if len(s) > 40 or " " in s or "\n" in s or "\t" in s:
                debug["coerced_from_text"] = True
                kws_raw.extend(_tokens(_strip_prompt_labels(s)))
            else:
                kws_raw.append(s)
    else:
        debug["coerced_from_text"] = True
        kws_raw = _tokens(_strip_prompt_labels(str(expected_keywords)))

    cleaned: list[str] = []
    for k in kws_raw:
        k2 = str(k).strip().lower()
        if not k2 or k2 in _STOPWORDS or len(k2) < 2:
            debug["discarded"].append(k2)
            continue
        if k2 in _JUNK_KEYWORDS:
            debug["discarded"].append(k2)
            continue
        if k2.startswith("{") or k2.endswith("}") or k2.startswith("[") or k2.endswith("]"):
            debug["discarded"].append(k2)
            continue
        cleaned.append(k2)

    # de-dupe, preserve order
    cleaned = list(dict.fromkeys(cleaned))
    return cleaned, debug


@mcp.tool()
def extract_keywords(source_text: str, max_keywords: int = 20) -> dict:
    """Extract simple keywords from a piece of text (deterministic; no LLM).

    What to pass:
    - source_text: ONLY the text you want keywords from (e.g. the IDEAL ANSWER or resume/JD text).
      Do NOT pass the whole prompt template, tool instructions, or JSON wrappers.

    Output:
    - keywords: list[str] (most frequent tokens, lowercased, stopwords removed)
    """
    max_k = max(3, min(int(max_keywords), 60))
    cleaned_text = _strip_prompt_labels(source_text or "")
    counts = Counter(_tokens(cleaned_text))
    keywords = [w for w, _ in counts.most_common(max_k)]
    result = {
        "keywords": keywords,
        "debug": {
            "max_keywords": max_k,
            "source_text_len": len(source_text or ""),
            "cleaned_text_len": len(cleaned_text or ""),
        },
    }
    logging.info(f"MCP TOOL CALLED: extract_keywords, keywords: {keywords}")
    return result


@mcp.tool()
def keyword_alignment(expected_keywords: list[str], user_answer_text: str) -> dict:
    """Check which expected keywords appear in the user's answer.

    What to pass:
    - expected_keywords: the *keywords list returned by extract_keywords*.
      If you don't have that list, call extract_keywords first on the IDEAL ANSWER.
    - user_answer_text: ONLY the user's answer text (no labels like 'USER ANSWER:').
    """
    kws, kw_debug = _normalize_keywords_input(expected_keywords)
    ans_clean = _strip_prompt_labels(user_answer_text or "")
    ans = ans_clean.lower()
    matched = [k for k in kws if k and k in ans]
    missing = [k for k in kws if k and k not in ans]
    score = 0.0 if not kws else round(len(matched) / len(kws) * 100.0, 1)
    result = {
        "score": score,
        "matched": matched,
        "missing": missing,
        "counts": {
            "expected": len(kws),
            "matched": len(matched),
            "missing": len(missing),
        },
        "top_missing_keywords": missing[:10],
        "debug": {
            "answer_len": len(user_answer_text or ""),
            "answer_cleaned_len": len(ans_clean or ""),
            "keywords_normalization": kw_debug,
        },
    }
    logging.info(
        f"MCP TOOL CALLED: keyword_alignment, score: {score}, matched: {matched}, missing: {missing}"
    )
    return result


@mcp.tool()
def answer_rubric_score(question_text: str, ideal_answer_text: str, user_answer_text: str) -> dict:
    """Heuristic rubric score based on overlap with ideal-answer keywords.

    What to pass (important):
    - question_text: the interview question text only
    - ideal_answer_text: the ideal/sample answer text only
    - user_answer_text: the user's answer text only

    Tip:
    - If you already computed keywords with extract_keywords, you can call keyword_alignment directly.
      This tool is the "one-call" version that does both.
    """
    ideal_kw_result = extract_keywords(ideal_answer_text, max_keywords=18)
    ideal_kws = ideal_kw_result.get("keywords", [])
    align = keyword_alignment(ideal_kws, user_answer_text)
    base = float(align.get("score") or 0.0)

    # Small boosts/penalties:
    ua = _strip_prompt_labels(user_answer_text or "").strip()
    if len(ua) < 60:
        base -= 10.0
    if len(ua) > 1200:
        base -= 5.0

    # Clamp 0-100
    score = max(0.0, min(100.0, round(base, 1)))
    result = {
        "score": score,
        "reasons": {
            "matched_keywords": align.get("matched", []),
            "missing_keywords": align.get("missing", []),
            "top_missing_keywords": align.get("top_missing_keywords", []),
            "note": "Heuristic score based on ideal-answer keyword overlap and length.",
            "question_hint": _strip_prompt_labels(question_text or "")[:200],
        },
        "debug": {
            "question_len": len(question_text or ""),
            "ideal_answer_len": len(ideal_answer_text or ""),
            "user_answer_len": len(user_answer_text or ""),
            "ideal_keywords_debug": ideal_kw_result.get("debug", {}),
            "alignment_debug": align.get("debug", {}),
        },
    }
    logging.info(f"MCP TOOL CALLED: answer_rubric_score, result: {result}")
    return result


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8080)


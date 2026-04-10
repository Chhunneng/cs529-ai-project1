"""LLM / OpenAI API integration (intent, resume extract/fill, Agents SDK).

Named ``llm`` so imports stay distinct from the third-party ``openai`` PyPI package
(``from openai import AsyncOpenAI`` vs ``from app.llm...``).
"""
from app.llm.resume_fill import generate_resume_fill

__all__ = [
    "generate_resume_fill",
]

"""OpenAI SDK integration (conversations, replies, intent, resume JSON fill)."""

from app.openai.client import (
    OpenAIReply,
    RESUME_ASSISTANT_SYSTEM_MESSAGE,
    create_openai_conversation,
    delete_openai_conversation_best_effort,
    generate_reply,
)
from app.openai.intent import IntentLabel, IntentResult, classify_intent
from app.openai.resume_fill import generate_resume_fill_json

__all__ = [
    "OpenAIReply",
    "RESUME_ASSISTANT_SYSTEM_MESSAGE",
    "IntentLabel",
    "IntentResult",
    "classify_intent",
    "create_openai_conversation",
    "delete_openai_conversation_best_effort",
    "generate_reply",
    "generate_resume_fill_json",
]

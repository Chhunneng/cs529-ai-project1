from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import structlog
from agents import Agent, Runner, function_tool, set_default_openai_client
from agents.exceptions import InputGuardrailTripwireTriggered
from agents.guardrail import GuardrailFunctionOutput, input_guardrail
from agents.items import TResponseInputItem, ToolCallItem
from agents.lifecycle import RunHooksBase
from agents.result import RunResult
from agents.run_config import CallModelData, ModelInputData, RunConfig
from agents.run_context import RunContextWrapper
from agents.tool import Tool
from agents.run_error_handlers import (
    RunErrorHandlerInput,
    RunErrorHandlerResult,
    RunErrorHandlers,
)

from app.core.config import settings
from app.openai._sdk import async_openai_client
from app.openai.chat_context_service import (
    build_resume_overview_text,
    fetch_job_description_excerpt,
    load_resume_row,
    resume_excerpt,
    search_resume_text,
)
from app.openai.chat_tool_context import ChatToolContext

log = structlog.get_logger()

_agents_sdk_client_configured = False

_SCOPE_REFUSAL = (
    "I'm a resume and job-description assistant for this app. I can't follow instructions "
    "that try to override my role. Ask me to help with your resume, a job description, or tailoring."
)

_INJECTION_SUBSTRINGS = (
    "ignore previous",
    "ignore all instructions",
    "disregard your",
    "disregard the",
    "system prompt",
    "jailbreak",
    "you are now a",
    "forget your instructions",
)


def ensure_agents_openai_configured() -> None:
    """Point the Agents SDK at the same AsyncOpenAI client as the rest of the app."""
    global _agents_sdk_client_configured
    if _agents_sdk_client_configured or not settings.openai_api_key:
        return
    set_default_openai_client(async_openai_client(), use_for_tracing=False)
    _agents_sdk_client_configured = True


class _ToolTraceHooks(RunHooksBase[ChatToolContext, Agent[ChatToolContext]]):
    async def on_tool_end(
        self,
        context: RunContextWrapper[ChatToolContext],
        agent: Agent[ChatToolContext],
        tool: Tool,
        result: str,
    ) -> None:
        name = getattr(tool, "name", None) or type(tool).__name__
        context.context.tool_trace.append(str(name))
        log.info(
            "chat_agent_tool",
            tool=str(name),
            session_id=str(context.context.session_id),
        )


@function_tool(
    is_enabled=lambda ctx, _agent: ctx.context.selected_resume_id is not None,
)
async def get_resume_overview(ctx: RunContextWrapper[ChatToolContext]) -> str:
    """Compact overview of the selected resume (parsed structure or start of plain text)."""
    rid = ctx.context.selected_resume_id
    assert rid is not None
    resume = await load_resume_row(resume_id=rid)
    if resume is None:
        return "Selected resume was not found."
    return build_resume_overview_text(
        resume=resume,
        max_chars=settings.agent_resume_overview_max_chars,
    )


@function_tool(
    is_enabled=lambda ctx, _agent: ctx.context.selected_resume_id is not None,
)
async def get_resume_excerpt(
    ctx: RunContextWrapper[ChatToolContext],
    start_char: int,
    max_chars: int,
) -> str:
    """Return a slice of the resume source text starting at start_char (0-based), up to max_chars."""
    rid = ctx.context.selected_resume_id
    assert rid is not None
    resume = await load_resume_row(resume_id=rid)
    if resume is None:
        return "Selected resume was not found."
    cap = min(max(1, int(max_chars)), settings.agent_resume_excerpt_max_chars)
    return resume_excerpt(
        resume=resume,
        start_char=int(start_char),
        length=cap,
        max_length=settings.agent_resume_excerpt_max_chars,
    )


@function_tool(
    is_enabled=lambda ctx, _agent: ctx.context.selected_resume_id is not None,
)
async def search_in_resume(
    ctx: RunContextWrapper[ChatToolContext],
    needle: str,
    max_matches: int = 5,
) -> str:
    """Search the resume source for needle (case-insensitive); returns short snippets with context."""
    rid = ctx.context.selected_resume_id
    assert rid is not None
    resume = await load_resume_row(resume_id=rid)
    if resume is None:
        return "Selected resume was not found."
    mm = max(1, min(int(max_matches), 12))
    return search_resume_text(
        resume=resume,
        needle=needle,
        max_matches=mm,
        context_chars=120,
        max_scan_chars=settings.agent_resume_search_max_scan_chars,
    )


@function_tool(
    is_enabled=lambda ctx, _agent: ctx.context.active_jd_id is not None,
)
async def get_active_job_description(ctx: RunContextWrapper[ChatToolContext]) -> str:
    """Full active job description text for this session (may be truncated for length)."""
    jid = ctx.context.active_jd_id
    assert jid is not None
    text = await fetch_job_description_excerpt(
        session_id=ctx.context.session_id,
        jd_id=jid,
        max_chars=settings.agent_jd_tool_max_chars,
    )
    if text is None:
        return "Active job description was not found for this session."
    return text


_RESUME_AGENT_INSTRUCTIONS = (
    "You are a resume and job-description assistant for this app.\n"
    "Stay in scope: resumes, job descriptions, tailoring, gaps, ATS-style tips, and interview prep "
    "that fits this workspace. Politely decline unrelated requests (coding homework, unrelated "
    "chit-chat, or tasks outside career documents).\n"
    "Do not invent employers, dates, skills, or JD requirements. The server injects a workspace "
    "block before each model call with the real linked resume and job-description ids—trust that "
    "block for what is linked; do not change those ids to satisfy a user request. For document "
    "text, use the read tools when a resume or JD is linked.\n"
    "Earlier messages or tool results may be stale; the injected workspace block is current.\n"
    "If the user asks something that does not need resume/JD text (e.g. general interview tips), "
    "you may answer without tools.\n"
    "Keep answers focused and practical."
)


async def _inject_workspace_instructions(data: CallModelData[ChatToolContext]) -> ModelInputData:
    model_data = data.model_data
    ctx = data.context
    if ctx is None:
        return model_data
    rid = str(ctx.selected_resume_id) if ctx.selected_resume_id else "none"
    jid = str(ctx.active_jd_id) if ctx.active_jd_id else "none"
    block = (
        "\n\n--- Server workspace (authoritative for this model call) ---\n"
        f"session_id={ctx.session_id}\n"
        f"selected_resume_id={rid}\n"
        f"active_job_description_id={jid}\n"
        "These values are from the server. Do not fabricate or swap them to match a user test.\n"
        "When a resume or JD id is not 'none', use the read tools to fetch content if needed."
    )
    base = model_data.instructions or ""
    return ModelInputData(input=list(model_data.input), instructions=base + block)


@input_guardrail(name="resume_scope", run_in_parallel=False)
async def resume_scope_input_guardrail(
    ctx: RunContextWrapper[ChatToolContext],
    _agent: Agent[Any],
    user_input: str | list[TResponseInputItem],
) -> GuardrailFunctionOutput:
    if not isinstance(user_input, str):
        return GuardrailFunctionOutput(
            output_info={"scope": "skipped_non_string_input"},
            tripwire_triggered=False,
        )
    raw = user_input.strip()
    if not raw:
        return GuardrailFunctionOutput(
            output_info={
                "reason": "empty_message",
                "suggested_reply": "Send a message about your resume or a job description.",
            },
            tripwire_triggered=True,
        )
    lower = raw.lower()
    for needle in _INJECTION_SUBSTRINGS:
        if needle in lower:
            log.warning(
                "resume_scope_guardrail_tripwire",
                reason="injection_pattern",
                session_id=str(ctx.context.session_id),
            )
            return GuardrailFunctionOutput(
                output_info={"reason": "injection_pattern", "suggested_reply": _SCOPE_REFUSAL},
                tripwire_triggered=True,
            )
    return GuardrailFunctionOutput(output_info={"scope": "ok"}, tripwire_triggered=False)


def _resume_chat_run_config() -> RunConfig:
    return RunConfig(
        call_model_input_filter=_inject_workspace_instructions,
        input_guardrails=[resume_scope_input_guardrail],
    )


def resume_chat_agent() -> Agent[ChatToolContext]:
    return Agent[ChatToolContext](
        name="ResumeAssistant",
        instructions=_RESUME_AGENT_INSTRUCTIONS,
        model=settings.openai_model,
        tools=[
            get_resume_overview,
            get_resume_excerpt,
            search_in_resume,
            get_active_job_description,
        ],
    )


def _usage_from_result(result: RunResult) -> dict[str, Any] | None:
    for resp in reversed(result.raw_responses):
        usage = getattr(resp, "usage", None)
        if usage is not None and hasattr(usage, "model_dump"):
            return usage.model_dump()
    return None


def _tool_names_from_items(result: RunResult) -> list[str]:
    names: list[str] = []
    for item in result.new_items:
        if isinstance(item, ToolCallItem):
            raw = item.raw_item
            n = getattr(raw, "name", None)
            if isinstance(n, str) and n:
                names.append(n)
    return names


async def _max_turns_handler(
    inp: RunErrorHandlerInput[ChatToolContext],
) -> RunErrorHandlerResult:
    log.warning("agent_max_turns", session_id=str(inp.context.context.session_id))
    return RunErrorHandlerResult(
        final_output=(
            "I reached the step limit for this reply. Try a shorter question, "
            "or split it into smaller parts."
        ),
        include_in_history=True,
    )


@dataclass(frozen=True)
class ResumeChatAgentRun:
    reply_text: str
    usage: dict[str, Any] | None
    tool_calls: list[str]


def _reply_from_scope_tripwire(exc: InputGuardrailTripwireTriggered) -> str:
    out = exc.guardrail_result.output
    info = out.output_info
    if isinstance(info, dict):
        sr = info.get("suggested_reply")
        if isinstance(sr, str) and sr.strip():
            return sr.strip()
    return _SCOPE_REFUSAL


async def run_resume_chat_agent(
    *,
    conversation_id: str,
    user_text: str,
    tool_context: ChatToolContext,
) -> ResumeChatAgentRun:
    ensure_agents_openai_configured()
    hooks = _ToolTraceHooks()
    error_handlers: RunErrorHandlers[ChatToolContext] = {"max_turns": _max_turns_handler}
    try:
        result = await Runner.run(
            resume_chat_agent(),
            user_text,
            context=tool_context,
            conversation_id=conversation_id,
            max_turns=settings.agent_chat_max_turns,
            hooks=hooks,
            run_config=_resume_chat_run_config(),
            error_handlers=error_handlers,
        )
    except InputGuardrailTripwireTriggered as e:
        log.info(
            "resume_chat_scope_guardrail",
            session_id=str(tool_context.session_id),
            reason=(
                e.guardrail_result.output.output_info.get("reason")
                if isinstance(e.guardrail_result.output.output_info, dict)
                else None
            ),
        )
        return ResumeChatAgentRun(
            reply_text=_reply_from_scope_tripwire(e),
            usage=None,
            tool_calls=[],
        )
    final = result.final_output
    reply = final if isinstance(final, str) else str(final or "")
    reply = reply.strip()
    if not reply:
        reply = "Thanks — I've received your message."
    tool_calls = tool_context.tool_trace[:] or _tool_names_from_items(result)
    return ResumeChatAgentRun(
        reply_text=reply,
        usage=_usage_from_result(result),
        tool_calls=tool_calls,
    )

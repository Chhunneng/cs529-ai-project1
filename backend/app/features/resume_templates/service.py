from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import structlog
from agents import Runner
from agents.stream_events import AgentUpdatedStreamEvent, RawResponsesStreamEvent, RunItemStreamEvent
from openai.types.responses import ResponseTextDeltaEvent

from app.llm.agents import LATEX_RESUME_FIX_AGENT, LATEX_RESUME_SAMPLE_WRITER_AGENT
from app.llm.agents_bootstrap import ONE_SHOT_AGENT_MAX_TURNS
from app.llm.schema import LatexResumeSampleOutput
from app.schemas.resume_template import ResumeTemplateValidateResponse
from app.features.resume_templates.latex_preview import validate_template_latex

log = structlog.get_logger()


def _sse_data_line(obj: dict) -> str:
    return f"data: {json.dumps(obj, default=str)}\n\n"


async def _stream_latex_agent_sse_lines(
    *,
    agent: Any,
    user_input: str,
    error_log_key: str,
    user_error_detail: str,
) -> AsyncIterator[str]:
    stream_result = Runner.run_streamed(
        agent,
        user_input,
        context=None,
        session=None,
        max_turns=ONE_SHOT_AGENT_MAX_TURNS,
    )
    try:
        async for ev in stream_result.stream_events():
            if isinstance(ev, RunItemStreamEvent):
                yield _sse_data_line({"type": "item", "name": ev.name})
            elif isinstance(ev, AgentUpdatedStreamEvent):
                yield _sse_data_line({"type": "agent", "name": ev.new_agent.name})
            elif isinstance(ev, RawResponsesStreamEvent) and isinstance(ev.data, ResponseTextDeltaEvent):
                delta = ev.data.delta or ""
                if delta:
                    yield _sse_data_line({"type": "text_delta", "delta": delta})
    except Exception as e:
        log.error(error_log_key, error=e)
        yield _sse_data_line({"type": "error", "detail": user_error_detail})
        return

    final = stream_result.final_output
    if not isinstance(final, LatexResumeSampleOutput):
        log.error(
            error_log_key + "_bad_output",
            final_type=type(final).__name__,
        )
        yield _sse_data_line({"type": "error", "detail": user_error_detail})
        return

    yield _sse_data_line({"type": "complete", "latex_resume_content": final.latex_resume_content})


async def stream_generate_latex_from_requirements_sse(*, requirements: str) -> AsyncIterator[str]:
    async for line in _stream_latex_agent_sse_lines(
        agent=LATEX_RESUME_SAMPLE_WRITER_AGENT,
        user_input=requirements,
        error_log_key="latex_resume_sample_writer_agent_error",
        user_error_detail="Generation failed. Try again later.",
    ):
        yield line


def _user_message_for_latex_fix(*, latex_source: str, error_message: str) -> str:
    return (
        "### Compiler / error information\n\n"
        f"{error_message.strip()}\n\n"
        "### Full LaTeX source to fix\n\n"
        f"{latex_source.strip()}"
    )


async def stream_fix_resume_template_latex_sse(*, latex_source: str, error_message: str) -> AsyncIterator[str]:
    user_input = _user_message_for_latex_fix(latex_source=latex_source, error_message=error_message)
    async for line in _stream_latex_agent_sse_lines(
        agent=LATEX_RESUME_FIX_AGENT,
        user_input=user_input,
        error_log_key="latex_resume_fix_agent_error",
        user_error_detail="Fix failed. Try again later.",
    ):
        yield line


async def validate_resume_template_latex(*, latex_source: str) -> ResumeTemplateValidateResponse:
    return await validate_template_latex(latex_source=latex_source)

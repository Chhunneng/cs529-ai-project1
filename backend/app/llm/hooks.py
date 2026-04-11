from agents.lifecycle import RunHooksBase
from agents.run_context import RunContextWrapper
from agents.tool import Tool
from agents import Agent
from app.llm.context import ResumeAgentContext

import structlog

log = structlog.get_logger()

class ResumePdfAgentToolTraceHooks(RunHooksBase[ResumeAgentContext, Agent[ResumeAgentContext]]):
    async def on_tool_end(
        self,
        context: RunContextWrapper[ResumeAgentContext],
        agent: Agent[ResumeAgentContext],
        tool: Tool,
        result: str,
    ) -> None:
        name = getattr(tool, "name", None) or type(tool).__name__
        context.context.tool_trace.append(str(name))
        correlation = (
            str(context.context.chat_session_id)
            if context.context.chat_session_id is not None
            else (
                str(context.context.render_output_id)
                if context.context.render_output_id is not None
                else "unknown"
            )
        )
        log.info(
            "chat_agent_tool",
            tool=str(name),
            session_id=correlation,
        )

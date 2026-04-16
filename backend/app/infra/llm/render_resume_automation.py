from __future__ import annotations

from app.llm.context import ResumeAgentContext
from app.llm.render_resume_agent import run_render_resume_automation


class RenderResumeAutomationClient:
    async def generate_latex(
        self,
        *,
        user_prompt: str,
        tool_context: ResumeAgentContext,
    ) -> tuple[str, list[str]]:
        result = await run_render_resume_automation(user_prompt=user_prompt, tool_context=tool_context)
        return result.latex_resume_content, list(tool_context.tool_trace)


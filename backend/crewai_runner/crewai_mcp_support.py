"""Shared MCP wiring and logging (course mcpdemo-style)."""

from __future__ import annotations

import logging
import os

from crewai.mcp import MCPServerHTTP
from crewai.mcp.filters import create_static_tool_filter

# Tools exposed by mcp/interview-tools/server.py (FastMCP)
_INTERVIEW_MCP_TOOL_NAMES = ("extract_keywords", "keyword_alignment", "answer_rubric_score")

_crewai_log_filter_installed = False


def ensure_crewai_log_filter() -> None:
    """Suppress noisy MCP native-tool messages on the crewai logger (mcpdemo pattern)."""
    global _crewai_log_filter_installed
    if _crewai_log_filter_installed:
        return

    class _SuppressMCPToolNoise(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            return "Failed to create native MCP tool" not in record.getMessage()

    logging.getLogger("crewai").addFilter(_SuppressMCPToolNoise())
    _crewai_log_filter_installed = True


def model_name() -> str:
    raw = os.getenv("CREWAI_LLM_MODEL", "openai/gpt-4o-mini").strip()
    return raw or "openai/gpt-4o-mini"


def mcp_interview_tools_url() -> str | None:
    raw = os.getenv("MCP_INTERVIEW_TOOLS_URL", "").strip()
    return raw or None


def build_mcp_servers():
    """HTTP MCP servers for interview tools; optional tool allowlist (mcpdemo-style)."""
    ensure_crewai_log_filter()
    url = mcp_interview_tools_url()
    if not url:
        return []

    tool_filter = create_static_tool_filter(allowed_tool_names=list(_INTERVIEW_MCP_TOOL_NAMES))

    return [
        MCPServerHTTP(
            url=url,
            streamable=True,
            cache_tools_list=True,
            tool_filter=tool_filter,
        )
    ]

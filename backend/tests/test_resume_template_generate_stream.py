"""Tests for LaTeX generate-from-requirements streaming service."""

import json
from unittest.mock import patch

import pytest

from app.llm.schema import LatexResumeSampleOutput
from app.features.resume_templates.service import stream_generate_latex_from_requirements_sse


@pytest.mark.asyncio
async def test_stream_generate_latex_emits_complete() -> None:
    tex = "\\documentclass{article}\\begin{document}g\\end{document}"
    fake = LatexResumeSampleOutput(latex_resume_content=tex)

    class FakeStreaming:
        final_output = fake

        async def stream_events(self):
            if False:
                yield None

    def fake_run_streamed(*_a, **_kw):
        return FakeStreaming()

    lines: list[str] = []
    with patch("app.features.resume_templates.service.Runner.run_streamed", fake_run_streamed):
        async for line in stream_generate_latex_from_requirements_sse(requirements="one column resume"):
            lines.append(line)

    assert lines
    payload = json.loads(lines[-1].removeprefix("data: ").strip())
    assert payload["type"] == "complete"
    assert payload["latex_resume_content"] == tex

"""Tests for resume template LaTeX validate endpoint helper."""

from unittest.mock import AsyncMock, patch

import pytest

from app.features.resume_templates.latex_preview import validate_template_latex


@pytest.mark.asyncio
async def test_validate_template_latex_ok_when_compile_succeeds() -> None:
    with patch(
        "app.features.resume_templates.latex_preview.compile_latex_to_pdf",
        AsyncMock(return_value=(b"%PDF", "")),
    ):
        r = await validate_template_latex(latex_source="\\documentclass{article}\\begin{document}x\\end{document}")
    assert r.ok is True
    assert r.message and "success" in r.message.lower()


@pytest.mark.asyncio
async def test_validate_template_latex_empty_source() -> None:
    r = await validate_template_latex(latex_source="   ")
    assert r.ok is False
    assert "empty" in (r.message or "").lower()

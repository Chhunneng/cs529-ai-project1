"""Create/patch resume templates require compilable LaTeX; `valid` is stored."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import engine
from app.main import app
from app.schemas.resume_template import ResumeTemplateValidateResponse

_MIN_TEX = r"\documentclass{article}\begin{document}x\end{document}"


@pytest.mark.asyncio
async def test_resume_template_valid_save_scenarios() -> None:
    """
    Single async test: sync TestClient-based tests elsewhere bind asyncpg to another loop;
    dispose the engine first so this coroutine's loop owns fresh pool connections.
    """
    await engine.dispose()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch(
            "app.features.resume_templates.api.validate_template_latex",
            new_callable=AsyncMock,
            return_value=ResumeTemplateValidateResponse(ok=False, message="bad tex"),
        ):
            res422 = await client.post(
                "/api/v1/resume-templates",
                json={"name": "t-invalid", "latex_source": _MIN_TEX},
            )
        assert res422.status_code == 422
        err = res422.json()["error"]
        assert err["code"] == "validation_error"
        assert err["details"].get("ok") is False

        with patch(
            "app.features.resume_templates.api.validate_template_latex",
            new_callable=AsyncMock,
            return_value=ResumeTemplateValidateResponse(
                ok=True,
                message="LaTeX compiles successfully with pdflatex.",
            ),
        ):
            res201 = await client.post(
                "/api/v1/resume-templates",
                json={"name": "t-valid-create", "latex_source": _MIN_TEX},
            )
        assert res201.status_code == 201
        data = res201.json()
        assert data["valid"] is True
        assert data["latex_source"] == _MIN_TEX
        tid = data["id"]

        with patch(
            "app.features.resume_templates.api.validate_template_latex",
            new_callable=AsyncMock,
            return_value=ResumeTemplateValidateResponse(ok=False, message="fail"),
        ):
            res_patch_bad = await client.patch(
                f"/api/v1/resume-templates/{tid}",
                json={"latex_source": _MIN_TEX + "\n%bad"},
            )
        assert res_patch_bad.status_code == 422

        with patch(
            "app.features.resume_templates.api.validate_template_latex",
            new_callable=AsyncMock,
        ) as validate_mock:
            res_rename = await client.patch(
                f"/api/v1/resume-templates/{tid}",
                json={"name": "renamed-only"},
            )
        assert res_rename.status_code == 200
        validate_mock.assert_not_awaited()
        assert res_rename.json()["name"] == "renamed-only"

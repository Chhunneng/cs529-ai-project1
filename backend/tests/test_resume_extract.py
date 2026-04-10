from unittest.mock import AsyncMock, patch

import pytest

from app.llm.resume_extract import ResumeProfileV1, extract_resume_profile_json


@pytest.mark.asyncio
async def test_extract_resume_profile_json_uses_stateless_runner_only() -> None:
    fake = ResumeProfileV1.model_validate(
        {
            "_schema_version": 1,
            "summary": "Builder",
            "contact": [],
            "outline": [
                {"depth": 0, "text": "Experience"},
                {"depth": 1, "text": "Acme | 2020-2023"},
                {"depth": 2, "text": "Engineer"},
                {"depth": 3, "text": "Shipped widgets"},
            ],
            "sections_flat": [],
        }
    )
    run_mock = AsyncMock(return_value=type("RR", (), {"final_output": fake})())

    with patch("app.llm.resume_extract.Runner.run", run_mock):
        out = await extract_resume_profile_json(resume_text="Jane Doe\njane@example.com")

    assert out["_schema_version"] == 1
    assert out["contact"] == []
    assert out["summary"] == "Builder"
    assert out["sections_flat"] == []
    assert len(out["outline"]) == 4
    assert out["outline"][0] == {"depth": 0, "text": "Experience"}
    assert out["outline"][3] == {"depth": 3, "text": "Shipped widgets"}

    run_mock.assert_awaited_once()
    kwargs = run_mock.await_args.kwargs
    assert kwargs.get("session") is None
    assert kwargs.get("conversation_id") is None

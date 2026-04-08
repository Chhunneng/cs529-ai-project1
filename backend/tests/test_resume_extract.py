from unittest.mock import AsyncMock, patch

import pytest

from app.openai.resume_extract import extract_resume_profile_json


@pytest.mark.asyncio
async def test_extract_resume_profile_json_uses_stateless_input_only() -> None:
    fake_json = (
        '{"_schema_version":1,"summary":"Builder","contact":[],'
        '"outline":[{"depth":0,"text":"Experience"},{"depth":1,"text":"Acme | 2020-2023"},'
        '{"depth":2,"text":"Engineer"},{"depth":3,"text":"Shipped widgets"}],'
        '"sections_flat":[]}'
    )
    fake_resp = type("R", (), {"output_text": fake_json})()
    create_mock = AsyncMock(return_value=fake_resp)

    with patch("app.openai.resume_extract.async_openai_client") as client_factory:
        client_factory.return_value = type(
            "C", (), {"responses": type("R", (), {"create": create_mock})()}
        )()
        out = await extract_resume_profile_json(resume_text="Jane Doe\njane@example.com")

    assert out["_schema_version"] == 1
    assert out["contact"] == []
    assert out["summary"] == "Builder"
    assert out["sections_flat"] == []
    assert len(out["outline"]) == 4
    assert out["outline"][0] == {"depth": 0, "text": "Experience"}
    assert out["outline"][3] == {"depth": 3, "text": "Shipped widgets"}
    create_mock.assert_awaited_once()
    kwargs = create_mock.await_args.kwargs
    assert "conversation" not in kwargs
    assert "conversation_id" not in kwargs
    assert "input" in kwargs
    assert isinstance(kwargs["input"], list)
    fmt = kwargs["text"]["format"]
    assert fmt["name"] == "resume_profile_v1"

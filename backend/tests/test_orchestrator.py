from app.orchestrator.router import decide_next_action


def test_job_description_intent() -> None:
    a = decide_next_action(
        has_resume=False, has_job_description=False, user_intent="job_description"
    )
    assert a.agent_name == "JDIngestAgent"


def test_tailor_resume() -> None:
    a = decide_next_action(
        has_resume=True, has_job_description=True, user_intent="tailor_resume"
    )
    assert a.agent_name == "TailorAgent"


def test_gap_analysis_when_resume_and_jd_and_generic() -> None:
    a = decide_next_action(
        has_resume=True, has_job_description=True, user_intent="generic_chat"
    )
    assert a.agent_name == "GapAnalysisAgent"


def test_default_openai_reply() -> None:
    a = decide_next_action(
        has_resume=False, has_job_description=False, user_intent="generic_chat"
    )
    assert a.agent_name == "OpenAIReplyAgent"


def test_upload_resume_future() -> None:
    a = decide_next_action(
        has_resume=False, has_job_description=False, user_intent="upload_resume"
    )
    assert a.agent_name == "ResumeParserAgent"

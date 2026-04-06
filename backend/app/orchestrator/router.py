from dataclasses import dataclass


@dataclass(frozen=True)
class NextAction:
    agent_name: str
    reason: str


def decide_next_action(*, has_resume: bool, has_job_description: bool, user_intent: str) -> NextAction:
    """
    Phase 1 router skeleton.
    Later: replace user_intent with intent classifier + session state machine.
    """
    if user_intent == "upload_resume":
        return NextAction(agent_name="ResumeParserAgent", reason="New resume uploaded")
    if user_intent == "job_description":
        return NextAction(agent_name="JDKeywordAgent", reason="Job description detected")
    if has_resume and has_job_description:
        return NextAction(agent_name="GapAnalysisAgent", reason="Resume+JD available")
    if user_intent == "improve_resume":
        return NextAction(agent_name="ResumeGeneratorAgent", reason="User asked to improve resume")
    if user_intent == "score_resume":
        return NextAction(agent_name="ScoringAgent", reason="User asked for score")
    return NextAction(agent_name="NoOpAgent", reason="No actionable intent")


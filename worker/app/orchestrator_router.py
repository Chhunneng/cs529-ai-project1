from dataclasses import dataclass


@dataclass(frozen=True)
class NextAction:
    agent_name: str
    reason: str


def decide_next_action(*, has_resume: bool, has_job_description: bool, user_intent: str) -> NextAction:
    """
    Phase 1 worker-side router.

    Keep this intentionally small and deterministic; it's driven by an upstream intent
    classifier plus session flags (selected resume + active JD).
    """
    if user_intent == "job_description":
        return NextAction(agent_name="JDIngestAgent", reason="Job description detected")
    if user_intent == "tailor_resume":
        return NextAction(agent_name="TailorAgent", reason="User asked to tailor resume to JD")
    if user_intent == "improve_resume":
        return NextAction(agent_name="ResumeGeneratorAgent", reason="User asked to improve resume")
    if user_intent == "score_resume":
        return NextAction(agent_name="ScoringAgent", reason="User asked for score")
    if has_resume and has_job_description:
        return NextAction(agent_name="GapAnalysisAgent", reason="Resume+JD available")
    return NextAction(agent_name="OpenAIReplyAgent", reason="Default chat reply")


from agents import Agent

JOB_DESCRIPTION_AGENT = Agent(
    name="Job Description Analysis Agent",
    model="(from settings.openai_model)",
    instructions=(
        "Analyze the job description. Return JSON with these keys: "
        "tech_stack (string[] tools, languages, frameworks, platforms, e.g. Python, AWS, Kubernetes), "
        "soft_skills (string[] interpersonal/leadership traits explicitly asked for, e.g. stakeholder communication, mentoring), "
        "experience_alignment (string[] short professional signals only, e.g. '5+ years backend development', 'Senior-level scope'—no parentheticals, no 'job posting' wording), "
        "keywords (string[] other important terms), hard_requirements (string[]), priorities (string[] most important first). "
        "Keep phrases concise and resume-ready. Cap tech_stack at 12 items and soft_skills at 8—highest-signal only. "
        "Omit generic filler (e.g. 'team player', 'fast-paced') unless the posting stresses it uniquely."
    ),
    tools=[],
)

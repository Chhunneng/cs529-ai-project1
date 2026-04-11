from agents import Agent, ModelSettings
from openai.types.shared import Reasoning

from app.core.config import settings
from app.llm.schema import (
    JobDescriptionParserOutput,
    LatexResumeSampleOutput,
    ResumeFillAtsV1,
    ResumePdfMessageOutput,
    ResumeProfileV1,
    ResumeTailorOutput,
)
from app.llm.tools import (
    get_full_resume_text,
    get_resume_excerpt,
    search_in_resume,
    get_active_job_description,
    get_resume_template_latex,
    check_latex_compiles_on_server,
)

from app.llm._instructions import (
    JOB_DESCRIPTION_PARSER_INSTRUCTIONS,
    LATEX_RESUME_FIX_INSTRUCTIONS,
    LATEX_RESUME_SAMPLE_WRITER_INSTRUCTIONS,
    RESUME_AGENT_INSTRUCTIONS,
    RESUME_EXTRACT_INSTRUCTIONS,
    RESUME_FILL_INSTRUCTIONS,
    RESUME_TAILOR_INSTRUCTIONS,
)



LATEX_RESUME_SAMPLE_WRITER_AGENT = Agent(
    name="Latex Resume Sample Writer Agent",
    instructions=LATEX_RESUME_SAMPLE_WRITER_INSTRUCTIONS,
    model=settings.openai.model,
    output_type=LatexResumeSampleOutput,
    model_settings=ModelSettings(reasoning=Reasoning(effort="high")),
    tools=[
        check_latex_compiles_on_server,
    ],
)


LATEX_RESUME_FIX_AGENT = Agent(
    name="Latex Resume Fix Agent",
    instructions=LATEX_RESUME_FIX_INSTRUCTIONS,
    model=settings.openai.model,
    output_type=LatexResumeSampleOutput,
    model_settings=ModelSettings(reasoning=Reasoning(effort="high")),
    tools=[
        check_latex_compiles_on_server,
    ],
)

RESUME_EXTRACT_AGENT = Agent(
    name="Resume Extract Agent",
    instructions=RESUME_EXTRACT_INSTRUCTIONS,
    model=settings.openai.model,
    model_settings=ModelSettings(reasoning=Reasoning(effort="medium")),
    output_type=ResumeProfileV1,
)


JOB_DESCRIPTION_PARSER_AGENT = Agent(
    name="Job Description Parser Agent",
    instructions=JOB_DESCRIPTION_PARSER_INSTRUCTIONS,
    model=settings.openai.model,
    output_type=JobDescriptionParserOutput,
    model_settings=ModelSettings(reasoning=Reasoning(effort="medium")),
    tools=[
        get_active_job_description,
    ],
)

get_job_description_details_tool = JOB_DESCRIPTION_PARSER_AGENT.as_tool(
    tool_name="get_job_description_details",
    tool_description="Get the details of the active job description.",
)

RESUME_TAILOR_AGENT = Agent(
    name="Resume Tailor Agent",
    instructions=RESUME_TAILOR_INSTRUCTIONS,
    model=settings.openai.model,
    model_settings=ModelSettings(reasoning=Reasoning(effort="medium")),
    output_type=ResumeTailorOutput,
    tools=[
        get_job_description_details_tool,
        get_full_resume_text,
        get_resume_excerpt,
    ],
)

tailor_resume_for_job_tool = RESUME_TAILOR_AGENT.as_tool(
    tool_name="tailor_resume_for_job",
    tool_description=(
        "Run a dedicated resume-tailoring pass for the active job description. "
        "Call this when the user wants a tailored, ATS-aware resume or a PDF/typeset document aligned "
        "to the linked job—before you draft latex_document. "
        "The sub-agent loads parsed JD details (Keywords, Skills, Requirements) and the full resume "
        "text, then returns structured fields: tailored_resume_text (plain text, authoritative body "
        "copy for LaTeX), change_summary, and matched_keywords. "
        "You must base the document body on tailored_resume_text from this tool—not on stale guesses "
        "or unfetched resume text. "
        "Do not use for pure Q&A or advice with no document or rewrite request."
    ),
    max_turns=12,
    is_enabled=lambda ctx, _agent: (
        ctx.context.resume_id is not None and ctx.context.job_description_id is not None
    ),
)

RESUME_PDF_AGENT = Agent(
    name="ResumePdfAssistant",
    instructions=RESUME_AGENT_INSTRUCTIONS,
    model=settings.openai.model,
    output_type=ResumePdfMessageOutput,
    tools=[
        get_job_description_details_tool,
        tailor_resume_for_job_tool,
        get_full_resume_text,
        get_resume_excerpt,
        search_in_resume,
        get_resume_template_latex,
        check_latex_compiles_on_server,
    ],
)


RESUME_FILL_AGENT = Agent(
    name="ResumeFill",
    instructions=RESUME_FILL_INSTRUCTIONS,
    model=settings.openai.model,
    output_type=ResumeFillAtsV1,
    tools=[],
)

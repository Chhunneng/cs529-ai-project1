from agents import Agent, ModelSettings
from openai.types.shared import Reasoning

from app.llm.schema import (
    JobDescriptionParserOutput,
    LatexResumeSampleOutput,
    ResumeFillAtsV1,
    ResumePdfMessageOutput,
    ResumeProfileV1,
)
from app.llm.tools import (
    get_resume_overview,
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
)

LATEX_RESUME_SAMPLE_WRITER_AGENT = Agent(
    name="Latex Resume Sample Writer Agent",
    instructions=LATEX_RESUME_SAMPLE_WRITER_INSTRUCTIONS,
    model="gpt-5-nano",
    output_type=LatexResumeSampleOutput,
    model_settings=ModelSettings(reasoning=Reasoning(effort="high")),
    tools=[
        check_latex_compiles_on_server,
    ],
)


LATEX_RESUME_FIX_AGENT = Agent(
    name="Latex Resume Fix Agent",
    instructions=LATEX_RESUME_FIX_INSTRUCTIONS,
    model="gpt-5-nano",
    output_type=LatexResumeSampleOutput,
    model_settings=ModelSettings(reasoning=Reasoning(effort="high")),
    tools=[
        check_latex_compiles_on_server,
    ],
)


RESUME_EXTRACT_AGENT = Agent(
    name="Resume Extract Agent",
    instructions=RESUME_EXTRACT_INSTRUCTIONS,
    model="gpt-5-nano",
    model_settings=ModelSettings(reasoning=Reasoning(effort="medium")),
    output_type=ResumeProfileV1,
)


JOB_DESCRIPTION_PARSER_AGENT = Agent(
    name="Job Description Parser Agent",
    instructions=JOB_DESCRIPTION_PARSER_INSTRUCTIONS,
    model="gpt-5-nano",
    output_type=JobDescriptionParserOutput,
    model_settings=ModelSettings(reasoning=Reasoning(effort="medium")),
    tools=[
        get_active_job_description,
    ],
)


RESUME_PDF_AGENT = Agent(
    name="ResumePdfAssistant",
    instructions=RESUME_AGENT_INSTRUCTIONS,
    model="gpt-5-nano",
    output_type=ResumePdfMessageOutput,
    tools=[
        get_resume_overview,
        get_resume_excerpt,
        search_in_resume,
        get_active_job_description,
        get_resume_template_latex,
        check_latex_compiles_on_server,
    ],
)


RESUME_FILL_AGENT = Agent(
    name="ResumeFill",
    instructions=RESUME_FILL_INSTRUCTIONS,
    model="gpt-5-nano",
    output_type=ResumeFillAtsV1,
    tools=[],
)

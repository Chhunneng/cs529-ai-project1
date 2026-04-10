from pydantic import BaseModel, ConfigDict, Field


class LatexResumeSampleOutput(BaseModel):
    """
    Output schema for the latex resume sample writer agent.
    """

    latex_resume_content: str


class ResumeProfileContactRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    value: str


class ResumeProfileOutlineRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    depth: int
    text: str


class ResumeProfileSectionFlat(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    content: str


class ResumeProfileV1(BaseModel):
    """Resume profile v1: outline rows (depth + text) + contact + summary + sections_flat."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_version: int = Field(
        ...,
        alias="_schema_version",
        description="Schema version; use 1.",
    )
    summary: str
    contact: list[ResumeProfileContactRow]
    outline: list[ResumeProfileOutlineRow]
    sections_flat: list[ResumeProfileSectionFlat]


class ResumePdfMessageOutput(BaseModel):
    """Structured final output: user-facing text plus LaTeX source for PDF compilation."""

    assistant_message: str = Field(..., description="Short reply shown in chat.")
    latex_document: str | None = Field(
        default=None,
        description=(
            "When the user asked for a PDF, an updated typeset resume, or similar output, "
            "set this to a complete LaTeX document pdflatex can compile. "
            "Use the linked template for style and syntax (preamble, packages, fonts, section "
            "macros)—not as a fixed layout to copy verbatim; the body must contain real resume "
            "content from tools, with sections and bullets you add or change as needed. "
            "When the user only wanted advice, Q&A, or edits without generating a document, "
            "set this field to null."
        ),
    )


class HeaderLink(BaseModel):
    label: str
    url: str


class Header(BaseModel):
    full_name: str
    email: str
    phone: str
    location: str
    links: list[HeaderLink] = Field(default_factory=list)


class ExperienceItem(BaseModel):
    title: str
    company: str
    location: str
    start: str
    end: str
    bullets: list[str]


class EducationItem(BaseModel):
    school: str
    degree: str
    start: str
    end: str


class ResumeFillAtsV1(BaseModel):
    header: Header
    summary: str
    experience: list[ExperienceItem]
    education: list[EducationItem]
    skills: list[str]

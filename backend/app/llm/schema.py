from pydantic import BaseModel


class LatexResumeSampleOutput(BaseModel):
    """
    Output schema for the latex resume sample writer agent.
    """
    latex_resume_content: str

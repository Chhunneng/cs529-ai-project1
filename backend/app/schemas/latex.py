from pydantic import BaseModel, Field


class LatexCompileRequest(BaseModel):
    tex: str = Field(..., min_length=1)


class LatexCompileResponse(BaseModel):
    pdf_base64: str
    log: str

from fastapi import APIRouter, Header, HTTPException, status

from app.core.config import settings
from app.services.latex_compile import pdf_to_base64
from app.features.latex.service import compile_tex_to_pdf
from app.schemas.latex import LatexCompileRequest, LatexCompileResponse

router = APIRouter()


def _check_internal_token(x_internal_token: str | None) -> None:
    expected = settings.internal.compile_token
    if not expected:
        return
    if x_internal_token != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing X-Internal-Token",
        )


@router.post("/compile", response_model=LatexCompileResponse)
async def compile_tex(
    body: LatexCompileRequest,
    x_internal_token: str | None = Header(default=None, alias="X-Internal-Token"),
) -> LatexCompileResponse:
    _check_internal_token(x_internal_token)
    try:
        pdf_bytes, log = await compile_tex_to_pdf(tex=body.tex)
    except RuntimeError as e:
        # `features.latex` wraps compile errors into RuntimeError for consistent callers.
        # The old API endpoint shape expects a 422 when compilation fails.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": str(e)},
        ) from e
    return LatexCompileResponse(pdf_base64=pdf_to_base64(pdf_bytes), log=log)

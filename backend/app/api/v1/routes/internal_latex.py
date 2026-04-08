import asyncio

from fastapi import APIRouter, Header, HTTPException, status

from app.core.config import settings
from app.schemas.latex import LatexCompileRequest, LatexCompileResponse
from app.services.latex_compile import LatexCompileError, compile_tex_to_pdf_bytes, pdf_to_base64

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
        pdf_bytes, log = await asyncio.to_thread(compile_tex_to_pdf_bytes, body.tex)
    except LatexCompileError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": e.args[0], "log": e.log},
        ) from e
    return LatexCompileResponse(pdf_base64=pdf_to_base64(pdf_bytes), log=log)

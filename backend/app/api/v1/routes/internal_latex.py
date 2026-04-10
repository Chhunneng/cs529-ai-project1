from fastapi import APIRouter, HTTPException, status

from app.services.latex_compile import LaTeXCompileFailed, pdf_to_base64
from app.features.latex.service import compile_latex_to_pdf
from app.schemas.latex import LatexCompileRequest, LatexCompileResponse

router = APIRouter()



@router.post("/compile", response_model=LatexCompileResponse)
async def compile_tex(
    body: LatexCompileRequest,
) -> LatexCompileResponse:
    try:
        pdf_bytes, log = await compile_latex_to_pdf(latex=body.latex)
    except LaTeXCompileFailed as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.detail,
        ) from e
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": str(e)},
        ) from e
    return LatexCompileResponse(pdf_base64=pdf_to_base64(pdf_bytes), log=log)

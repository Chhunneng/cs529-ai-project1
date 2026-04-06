from __future__ import annotations

import base64

import httpx
import structlog

from app.config import settings

log = structlog.get_logger()


async def compile_tex_to_pdf(*, tex: str) -> tuple[bytes, str]:
    url = f"{settings.latex_service_url.rstrip('/')}/compile"
    headers: dict[str, str] = {}
    if settings.internal_compile_token:
        headers["X-Internal-Token"] = settings.internal_compile_token

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, json={"tex": tex}, headers=headers)
    if resp.status_code >= 400:
        detail: str | dict
        try:
            body = resp.json()
            detail = body.get("detail", body)
        except Exception:
            detail = resp.text
        log.warning("latex_compile_http_error", status=resp.status_code, detail=str(detail)[:2000])
        raise RuntimeError(f"LaTeX service error {resp.status_code}: {detail}") from None
    data = resp.json()
    pdf_b64 = data.get("pdf_base64")
    if not pdf_b64:
        raise RuntimeError("LaTeX service returned no pdf_base64")
    log_bytes = str(data.get("log") or "")[-4000:]
    return base64.b64decode(pdf_b64), log_bytes

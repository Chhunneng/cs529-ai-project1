from __future__ import annotations

import uuid
from io import BytesIO
from pathlib import Path

import structlog
from docx import Document
from fastapi import UploadFile
from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.resume import Resume
from app.queue_jobs import ParseResumeJob
from app.services.queue import enqueue_job

log = structlog.get_logger()

ALLOWED_EXTENSIONS = frozenset({".pdf", ".txt", ".docx"})

MIME_BY_EXT: dict[str, str] = {
    ".pdf": "application/pdf",
    ".txt": "text/plain; charset=utf-8",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


class ResumeUploadError(ValueError):
    pass


def _extension_from_filename(name: str | None) -> str:
    if not name or not name.strip():
        raise ResumeUploadError("Filename is required.")
    p = Path(name.strip())
    ext = p.suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ResumeUploadError(
            "Unsupported file type. Allowed: .pdf, .txt, .docx."
        )
    return ext


def _extract_text(ext: str, data: bytes) -> str:
    if ext == ".txt":
        return data.decode("utf-8", errors="replace").strip()
    if ext == ".pdf":
        reader = PdfReader(BytesIO(data))
        parts: list[str] = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                parts.append(t)
        return "\n".join(parts).strip()
    if ext == ".docx":
        doc = Document(BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs).strip()
    raise ResumeUploadError("Unsupported file type.")


def absolute_upload_path(storage_relpath: str) -> Path | None:
    base = Path(settings.storage.resume_uploads_dir).resolve()
    target = (base / storage_relpath).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        log.warn("resume_path_escape_attempt", relpath=storage_relpath)
        return None
    return target


def remove_stored_file(storage_relpath: str | None) -> None:
    if not storage_relpath:
        return
    path = absolute_upload_path(storage_relpath)
    if path is None:
        return
    try:
        if path.is_file():
            path.unlink()
    except OSError as e:
        log.warn("resume_file_delete_failed", path=str(path), error=str(e))


async def read_upload_bytes(upload: UploadFile, limit: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise ResumeUploadError(
                f"File is too large (max {limit // (1024 * 1024)} MB)."
            )
        chunks.append(chunk)
    data = b"".join(chunks)
    if not data:
        raise ResumeUploadError("Empty file.")
    return data


async def create_resume_from_upload(
    *, db: AsyncSession, upload: UploadFile
) -> Resume:
    ext = _extension_from_filename(upload.filename)
    data = await read_upload_bytes(upload, settings.storage.resume_upload_max_bytes)
    content_text = _extract_text(ext, data)
    if not content_text:
        raise ResumeUploadError(
            "Could not extract any text from this file. Try a different export or format."
        )

    resume_id = uuid.uuid4()
    storage_relpath = f"{resume_id}{ext}"
    abs_path = absolute_upload_path(storage_relpath)
    if abs_path is None:
        raise ResumeUploadError("Invalid storage path.")

    abs_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        abs_path.write_bytes(data)
    except OSError as e:
        log.error("resume_write_failed", path=str(abs_path), error=str(e))
        raise ResumeUploadError("Could not save file.") from e

    original = Path(upload.filename or "resume").name
    if len(original) > 255:
        original = original[:255]

    resume = Resume(
        id=resume_id,
        original_filename=original,
        mime_type=MIME_BY_EXT.get(ext, "application/octet-stream"),
        byte_size=len(data),
        storage_relpath=storage_relpath,
        content_text=content_text,
        parsed_json=None,
    )
    db.add(resume)
    try:
        await db.commit()
        await db.refresh(resume)
    except Exception:
        await db.rollback()
        remove_stored_file(storage_relpath)
        raise

    try:
        await enqueue_job(ParseResumeJob(resume_id=str(resume_id)))
        log.info("parse_resume_enqueued", resume_id=str(resume_id))
    except Exception:
        log.exception("parse_resume_enqueue_failed", resume_id=str(resume_id))

    return resume

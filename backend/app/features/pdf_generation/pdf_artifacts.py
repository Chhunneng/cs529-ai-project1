from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings
from app.db.session import AsyncSessionMaker
from app.models.pdf_artifact import PdfArtifact

PDF_ARTIFACT_MIME = "application/pdf"


def unlink_pdf_artifact_file(*, storage_relpath: str) -> None:
    """Remove a stored PDF file under ``artifacts_dir`` if it exists (same rules as session/message cleanup)."""
    root = Path(settings.storage.artifacts_dir).resolve()
    try:
        path = (root / storage_relpath).resolve()
        path.relative_to(root)
    except (ValueError, OSError):
        return
    if path.is_file():
        try:
            path.unlink()
        except OSError:
            pass


@dataclass(frozen=True)
class PdfArtifactFileWrite:
    artifact_id: uuid.UUID
    storage_relpath: str
    sha256_hex: str


def write_pdf_artifact_file(pdf_bytes: bytes) -> PdfArtifactFileWrite:
    """Write PDF bytes under artifacts_dir and return ids + hash for the DB row."""
    artifact_id = uuid.uuid4()
    storage_relpath = f"pdf-artifacts/{artifact_id}.pdf"
    root = Path(settings.storage.artifacts_dir).resolve()
    dest = (root / storage_relpath).resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(pdf_bytes)
    sha256_hex = hashlib.sha256(pdf_bytes).hexdigest()
    return PdfArtifactFileWrite(
        artifact_id=artifact_id,
        storage_relpath=storage_relpath,
        sha256_hex=sha256_hex,
    )


async def insert_pdf_artifact_row(
    session_id: uuid.UUID,
    write: PdfArtifactFileWrite,
) -> uuid.UUID:
    """Persist a PdfArtifact row matching a file already written by write_pdf_artifact_file."""
    async with AsyncSessionMaker() as db:
        db.add(
            PdfArtifact(
                id=write.artifact_id,
                session_id=session_id,
                storage_relpath=write.storage_relpath,
                mime_type=PDF_ARTIFACT_MIME,
                sha256_hex=write.sha256_hex,
            )
        )
        await db.commit()
    return write.artifact_id

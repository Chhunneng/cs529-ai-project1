from __future__ import annotations

import uuid
from pathlib import Path

from app.core.config import settings


class LocalArtifactStore:
    def write_tex_pdf(
        self,
        *,
        output_id: uuid.UUID,
        tex: str,
        pdf_bytes: bytes,
    ) -> tuple[str, str]:
        out_dir = Path(settings.storage.artifacts_dir) / str(output_id)
        out_dir.mkdir(parents=True, exist_ok=True)

        tex_path = out_dir / "resume.tex"
        tex_path.write_text(tex, encoding="utf-8")

        pdf_path = out_dir / "resume.pdf"
        pdf_path.write_bytes(pdf_bytes)

        return str(tex_path.resolve()), str(pdf_path.resolve())


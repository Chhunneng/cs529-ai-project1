"""Resume templates: DB-only LaTeX, drop storage_path.

Revision ID: 0005_resume_templates_db_only_latex
Revises: 0004_agent_sessions_openai_conversation_id
Create Date: 2026-04-07
"""

from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0005_resume_templates_db_only_latex"
down_revision = "0004_agent_sessions_openai_conversation_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    tex_file = backend_root / "templates" / "resume" / "ats-v1" / "template.tex"
    if not tex_file.is_file():
        raise RuntimeError(f"Migration expects bundled template at {tex_file}")
    ats_tex = tex_file.read_text(encoding="utf-8")

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE resume_templates
            SET latex_source = :tex
            WHERE id = 'ats-v1' AND (latex_source IS NULL OR trim(latex_source) = '')
            """
        ),
        {"tex": ats_tex},
    )

    empty = conn.execute(
        sa.text(
            """
            SELECT count(*) FROM resume_templates
            WHERE latex_source IS NULL OR trim(latex_source) = ''
            """
        )
    ).scalar()
    if empty and int(empty) > 0:
        raise RuntimeError(
            "resume_templates has rows with empty latex_source after backfill; fix data and retry"
        )

    op.alter_column(
        "resume_templates",
        "latex_source",
        existing_type=sa.Text(),
        nullable=False,
    )
    op.drop_column("resume_templates", "storage_path")


def downgrade() -> None:
    op.alter_column(
        "resume_templates",
        "latex_source",
        existing_type=sa.Text(),
        nullable=True,
    )
    op.add_column(
        "resume_templates",
        sa.Column("storage_path", sa.Text(), nullable=True),
    )
    op.execute(
        sa.text("UPDATE resume_templates SET storage_path = 'resume/ats-v1' WHERE id = 'ats-v1'")
    )
    op.execute(
        sa.text("UPDATE resume_templates SET storage_path = '__inline__' WHERE id <> 'ats-v1'")
    )
    op.alter_column(
        "resume_templates",
        "storage_path",
        existing_type=sa.Text(),
        nullable=False,
    )

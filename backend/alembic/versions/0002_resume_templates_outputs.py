"""Resume templates and outputs.

Revision ID: 0002_resume_templates_outputs
Revises: 0001_initial
Create Date: 2026-04-06
"""

import json
from pathlib import Path

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_resume_templates_outputs"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resume_templates",
        sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("schema_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_table(
        "resume_outputs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("input_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("tex_path", sa.Text(), nullable=True),
        sa.Column("pdf_path", sa.Text(), nullable=True),
        sa.Column("error_text", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["session_id"], ["agent_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["template_id"], ["resume_templates.id"], ondelete="RESTRICT"),
    )

    backend_root = Path(__file__).resolve().parents[2]
    schema_path = backend_root / "templates" / "resume" / "ats-v1" / "schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    resume_templates = sa.table(
        "resume_templates",
        sa.column("id", sa.String(length=64)),
        sa.column("name", sa.Text()),
        sa.column("storage_path", sa.Text()),
        sa.column("schema_json", postgresql.JSONB),
    )
    op.bulk_insert(
        resume_templates,
        [
            {
                "id": "ats-v1",
                "name": "ATS Classic",
                "storage_path": "resume/ats-v1",
                "schema_json": schema,
            }
        ],
    )


def downgrade() -> None:
    op.drop_table("resume_outputs")
    op.drop_table("resume_templates")

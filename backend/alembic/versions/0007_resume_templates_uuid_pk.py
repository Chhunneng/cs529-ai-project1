"""Resume templates: UUID primary key (replace string id).

Revision ID: 0007_resume_templates_uuid_pk
Revises: 0006_resume_outputs_template_id_nullable
Create Date: 2026-04-07
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0007_resume_templates_uuid_pk"
down_revision = "0006_resume_outputs_template_id_nullable"
branch_labels = None
depends_on = None

# Deterministic UUID for legacy seeded row id "ats-v1" (stable across environments).
LEGACY_ATS_V1_UUID = uuid.uuid5(uuid.NAMESPACE_DNS, "cs529.resume_template.ats-v1")


def upgrade() -> None:
    conn = op.get_bind()

    op.drop_constraint(
        "resume_outputs_template_id_fkey",
        "resume_outputs",
        type_="foreignkey",
    )

    op.add_column(
        "resume_templates",
        sa.Column("id_new", postgresql.UUID(as_uuid=True), nullable=True),
    )

    conn.execute(
        sa.text("UPDATE resume_templates SET id_new = CAST(:u AS uuid) WHERE id = 'ats-v1'"),
        {"u": str(LEGACY_ATS_V1_UUID)},
    )
    conn.execute(sa.text("UPDATE resume_templates SET id_new = gen_random_uuid() WHERE id_new IS NULL"))

    op.add_column(
        "resume_outputs",
        sa.Column("template_id_new", postgresql.UUID(as_uuid=True), nullable=True),
    )
    conn.execute(
        sa.text(
            """
            UPDATE resume_outputs AS o
            SET template_id_new = t.id_new
            FROM resume_templates AS t
            WHERE o.template_id IS NOT NULL AND o.template_id = t.id
            """
        )
    )

    op.drop_column("resume_outputs", "template_id")
    op.execute(sa.text("ALTER TABLE resume_outputs RENAME COLUMN template_id_new TO template_id"))

    op.drop_constraint("resume_templates_pkey", "resume_templates", type_="primary")
    op.drop_column("resume_templates", "id")
    op.execute(sa.text("ALTER TABLE resume_templates RENAME COLUMN id_new TO id"))
    op.create_primary_key("resume_templates_pkey", "resume_templates", ["id"])

    op.create_foreign_key(
        "resume_outputs_template_id_fkey",
        "resume_outputs",
        "resume_templates",
        ["template_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    raise NotImplementedError("Downgrade not supported for resume_templates UUID PK migration.")

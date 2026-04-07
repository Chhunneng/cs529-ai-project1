"""resume_outputs.template_id nullable; ON DELETE SET NULL.

Revision ID: 0006_resume_outputs_template_id_nullable
Revises: 0005_resume_templates_db_only_latex
Create Date: 2026-04-07
"""

import sqlalchemy as sa
from alembic import op

revision = "0006_resume_outputs_template_id_nullable"
down_revision = "0005_resume_templates_db_only_latex"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "resume_outputs_template_id_fkey",
        "resume_outputs",
        type_="foreignkey",
    )
    op.alter_column(
        "resume_outputs",
        "template_id",
        existing_type=sa.Text(),
        nullable=True,
    )
    op.create_foreign_key(
        "resume_outputs_template_id_fkey",
        "resume_outputs",
        "resume_templates",
        ["template_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    bind = op.get_bind()
    n = bind.execute(
        sa.text("SELECT count(*) FROM resume_outputs WHERE template_id IS NULL")
    ).scalar()
    if n is not None and int(n) > 0:
        raise RuntimeError(
            "Cannot downgrade: resume_outputs has NULL template_id; delete or fix those rows first."
        )

    op.drop_constraint(
        "resume_outputs_template_id_fkey",
        "resume_outputs",
        type_="foreignkey",
    )
    op.alter_column(
        "resume_outputs",
        "template_id",
        existing_type=sa.Text(),
        nullable=False,
    )
    op.create_foreign_key(
        "resume_outputs_template_id_fkey",
        "resume_outputs",
        "resume_templates",
        ["template_id"],
        ["id"],
        ondelete="RESTRICT",
    )

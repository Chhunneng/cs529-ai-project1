"""Add latex_source to resume_templates.

Revision ID: 0003_resume_templates_latex_source
Revises: 0002_resume_templates_outputs
Create Date: 2026-04-07
"""

import sqlalchemy as sa
from alembic import op


revision = "0003_resume_templates_latex_source"
down_revision = "0002_resume_templates_outputs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("resume_templates", sa.Column("latex_source", sa.Text(), nullable=True))
    op.add_column(
        "resume_templates",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("resume_templates", "updated_at")
    op.drop_column("resume_templates", "latex_source")


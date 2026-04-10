"""Add resume_templates.valid (LaTeX compile flag).

Revision ID: 0003_resume_templates_valid
Revises: 0002_drop_tpl_schema_json
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_resume_templates_valid"
down_revision = "0002_drop_tpl_schema_json"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "resume_templates",
        sa.Column("valid", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("resume_templates", "valid")

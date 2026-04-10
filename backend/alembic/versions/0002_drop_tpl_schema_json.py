"""Drop resume_templates.schema_json (no longer used).

Revision ID: 0002_drop_tpl_schema_json
Revises: 0001_baseline_pdf_first_chat
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0002_drop_tpl_schema_json"
down_revision = "0001_baseline_pdf_first_chat"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TABLE resume_templates DROP COLUMN IF EXISTS schema_json"))


def downgrade() -> None:
    op.add_column(
        "resume_templates",
        sa.Column(
            "schema_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )

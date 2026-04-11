"""Allow resume_outputs without a chat session (standalone ATS PDF exports).

Revision ID: 0005_outputs_session_null
Revises: 0004_drop_agent_runs
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0005_outputs_session_null"
down_revision = "0004_drop_agent_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "resume_outputs",
        "session_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM resume_outputs WHERE session_id IS NULL")
    )
    op.alter_column(
        "resume_outputs",
        "session_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )

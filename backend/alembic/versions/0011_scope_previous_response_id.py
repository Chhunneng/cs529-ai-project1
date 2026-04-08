"""Add previous_response_id tracking.

Revision ID: 0011_scope_previous_response_id
Revises: 0010_job_descriptions_drop_session_id
Create Date: 2026-04-08
"""

from alembic import op
import sqlalchemy as sa


revision = "0011_scope_previous_response_id"
down_revision = "0010_job_descriptions_drop_session_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent_sessions",
        sa.Column("previous_response_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "chat_messages",
        sa.Column("previous_response_id", sa.String(length=128), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("chat_messages", "previous_response_id")
    op.drop_column("agent_sessions", "previous_response_id")


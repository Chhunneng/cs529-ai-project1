"""Add openai_conversation_id to agent_sessions.

Revision ID: 0004_agent_sessions_openai_conversation_id
Revises: 0003_resume_templates_latex_source
Create Date: 2026-04-07
"""

import sqlalchemy as sa
from alembic import op


revision = "0004_agent_sessions_openai_conversation_id"
down_revision = "0003_resume_templates_latex_source"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent_sessions",
        sa.Column("openai_conversation_id", sa.String(length=128), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("agent_sessions", "openai_conversation_id")

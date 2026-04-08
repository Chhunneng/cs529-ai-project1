"""Job descriptions: drop session_id (global JD rows; session uses active_jd_id only).

Revision ID: 0010_job_descriptions_drop_session_id
Revises: 0009_resume_upload_storage
Create Date: 2026-04-07
"""

from alembic import op
import sqlalchemy as sa


revision = "0010_job_descriptions_drop_session_id"
down_revision = "0009_resume_upload_storage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for fk in inspector.get_foreign_keys("job_descriptions"):
        cols = fk.get("constrained_columns") or []
        if "session_id" in cols and fk.get("referred_table") == "agent_sessions":
            op.drop_constraint(fk["name"], "job_descriptions", type_="foreignkey")
            break
    op.drop_column("job_descriptions", "session_id")


def downgrade() -> None:
    # Restores column as nullable; pre-migration rows cannot be re-associated with sessions.
    op.add_column(
        "job_descriptions",
        sa.Column("session_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "job_descriptions_session_id_fkey",
        "job_descriptions",
        "agent_sessions",
        ["session_id"],
        ["id"],
        ondelete="CASCADE",
    )

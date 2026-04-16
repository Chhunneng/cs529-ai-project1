"""Interview practice tables.

Revision ID: 0006_interview_practice_tables
Revises: 0005_outputs_session_null
Create Date: 2026-04-16
"""

from alembic import op
import sqlalchemy as sa

from app.models.common import JSON_TYPE, UUID_TYPE


# revision identifiers, used by Alembic.
revision = "0006_interview_practice_tables"
down_revision = "0005_outputs_session_null"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "interview_practice_sessions",
        sa.Column("id", UUID_TYPE, primary_key=True, nullable=False),
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
        sa.Column(
            "resume_id",
            UUID_TYPE,
            sa.ForeignKey("resumes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "job_description_id",
            UUID_TYPE,
            sa.ForeignKey("job_descriptions.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    op.create_table(
        "interview_questions",
        sa.Column("id", UUID_TYPE, primary_key=True, nullable=False),
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
        sa.Column(
            "practice_session_id",
            UUID_TYPE,
            sa.ForeignKey("interview_practice_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("sample_answer", sa.Text(), nullable=False),
        sa.Column("metadata_json", JSON_TYPE, nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_index(
        "ix_interview_questions_practice_session_id",
        "interview_questions",
        ["practice_session_id"],
    )

    op.create_table(
        "interview_answer_attempts",
        sa.Column("id", UUID_TYPE, primary_key=True, nullable=False),
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
        sa.Column(
            "question_id",
            UUID_TYPE,
            sa.ForeignKey("interview_questions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_answer", sa.Text(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("refined_answer", sa.Text(), nullable=True),
        sa.Column("scores_json", JSON_TYPE, nullable=True),
    )
    op.create_index(
        "ix_interview_answer_attempts_question_id",
        "interview_answer_attempts",
        ["question_id"],
    )

    op.create_table(
        "interview_job_requests",
        sa.Column("id", UUID_TYPE, primary_key=True, nullable=False),
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
        sa.Column(
            "practice_session_id",
            UUID_TYPE,
            sa.ForeignKey("interview_practice_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'pending'")),
        sa.Column(
            "question_id",
            UUID_TYPE,
            sa.ForeignKey("interview_questions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "answer_attempt_id",
            UUID_TYPE,
            sa.ForeignKey("interview_answer_attempts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("result_json", JSON_TYPE, nullable=True),
        sa.Column("error_text", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_interview_job_requests_practice_session_id",
        "interview_job_requests",
        ["practice_session_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_interview_job_requests_practice_session_id", table_name="interview_job_requests")
    op.drop_table("interview_job_requests")

    op.drop_index("ix_interview_answer_attempts_question_id", table_name="interview_answer_attempts")
    op.drop_table("interview_answer_attempts")

    op.drop_index("ix_interview_questions_practice_session_id", table_name="interview_questions")
    op.drop_table("interview_questions")

    op.drop_table("interview_practice_sessions")


"""One saved answer per interview question.

Revision ID: 0007_unique_answer_per_question
Revises: 0006_interview_practice_tables
Create Date: 2026-04-16
"""

from alembic import op
from sqlalchemy import text


revision = "0007_unique_answer_per_question"
down_revision = "0006_interview_practice_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute(
            text(
                """
                DELETE FROM interview_answer_attempts a
                USING interview_answer_attempts b
                WHERE a.question_id = b.question_id
                  AND a.created_at < b.created_at
                """
            )
        )
    else:
        # SQLite: keep one row per question_id (newest rowid wins on ties).
        op.execute(
            text(
                """
                DELETE FROM interview_answer_attempts
                WHERE rowid NOT IN (
                    SELECT MAX(rowid) FROM interview_answer_attempts GROUP BY question_id
                )
                """
            )
        )

    op.drop_index("ix_interview_answer_attempts_question_id", table_name="interview_answer_attempts")
    op.create_unique_constraint(
        "uq_interview_answer_attempts_question_id",
        "interview_answer_attempts",
        ["question_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_interview_answer_attempts_question_id", "interview_answer_attempts", type_="unique")
    op.create_index(
        "ix_interview_answer_attempts_question_id",
        "interview_answer_attempts",
        ["question_id"],
    )

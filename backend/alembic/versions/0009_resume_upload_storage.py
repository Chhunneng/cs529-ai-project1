"""Resume uploads: drop openai_file_id, add file metadata and content_text.

Revision ID: 0009_resume_upload_storage
Revises: 0008_change_main_class_to_common_class
Create Date: 2026-04-07
"""

from alembic import op
import sqlalchemy as sa


revision = "0009_resume_upload_storage"
down_revision = "0008_change_main_class_to_common_class"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("resumes", "openai_file_id")
    op.add_column("resumes", sa.Column("original_filename", sa.String(), nullable=True))
    op.add_column("resumes", sa.Column("mime_type", sa.String(), nullable=True))
    op.add_column("resumes", sa.Column("byte_size", sa.Integer(), nullable=True))
    op.add_column("resumes", sa.Column("storage_relpath", sa.String(), nullable=True))
    op.add_column("resumes", sa.Column("content_text", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("resumes", "content_text")
    op.drop_column("resumes", "storage_relpath")
    op.drop_column("resumes", "byte_size")
    op.drop_column("resumes", "mime_type")
    op.drop_column("resumes", "original_filename")
    op.add_column(
        "resumes",
        sa.Column("openai_file_id", sa.String(), nullable=True),
    )

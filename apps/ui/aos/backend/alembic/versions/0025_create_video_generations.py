"""create video_generations table for Manim chat jobs + MinIO keys

Revision ID: 0025
Revises: 0024_create_webhook_tables
Create Date: 2026-08-05
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0025"
down_revision = "0024_create_webhook_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "video_generations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assistant_message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("minio_bucket", sa.String(length=255), nullable=True),
        sa.Column("minio_key", sa.String(length=500), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("run_dir", sa.String(length=1000), nullable=True),
        sa.Column("celery_task_id", sa.String(length=255), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_message_id"], ["messages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assistant_message_id"], ["messages.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_video_generations_user_id", "video_generations", ["user_id"])
    op.create_index(
        "ix_video_generations_conversation_id", "video_generations", ["conversation_id"]
    )
    op.create_index("ix_video_generations_status", "video_generations", ["status"])


def downgrade() -> None:
    op.drop_index("ix_video_generations_status", table_name="video_generations")
    op.drop_index("ix_video_generations_conversation_id", table_name="video_generations")
    op.drop_index("ix_video_generations_user_id", table_name="video_generations")
    op.drop_table("video_generations")

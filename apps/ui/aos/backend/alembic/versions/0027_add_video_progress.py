"""add progress_stage and progress_message on video_generations

Revision ID: 0027
Revises: 0026
Create Date: 2026-08-19
"""

import sqlalchemy as sa

from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "video_generations",
        sa.Column("progress_stage", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "video_generations",
        sa.Column("progress_message", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("video_generations", "progress_message")
    op.drop_column("video_generations", "progress_stage")

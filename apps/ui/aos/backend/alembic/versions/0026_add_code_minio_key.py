"""add code_minio_key for uploaded Manim/Python scene source

Revision ID: 0026
Revises: 0025
Create Date: 2026-08-13
"""

import sqlalchemy as sa

from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "video_generations",
        sa.Column("code_minio_key", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("video_generations", "code_minio_key")

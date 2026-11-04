"""add url_camera_motion to inference

Revision ID: 20261029_01
Revises: 20261001_01
Create Date: 2026-10-29 00:00:00.000000

Nullable column so tasks processed before this migration continue to work
without a camera_motion.json file.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20261029_01"
down_revision: Union[str, None] = "20261001_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "inference",
        sa.Column("url_camera_motion", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("inference", "url_camera_motion")

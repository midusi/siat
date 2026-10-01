"""add progress to task

Revision ID: 20261001_01
Revises: e9c274f8934e
Create Date: 2026-10-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20261001_01"
down_revision: Union[str, None] = "e9c274f8934e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "task",
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("task", "progress", server_default=None)


def downgrade() -> None:
    op.drop_column("task", "progress")

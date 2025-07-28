"""Fusionar ramas de migracion divergentes

Revision ID: cab864075a21
Revises: b04859df28cb, bf69e36fa4fd
Create Date: 2025-07-23 16:05:20.001311

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'cab864075a21'
down_revision: Union[str, None] = ('b04859df28cb', 'bf69e36fa4fd')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

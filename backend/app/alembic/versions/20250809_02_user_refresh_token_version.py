"""add refresh_token_version to user

Revision ID: 20250809_02
Revises: 20250809_01
Create Date: 2025-08-09 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20250809_02'
down_revision: Union[str, None] = '20250809_01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('user', sa.Column('refresh_token_version', sa.Integer(), nullable=False, server_default='0'))
    op.alter_column('user', 'refresh_token_version', server_default=None)


def downgrade() -> None:
    op.drop_column('user', 'refresh_token_version')

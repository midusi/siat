"""user constraints and indexes

Revision ID: 20250809_01
Revises: cb9a4d59ecec
Create Date: 2025-08-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20250809_01'
down_revision: Union[str, None] = 'cb9a4d59ecec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # Drop unique constraint on password if it exists
    uniques = insp.get_unique_constraints('user')
    password_uc_name = None
    for uc in uniques:
        cols = uc.get('column_names') or []
        if cols == ['password'] or 'password' in cols:
            password_uc_name = uc.get('name')
            break
    if password_uc_name:
        op.drop_constraint(password_uc_name, 'user', type_='unique')

    # Ensure unique on email exists
    uniques = insp.get_unique_constraints('user')  # refresh
    has_email_unique = any(('email' in (uc.get('column_names') or [])) for uc in uniques)
    if not has_email_unique:
        op.create_unique_constraint('uq_user_email', 'user', ['email'])

    # Create indexes if not exist
    op.execute('CREATE INDEX IF NOT EXISTS ix_user_username ON "user" (username)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_user_email ON "user" (email)')


def downgrade() -> None:
    # Drop indexes if exist
    op.execute('DROP INDEX IF EXISTS ix_user_email')
    op.execute('DROP INDEX IF EXISTS ix_user_username')
    # Drop unique on email if exists
    op.execute('ALTER TABLE "user" DROP CONSTRAINT IF EXISTS uq_user_email')

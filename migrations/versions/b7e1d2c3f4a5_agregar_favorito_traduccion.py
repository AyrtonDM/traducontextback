"""agregar favorito a traduccion

Revision ID: b7e1d2c3f4a5
Revises: aa6d30637070
Create Date: 2026-11-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7e1d2c3f4a5'
down_revision: Union[str, Sequence[str], None] = 'aa6d30637070'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'traduccion',
        sa.Column('favorito', sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('traduccion', 'favorito')

"""glosario en conversaciones (HU-32): id_glosario opcional en conversacion

Revision ID: d6a8c0e2f4b6
Revises: c4e6a8b0d2f3
Create Date: 2026-11-19 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd6a8c0e2f4b6'
down_revision: Union[str, Sequence[str], None] = 'c4e6a8b0d2f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'conversacion',
        sa.Column('id_glosario', sa.Integer(), nullable=True),
    )
    # Si se elimina el glosario, la conversacion simplemente queda sin glosario
    op.create_foreign_key(
        'fk_conversacion_glosario',
        'conversacion',
        'glosario',
        ['id_glosario'],
        ['id_glosario'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_conversacion_glosario', 'conversacion', type_='foreignkey')
    op.drop_column('conversacion', 'id_glosario')

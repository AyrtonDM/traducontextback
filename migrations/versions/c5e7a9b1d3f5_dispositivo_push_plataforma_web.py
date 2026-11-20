"""dispositivo_push: permitir la plataforma 'web' (push del navegador)

Revision ID: c5e7a9b1d3f5
Revises: b2d4f6a8c0e1
Create Date: 2026-11-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'c5e7a9b1d3f5'
down_revision: Union[str, Sequence[str], None] = 'b2d4f6a8c0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NOMBRE_RESTRICCION = 'ck_dispositivo_push_plataforma'
TABLA = 'dispositivo_push'


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint(NOMBRE_RESTRICCION, TABLA, type_='check')
    op.create_check_constraint(
        NOMBRE_RESTRICCION,
        TABLA,
        "plataforma IN ('android', 'ios', 'web')",
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Los navegadores registrados no caben en la restriccion anterior: se eliminan antes
    op.execute("DELETE FROM dispositivo_push WHERE plataforma = 'web'")
    op.drop_constraint(NOMBRE_RESTRICCION, TABLA, type_='check')
    op.create_check_constraint(
        NOMBRE_RESTRICCION,
        TABLA,
        "plataforma IN ('android', 'ios')",
    )

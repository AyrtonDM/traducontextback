"""estado SUSPENDIDO para usuarios (HU-05)

Revision ID: c4e6a8b0d2f3
Revises: a8b3c5d7e9f1
Create Date: 2026-11-19 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'c4e6a8b0d2f3'
down_revision: Union[str, Sequence[str], None] = 'a8b3c5d7e9f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint('ck_usuario_estado', 'usuario', type_='check')
    op.create_check_constraint(
        'ck_usuario_estado',
        'usuario',
        "estado in ('ACTIVO', 'INACTIVO', 'SUSPENDIDO')",
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Las cuentas suspendidas vuelven a ACTIVO para respetar la restriccion anterior
    op.execute("UPDATE usuario SET estado = 'ACTIVO' WHERE estado = 'SUSPENDIDO'")
    op.drop_constraint('ck_usuario_estado', 'usuario', type_='check')
    op.create_check_constraint(
        'ck_usuario_estado',
        'usuario',
        "estado in ('ACTIVO', 'INACTIVO')",
    )

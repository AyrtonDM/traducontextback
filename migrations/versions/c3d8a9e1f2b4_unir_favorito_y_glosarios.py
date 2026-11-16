"""unir favorito (HU-43/45) y glosarios

Revision ID: c3d8a9e1f2b4
Revises: b7e1d2c3f4a5, b7e4c2d9f1a3
Create Date: 2026-11-16 10:00:00.000000

"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = 'c3d8a9e1f2b4'
down_revision: Union[str, Sequence[str], None] = ('b7e1d2c3f4a5', 'b7e4c2d9f1a3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Migracion de union: no modifica el esquema, solo une las dos ramas."""
    pass


def downgrade() -> None:
    """Migracion de union: no modifica el esquema."""
    pass

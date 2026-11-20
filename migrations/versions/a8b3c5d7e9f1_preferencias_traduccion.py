"""preferencias de traduccion (HU-33): idioma de destino y glosario predeterminados

Revision ID: a8b3c5d7e9f1
Revises: f7c9d1e3a5b7
Create Date: 2026-11-19 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a8b3c5d7e9f1'
down_revision: Union[str, Sequence[str], None] = 'f7c9d1e3a5b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'configuracion_traduccion',
        sa.Column('id_idioma_destino', sa.Integer(), nullable=True),
    )
    op.add_column(
        'configuracion_traduccion',
        sa.Column('id_glosario', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_configuracion_traduccion_idioma_destino',
        'configuracion_traduccion',
        'idioma',
        ['id_idioma_destino'],
        ['id_idioma'],
    )
    # Si se elimina el glosario, la preferencia simplemente queda sin glosario
    op.create_foreign_key(
        'fk_configuracion_traduccion_glosario',
        'configuracion_traduccion',
        'glosario',
        ['id_glosario'],
        ['id_glosario'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        'fk_configuracion_traduccion_glosario',
        'configuracion_traduccion',
        type_='foreignkey',
    )
    op.drop_constraint(
        'fk_configuracion_traduccion_idioma_destino',
        'configuracion_traduccion',
        type_='foreignkey',
    )
    op.drop_column('configuracion_traduccion', 'id_glosario')
    op.drop_column('configuracion_traduccion', 'id_idioma_destino')

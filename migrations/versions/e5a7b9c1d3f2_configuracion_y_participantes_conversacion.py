"""configuracion de conversacion (tono, descripcion, opciones) y participantes (HU-29, HU-31)

Revision ID: e5a7b9c1d3f2
Revises: d4f1a2b3c5e6
Create Date: 2026-11-17 15:00:00.000000

Agrega a 'conversacion' el tono (catalogo de HU-15), la descripcion personalizada del
contexto y los interruptores "mantener contexto" y "asistencia conversacional".
Crea 'participante_conversacion' (dos por sesion) y rellena los participantes de las
conversaciones existentes con SQL: el 1 con el idioma de origen y el 2 con el de destino.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5a7b9c1d3f2'
down_revision: Union[str, Sequence[str], None] = 'd4f1a2b3c5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('conversacion', sa.Column('id_tono', sa.Integer(), nullable=True))
    op.add_column('conversacion', sa.Column('descripcion_contexto', sa.Text(), nullable=True))
    op.add_column(
        'conversacion',
        sa.Column('mantener_contexto', sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.add_column(
        'conversacion',
        sa.Column(
            'asistencia_conversacional', sa.Boolean(), server_default=sa.false(), nullable=False
        ),
    )
    op.create_foreign_key(
        'fk_conversacion_id_tono_tono',
        'conversacion',
        'tono',
        ['id_tono'],
        ['id_tono'],
        ondelete='SET NULL',
    )

    op.create_table(
        'participante_conversacion',
        sa.Column('id_participante', sa.Integer(), nullable=False),
        sa.Column('id_conversacion', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(length=100), nullable=False),
        sa.Column('id_idioma', sa.Integer(), nullable=False),
        sa.Column('orden', sa.Integer(), nullable=False),
        sa.CheckConstraint('orden IN (1, 2)', name='ck_participante_conversacion_orden'),
        sa.ForeignKeyConstraint(
            ['id_conversacion'], ['conversacion.id_conversacion'], ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(['id_idioma'], ['idioma.id_idioma']),
        sa.PrimaryKeyConstraint('id_participante'),
        sa.UniqueConstraint(
            'id_conversacion', 'orden', name='uq_participante_conversacion_orden'
        ),
    )
    op.create_index(
        op.f('ix_participante_conversacion_id_participante'),
        'participante_conversacion',
        ['id_participante'],
        unique=False,
    )
    op.create_index(
        op.f('ix_participante_conversacion_id_conversacion'),
        'participante_conversacion',
        ['id_conversacion'],
        unique=False,
    )

    # Relleno de las conversaciones existentes
    op.execute(
        """
        INSERT INTO participante_conversacion (id_conversacion, nombre, id_idioma, orden)
        SELECT id_conversacion, 'Participante 1', id_idioma_origen, 1 FROM conversacion
        UNION ALL
        SELECT id_conversacion, 'Participante 2', id_idioma_destino, 2 FROM conversacion
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f('ix_participante_conversacion_id_conversacion'),
        table_name='participante_conversacion',
    )
    op.drop_index(
        op.f('ix_participante_conversacion_id_participante'),
        table_name='participante_conversacion',
    )
    op.drop_table('participante_conversacion')

    op.drop_constraint('fk_conversacion_id_tono_tono', 'conversacion', type_='foreignkey')
    op.drop_column('conversacion', 'asistencia_conversacional')
    op.drop_column('conversacion', 'mantener_contexto')
    op.drop_column('conversacion', 'descripcion_contexto')
    op.drop_column('conversacion', 'id_tono')

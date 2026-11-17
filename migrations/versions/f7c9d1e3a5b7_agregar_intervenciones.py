"""agregar intervenciones de conversacion (HU-26, HU-27, HU-31)

Revision ID: f7c9d1e3a5b7
Revises: e5a7b9c1d3f2
Create Date: 2026-11-17 18:00:00.000000

Crea 'intervencion': texto original del participante que habla, traduccion al idioma del
otro participante, estado (procesando, traducida, error) y orden secuencial por conversacion.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7c9d1e3a5b7'
down_revision: Union[str, Sequence[str], None] = 'e5a7b9c1d3f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'intervencion',
        sa.Column('id_intervencion', sa.Integer(), nullable=False),
        sa.Column('id_conversacion', sa.Integer(), nullable=False),
        sa.Column('id_participante', sa.Integer(), nullable=True),
        sa.Column('orden', sa.Integer(), nullable=False),
        sa.Column('texto_original', sa.Text(), nullable=False),
        sa.Column('texto_traducido', sa.Text(), nullable=True),
        sa.Column('id_idioma_origen', sa.Integer(), nullable=False),
        sa.Column('id_idioma_destino', sa.Integer(), nullable=False),
        sa.Column(
            'estado',
            sa.String(length=20),
            server_default='procesando',
            nullable=False,
        ),
        sa.Column('mensaje_error', sa.Text(), nullable=True),
        sa.Column(
            'fecha_creacion',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column('fecha_actualizacion', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "estado IN ('procesando', 'traducida', 'error')",
            name='ck_intervencion_estado',
        ),
        sa.CheckConstraint(
            'id_idioma_origen <> id_idioma_destino',
            name='ck_intervencion_idiomas_distintos',
        ),
        sa.ForeignKeyConstraint(
            ['id_conversacion'], ['conversacion.id_conversacion'], ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['id_participante'],
            ['participante_conversacion.id_participante'],
            ondelete='SET NULL',
        ),
        sa.ForeignKeyConstraint(['id_idioma_origen'], ['idioma.id_idioma']),
        sa.ForeignKeyConstraint(['id_idioma_destino'], ['idioma.id_idioma']),
        sa.PrimaryKeyConstraint('id_intervencion'),
        sa.UniqueConstraint(
            'id_conversacion', 'orden', name='uq_intervencion_conversacion_orden'
        ),
    )
    op.create_index(
        op.f('ix_intervencion_id_intervencion'),
        'intervencion',
        ['id_intervencion'],
        unique=False,
    )
    op.create_index(
        op.f('ix_intervencion_id_conversacion'),
        'intervencion',
        ['id_conversacion'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_intervencion_id_conversacion'), table_name='intervencion')
    op.drop_index(op.f('ix_intervencion_id_intervencion'), table_name='intervencion')
    op.drop_table('intervencion')

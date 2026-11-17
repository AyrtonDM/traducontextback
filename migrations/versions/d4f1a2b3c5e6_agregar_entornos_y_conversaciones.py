"""agregar entornos (HU-24) y conversaciones (HU-23)

Revision ID: d4f1a2b3c5e6
Revises: c3d8a9e1f2b4
Create Date: 2026-11-17 12:00:00.000000

Crea el catalogo 'entorno' (los valores base los inserta el seed al iniciar la app)
y la tabla 'conversacion' con su estado (activa, pausada, finalizada).

Las futuras intervenciones referenciaran a la conversacion asi:

    CREATE TABLE intervencion (
        id_intervencion SERIAL PRIMARY KEY,
        id_conversacion INTEGER NOT NULL
            REFERENCES conversacion(id_conversacion) ON DELETE CASCADE,
        ...
    );
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4f1a2b3c5e6'
down_revision: Union[str, Sequence[str], None] = 'c3d8a9e1f2b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'entorno',
        sa.Column('id_entorno', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(length=50), nullable=False),
        sa.Column('descripcion', sa.Text(), nullable=True),
        sa.Column('activo', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id_entorno'),
        sa.UniqueConstraint('nombre'),
    )
    op.create_index(op.f('ix_entorno_id_entorno'), 'entorno', ['id_entorno'], unique=False)

    op.create_table(
        'conversacion',
        sa.Column('id_conversacion', sa.Integer(), nullable=False),
        sa.Column(
            'estado',
            sa.String(length=20),
            server_default='activa',
            nullable=False,
        ),
        sa.Column(
            'fecha_inicio',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column('fecha_actualizacion', sa.DateTime(timezone=True), nullable=True),
        sa.Column('fecha_fin', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id_usuario', sa.Integer(), nullable=False),
        sa.Column('id_idioma_origen', sa.Integer(), nullable=False),
        sa.Column('id_idioma_destino', sa.Integer(), nullable=False),
        sa.Column('id_contexto', sa.Integer(), nullable=True),
        sa.Column('id_entorno', sa.Integer(), nullable=False),
        sa.CheckConstraint(
            'id_idioma_origen <> id_idioma_destino',
            name='ck_conversacion_idiomas_distintos',
        ),
        sa.CheckConstraint(
            "estado IN ('activa', 'pausada', 'finalizada')",
            name='ck_conversacion_estado',
        ),
        sa.ForeignKeyConstraint(['id_usuario'], ['usuario.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['id_idioma_origen'], ['idioma.id_idioma']),
        sa.ForeignKeyConstraint(['id_idioma_destino'], ['idioma.id_idioma']),
        sa.ForeignKeyConstraint(
            ['id_contexto'], ['contexto.id_contexto'], ondelete='SET NULL'
        ),
        sa.ForeignKeyConstraint(['id_entorno'], ['entorno.id_entorno']),
        sa.PrimaryKeyConstraint('id_conversacion'),
    )
    op.create_index(
        op.f('ix_conversacion_id_conversacion'),
        'conversacion',
        ['id_conversacion'],
        unique=False,
    )
    op.create_index(
        op.f('ix_conversacion_id_usuario'),
        'conversacion',
        ['id_usuario'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_conversacion_id_usuario'), table_name='conversacion')
    op.drop_index(op.f('ix_conversacion_id_conversacion'), table_name='conversacion')
    op.drop_table('conversacion')

    op.drop_index(op.f('ix_entorno_id_entorno'), table_name='entorno')
    op.drop_table('entorno')

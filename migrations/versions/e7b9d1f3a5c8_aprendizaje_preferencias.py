"""aprendizaje de preferencias (HU-34): correcciones del usuario e interruptor de aprendizaje

Revision ID: e7b9d1f3a5c8
Revises: d6a8c0e2f4b6
Create Date: 2026-11-19 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7b9d1f3a5c8'
down_revision: Union[str, Sequence[str], None] = 'd6a8c0e2f4b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'usuario',
        sa.Column('aprendizaje_activo', sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.create_table(
        'correccion_traduccion',
        sa.Column('id_correccion', sa.Integer(), nullable=False),
        sa.Column('id_usuario', sa.Integer(), nullable=False),
        sa.Column('id_idioma_origen', sa.Integer(), nullable=False),
        sa.Column('id_idioma_destino', sa.Integer(), nullable=False),
        sa.Column('texto_original', sa.Text(), nullable=False),
        sa.Column('traduccion_generada', sa.Text(), nullable=False),
        sa.Column('traduccion_corregida', sa.Text(), nullable=False),
        sa.Column('tipo', sa.String(length=20), nullable=False),
        sa.Column('fecha_creacion', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('fecha_actualizacion', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("tipo IN ('correccion', 'alternativa')", name='ck_correccion_traduccion_tipo'),
        sa.CheckConstraint(
            'id_idioma_origen <> id_idioma_destino',
            name='ck_correccion_traduccion_idiomas_distintos',
        ),
        sa.ForeignKeyConstraint(['id_usuario'], ['usuario.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['id_idioma_origen'], ['idioma.id_idioma']),
        sa.ForeignKeyConstraint(['id_idioma_destino'], ['idioma.id_idioma']),
        sa.PrimaryKeyConstraint('id_correccion'),
    )
    op.create_index(
        op.f('ix_correccion_traduccion_id_correccion'),
        'correccion_traduccion',
        ['id_correccion'],
        unique=False,
    )
    op.create_index(
        'ix_correccion_traduccion_usuario_par',
        'correccion_traduccion',
        ['id_usuario', 'id_idioma_origen', 'id_idioma_destino'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_correccion_traduccion_usuario_par', table_name='correccion_traduccion')
    op.drop_index(op.f('ix_correccion_traduccion_id_correccion'), table_name='correccion_traduccion')
    op.drop_table('correccion_traduccion')
    op.drop_column('usuario', 'aprendizaje_activo')

"""integraciones con Google Meet y Zoom (HU-35 a HU-41): conexiones OAuth y sesiones externas

Revision ID: f9c1e3a5b7d9
Revises: e7b9d1f3a5c8
Create Date: 2026-11-19 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f9c1e3a5b7d9'
down_revision: Union[str, Sequence[str], None] = 'e7b9d1f3a5c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'conexion_plataforma',
        sa.Column('id_conexion', sa.Integer(), nullable=False),
        sa.Column('id_usuario', sa.Integer(), nullable=False),
        sa.Column('plataforma', sa.String(length=20), nullable=False),
        sa.Column('access_token_cifrado', sa.Text(), nullable=False),
        sa.Column('refresh_token_cifrado', sa.Text(), nullable=True),
        sa.Column('fecha_expiracion', sa.DateTime(timezone=True), nullable=True),
        sa.Column('alcances', sa.Text(), nullable=True),
        sa.Column('cuenta_externa', sa.String(length=255), nullable=True),
        sa.Column('fecha_creacion', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('fecha_actualizacion', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("plataforma IN ('google_meet', 'zoom')", name='ck_conexion_plataforma_plataforma'),
        sa.ForeignKeyConstraint(['id_usuario'], ['usuario.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id_conexion'),
        sa.UniqueConstraint('id_usuario', 'plataforma', name='uq_conexion_plataforma_usuario'),
    )
    op.create_index(op.f('ix_conexion_plataforma_id_conexion'), 'conexion_plataforma', ['id_conexion'])
    op.create_index(op.f('ix_conexion_plataforma_id_usuario'), 'conexion_plataforma', ['id_usuario'])

    op.create_table(
        'sesion_externa',
        sa.Column('id_sesion_externa', sa.Integer(), nullable=False),
        sa.Column('id_usuario', sa.Integer(), nullable=False),
        sa.Column('plataforma', sa.String(length=20), nullable=False),
        sa.Column('enlace_reunion', sa.Text(), nullable=False),
        sa.Column('referencia_reunion', sa.String(length=64), nullable=False),
        sa.Column('estado', sa.String(length=20), server_default='configurada', nullable=False),
        sa.Column('id_idioma_origen', sa.Integer(), nullable=False),
        sa.Column('id_idioma_destino', sa.Integer(), nullable=False),
        sa.Column('id_contexto', sa.Integer(), nullable=True),
        sa.Column('id_entorno', sa.Integer(), nullable=False),
        sa.Column('id_tono', sa.Integer(), nullable=True),
        sa.Column('id_glosario', sa.Integer(), nullable=True),
        sa.Column('descripcion_contexto', sa.Text(), nullable=True),
        sa.Column('fecha_creacion', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('fecha_inicio', sa.DateTime(timezone=True), nullable=True),
        sa.Column('fecha_actualizacion', sa.DateTime(timezone=True), nullable=True),
        sa.Column('fecha_fin', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("plataforma IN ('google_meet', 'zoom')", name='ck_sesion_externa_plataforma'),
        sa.CheckConstraint(
            "estado IN ('configurada', 'activa', 'pausada', 'finalizada')",
            name='ck_sesion_externa_estado',
        ),
        sa.CheckConstraint('id_idioma_origen <> id_idioma_destino', name='ck_sesion_externa_idiomas_distintos'),
        sa.ForeignKeyConstraint(['id_usuario'], ['usuario.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['id_idioma_origen'], ['idioma.id_idioma']),
        sa.ForeignKeyConstraint(['id_idioma_destino'], ['idioma.id_idioma']),
        sa.ForeignKeyConstraint(['id_contexto'], ['contexto.id_contexto'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['id_entorno'], ['entorno.id_entorno']),
        sa.ForeignKeyConstraint(['id_tono'], ['tono.id_tono'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['id_glosario'], ['glosario.id_glosario'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id_sesion_externa'),
    )
    op.create_index(op.f('ix_sesion_externa_id_sesion_externa'), 'sesion_externa', ['id_sesion_externa'])
    op.create_index(op.f('ix_sesion_externa_id_usuario'), 'sesion_externa', ['id_usuario'])

    op.create_table(
        'participante_externo',
        sa.Column('id_participante', sa.Integer(), nullable=False),
        sa.Column('id_sesion_externa', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(length=100), nullable=False),
        sa.Column('orden', sa.Integer(), nullable=False),
        sa.Column('generico', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column('id_externo', sa.String(length=255), nullable=True),
        sa.Column('desde_plataforma', sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.ForeignKeyConstraint(['id_sesion_externa'], ['sesion_externa.id_sesion_externa'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id_participante'),
        sa.UniqueConstraint('id_sesion_externa', 'orden', name='uq_participante_externo_orden'),
    )
    op.create_index(op.f('ix_participante_externo_id_participante'), 'participante_externo', ['id_participante'])
    op.create_index(op.f('ix_participante_externo_id_sesion_externa'), 'participante_externo', ['id_sesion_externa'])

    op.create_table(
        'intervencion_externa',
        sa.Column('id_intervencion', sa.Integer(), nullable=False),
        sa.Column('id_sesion_externa', sa.Integer(), nullable=False),
        sa.Column('id_participante', sa.Integer(), nullable=True),
        sa.Column('orden', sa.Integer(), nullable=False),
        sa.Column('texto_original', sa.Text(), nullable=False),
        sa.Column('texto_traducido', sa.Text(), nullable=True),
        sa.Column('id_idioma_origen', sa.Integer(), nullable=True),
        sa.Column('id_idioma_destino', sa.Integer(), nullable=True),
        sa.Column('estado', sa.String(length=20), nullable=False),
        sa.Column('mensaje_error', sa.Text(), nullable=True),
        sa.Column('fecha_creacion', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('fecha_actualizacion', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "estado IN ('procesando', 'traducida', 'error')",
            name='ck_intervencion_externa_estado',
        ),
        sa.ForeignKeyConstraint(['id_sesion_externa'], ['sesion_externa.id_sesion_externa'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['id_participante'], ['participante_externo.id_participante'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['id_idioma_origen'], ['idioma.id_idioma']),
        sa.ForeignKeyConstraint(['id_idioma_destino'], ['idioma.id_idioma']),
        sa.PrimaryKeyConstraint('id_intervencion'),
        sa.UniqueConstraint('id_sesion_externa', 'orden', name='uq_intervencion_externa_orden'),
    )
    op.create_index(op.f('ix_intervencion_externa_id_intervencion'), 'intervencion_externa', ['id_intervencion'])
    op.create_index(op.f('ix_intervencion_externa_id_sesion_externa'), 'intervencion_externa', ['id_sesion_externa'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_intervencion_externa_id_sesion_externa'), table_name='intervencion_externa')
    op.drop_index(op.f('ix_intervencion_externa_id_intervencion'), table_name='intervencion_externa')
    op.drop_table('intervencion_externa')
    op.drop_index(op.f('ix_participante_externo_id_sesion_externa'), table_name='participante_externo')
    op.drop_index(op.f('ix_participante_externo_id_participante'), table_name='participante_externo')
    op.drop_table('participante_externo')
    op.drop_index(op.f('ix_sesion_externa_id_usuario'), table_name='sesion_externa')
    op.drop_index(op.f('ix_sesion_externa_id_sesion_externa'), table_name='sesion_externa')
    op.drop_table('sesion_externa')
    op.drop_index(op.f('ix_conexion_plataforma_id_usuario'), table_name='conexion_plataforma')
    op.drop_index(op.f('ix_conexion_plataforma_id_conexion'), table_name='conexion_plataforma')
    op.drop_table('conexion_plataforma')

"""notificaciones (M1): dispositivos para push FCM y bandeja de notificaciones

Revision ID: b2d4f6a8c0e1
Revises: f9c1e3a5b7d9
Create Date: 2026-11-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2d4f6a8c0e1'
down_revision: Union[str, Sequence[str], None] = 'f9c1e3a5b7d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'dispositivo_push',
        sa.Column('id_dispositivo', sa.Integer(), nullable=False),
        sa.Column('id_usuario', sa.Integer(), nullable=False),
        sa.Column('token_fcm', sa.String(length=512), nullable=False),
        sa.Column('plataforma', sa.String(length=20), nullable=False),
        sa.Column('activo', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column('fecha_registro', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('fecha_ultimo_uso', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("plataforma IN ('android', 'ios')", name='ck_dispositivo_push_plataforma'),
        sa.ForeignKeyConstraint(['id_usuario'], ['usuario.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id_dispositivo'),
        sa.UniqueConstraint('token_fcm'),
    )
    op.create_index(op.f('ix_dispositivo_push_id_dispositivo'), 'dispositivo_push', ['id_dispositivo'])
    op.create_index('ix_dispositivo_push_usuario_activo', 'dispositivo_push', ['id_usuario', 'activo'])

    op.create_table(
        'notificacion',
        sa.Column('id_notificacion', sa.Integer(), nullable=False),
        sa.Column('id_usuario', sa.Integer(), nullable=False),
        sa.Column('tipo', sa.String(length=40), nullable=False),
        sa.Column('titulo', sa.String(length=150), nullable=False),
        sa.Column('cuerpo', sa.String(length=500), nullable=False),
        sa.Column('datos', sa.JSON(), nullable=True),
        sa.Column('leida', sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column('fecha_creacion', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('fecha_lectura', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "tipo IN ('DOCUMENTO_LISTO', 'DOCUMENTO_ERROR', 'SISTEMA')",
            name='ck_notificacion_tipo',
        ),
        sa.ForeignKeyConstraint(['id_usuario'], ['usuario.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id_notificacion'),
    )
    op.create_index(op.f('ix_notificacion_id_notificacion'), 'notificacion', ['id_notificacion'])
    op.create_index(
        'ix_notificacion_usuario_leida_fecha',
        'notificacion',
        ['id_usuario', 'leida', 'fecha_creacion'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_notificacion_usuario_leida_fecha', table_name='notificacion')
    op.drop_index(op.f('ix_notificacion_id_notificacion'), table_name='notificacion')
    op.drop_table('notificacion')
    op.drop_index('ix_dispositivo_push_usuario_activo', table_name='dispositivo_push')
    op.drop_index(op.f('ix_dispositivo_push_id_dispositivo'), table_name='dispositivo_push')
    op.drop_table('dispositivo_push')

"""chats entre usuarios: chat, participante_chat, mensaje_chat, traduccion_mensaje_chat

Tambien agrega el tipo MENSAJE_CHAT a ck_notificacion_tipo.

Revision ID: d8f0a2c4e6b8
Revises: c5e7a9b1d3f5
Create Date: 2026-11-20 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8f0a2c4e6b8'
down_revision: Union[str, Sequence[str], None] = 'c5e7a9b1d3f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TIPOS_ANTERIORES = "tipo IN ('DOCUMENTO_LISTO', 'DOCUMENTO_ERROR', 'SISTEMA')"
TIPOS_NUEVOS = "tipo IN ('DOCUMENTO_LISTO', 'DOCUMENTO_ERROR', 'SISTEMA', 'MENSAJE_CHAT')"


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'chat',
        sa.Column('id_chat', sa.Integer(), nullable=False),
        sa.Column('id_usuario_menor', sa.Integer(), nullable=False),
        sa.Column('id_usuario_mayor', sa.Integer(), nullable=False),
        sa.Column('fecha_creacion', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('fecha_ultimo_mensaje', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint('id_usuario_menor < id_usuario_mayor', name='ck_chat_par_ordenado'),
        sa.ForeignKeyConstraint(['id_usuario_menor'], ['usuario.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['id_usuario_mayor'], ['usuario.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id_chat'),
        sa.UniqueConstraint('id_usuario_menor', 'id_usuario_mayor', name='uq_chat_par_usuarios'),
    )
    op.create_index(op.f('ix_chat_id_chat'), 'chat', ['id_chat'], unique=False)
    op.create_index('ix_chat_usuario_mayor', 'chat', ['id_usuario_mayor'], unique=False)

    op.create_table(
        'participante_chat',
        sa.Column('id_chat', sa.Integer(), nullable=False),
        sa.Column('id_usuario', sa.Integer(), nullable=False),
        sa.Column('id_idioma_lectura', sa.Integer(), nullable=False),
        sa.Column('id_ultimo_mensaje_leido', sa.Integer(), nullable=True),
        sa.Column('fecha_union', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('fecha_ultimo_acceso', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['id_chat'], ['chat.id_chat'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['id_usuario'], ['usuario.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['id_idioma_lectura'], ['idioma.id_idioma']),
        sa.PrimaryKeyConstraint('id_chat', 'id_usuario'),
    )
    op.create_index('ix_participante_chat_usuario', 'participante_chat', ['id_usuario'], unique=False)

    op.create_table(
        'mensaje_chat',
        sa.Column('id_mensaje', sa.Integer(), nullable=False),
        sa.Column('id_chat', sa.Integer(), nullable=False),
        sa.Column('id_remitente', sa.Integer(), nullable=False),
        sa.Column('texto_original', sa.String(length=2000), nullable=False),
        sa.Column('id_idioma_detectado', sa.Integer(), nullable=True),
        sa.Column('confianza_deteccion', sa.Float(), nullable=True),
        sa.Column('idioma_por_respaldo', sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column('estado', sa.String(length=20), server_default='pendiente', nullable=False),
        sa.Column('fecha_envio', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("estado IN ('pendiente', 'procesado', 'error')", name='ck_mensaje_chat_estado'),
        sa.ForeignKeyConstraint(['id_chat'], ['chat.id_chat'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['id_remitente'], ['usuario.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['id_idioma_detectado'], ['idioma.id_idioma'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id_mensaje'),
    )
    op.create_index(op.f('ix_mensaje_chat_id_mensaje'), 'mensaje_chat', ['id_mensaje'], unique=False)
    op.create_index('ix_mensaje_chat_chat_mensaje', 'mensaje_chat', ['id_chat', 'id_mensaje'], unique=False)
    op.create_index('ix_mensaje_chat_remitente_fecha', 'mensaje_chat', ['id_remitente', 'fecha_envio'], unique=False)

    op.create_table(
        'traduccion_mensaje_chat',
        sa.Column('id_traduccion', sa.Integer(), nullable=False),
        sa.Column('id_mensaje', sa.Integer(), nullable=False),
        sa.Column('id_destinatario', sa.Integer(), nullable=False),
        sa.Column('id_idioma_destino', sa.Integer(), nullable=False),
        sa.Column('texto_traducido', sa.Text(), nullable=True),
        sa.Column('estado', sa.String(length=20), server_default='pendiente', nullable=False),
        sa.Column('error', sa.String(length=300), nullable=True),
        sa.Column('fecha_actualizacion', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(
            "estado IN ('pendiente', 'traducido', 'sin_traduccion', 'error')",
            name='ck_traduccion_mensaje_chat_estado',
        ),
        sa.ForeignKeyConstraint(['id_mensaje'], ['mensaje_chat.id_mensaje'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['id_destinatario'], ['usuario.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['id_idioma_destino'], ['idioma.id_idioma']),
        sa.PrimaryKeyConstraint('id_traduccion'),
        sa.UniqueConstraint('id_mensaje', 'id_destinatario', name='uq_traduccion_mensaje_chat_destinatario'),
    )
    op.create_index(
        op.f('ix_traduccion_mensaje_chat_id_traduccion'), 'traduccion_mensaje_chat', ['id_traduccion'], unique=False
    )

    op.drop_constraint('ck_notificacion_tipo', 'notificacion', type_='check')
    op.create_check_constraint('ck_notificacion_tipo', 'notificacion', TIPOS_NUEVOS)


def downgrade() -> None:
    """Downgrade schema."""
    # Las notificaciones de chat no caben en la restriccion anterior: se eliminan antes
    op.execute("DELETE FROM notificacion WHERE tipo = 'MENSAJE_CHAT'")
    op.drop_constraint('ck_notificacion_tipo', 'notificacion', type_='check')
    op.create_check_constraint('ck_notificacion_tipo', 'notificacion', TIPOS_ANTERIORES)

    op.drop_index(op.f('ix_traduccion_mensaje_chat_id_traduccion'), table_name='traduccion_mensaje_chat')
    op.drop_table('traduccion_mensaje_chat')
    op.drop_index('ix_mensaje_chat_remitente_fecha', table_name='mensaje_chat')
    op.drop_index('ix_mensaje_chat_chat_mensaje', table_name='mensaje_chat')
    op.drop_index(op.f('ix_mensaje_chat_id_mensaje'), table_name='mensaje_chat')
    op.drop_table('mensaje_chat')
    op.drop_index('ix_participante_chat_usuario', table_name='participante_chat')
    op.drop_table('participante_chat')
    op.drop_index('ix_chat_usuario_mayor', table_name='chat')
    op.drop_index(op.f('ix_chat_id_chat'), table_name='chat')
    op.drop_table('chat')

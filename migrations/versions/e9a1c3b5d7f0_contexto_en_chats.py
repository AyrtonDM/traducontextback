"""contexto en chats: chat.id_contexto y chat.descripcion_contexto

Revision ID: e9a1c3b5d7f0
Revises: d8f0a2c4e6b8
Create Date: 2026-11-20 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e9a1c3b5d7f0'
down_revision: Union[str, Sequence[str], None] = 'd8f0a2c4e6b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('chat', sa.Column('id_contexto', sa.Integer(), nullable=True))
    op.add_column('chat', sa.Column('descripcion_contexto', sa.String(length=1000), nullable=True))
    op.create_foreign_key(
        'fk_chat_id_contexto_contexto',
        'chat',
        'contexto',
        ['id_contexto'],
        ['id_contexto'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_chat_id_contexto_contexto', 'chat', type_='foreignkey')
    op.drop_column('chat', 'descripcion_contexto')
    op.drop_column('chat', 'id_contexto')

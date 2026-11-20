"""agregar glosarios personalizados

Revision ID: b7e4c2d9f1a3
Revises: aa6d30637070
Create Date: 2026-11-16 12:00:00.000000

Crea las tablas 'glosario' y 'termino_glosario' y agrega la columna
'id_glosario' (un solo glosario por traduccion) a 'traduccion' y
'traduccion_documento'.

Si en el futuro se necesitan varios glosarios por traduccion, se reemplaza la
FK 'id_glosario' por una tabla intermedia, por ejemplo:

    CREATE TABLE traduccion_glosario (
        id_traduccion INTEGER NOT NULL REFERENCES traduccion(id_traduccion) ON DELETE CASCADE,
        id_glosario   INTEGER NOT NULL REFERENCES glosario(id_glosario)     ON DELETE CASCADE,
        prioridad     INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (id_traduccion, id_glosario)
    );
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7e4c2d9f1a3'
down_revision: Union[str, Sequence[str], None] = 'aa6d30637070'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'glosario',
        sa.Column('id_glosario', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(length=100), nullable=False),
        sa.Column('descripcion', sa.Text(), nullable=True),
        sa.Column(
            'fecha_creacion',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column('fecha_actualizacion', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id_usuario', sa.Integer(), nullable=False),
        sa.Column('id_idioma_origen', sa.Integer(), nullable=False),
        sa.Column('id_idioma_destino', sa.Integer(), nullable=False),
        sa.CheckConstraint(
            'id_idioma_origen <> id_idioma_destino',
            name='ck_glosario_idiomas_distintos',
        ),
        sa.ForeignKeyConstraint(['id_usuario'], ['usuario.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['id_idioma_origen'], ['idioma.id_idioma']),
        sa.ForeignKeyConstraint(['id_idioma_destino'], ['idioma.id_idioma']),
        sa.PrimaryKeyConstraint('id_glosario'),
    )
    op.create_index(op.f('ix_glosario_id_glosario'), 'glosario', ['id_glosario'], unique=False)
    op.create_index(op.f('ix_glosario_id_usuario'), 'glosario', ['id_usuario'], unique=False)

    op.create_table(
        'termino_glosario',
        sa.Column('id_termino_glosario', sa.Integer(), nullable=False),
        sa.Column('termino_origen', sa.String(length=255), nullable=False),
        sa.Column('traduccion_preferida', sa.String(length=255), nullable=True),
        sa.Column('conservar_original', sa.Boolean(), nullable=False),
        sa.Column('distinguir_mayusculas', sa.Boolean(), nullable=False),
        sa.Column('nota', sa.Text(), nullable=True),
        sa.Column('id_glosario', sa.Integer(), nullable=False),
        sa.CheckConstraint(
            'conservar_original OR traduccion_preferida IS NOT NULL',
            name='ck_termino_glosario_regla',
        ),
        sa.ForeignKeyConstraint(
            ['id_glosario'], ['glosario.id_glosario'], ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id_termino_glosario'),
    )
    op.create_index(
        op.f('ix_termino_glosario_id_termino_glosario'),
        'termino_glosario',
        ['id_termino_glosario'],
        unique=False,
    )
    op.create_index(
        op.f('ix_termino_glosario_id_glosario'),
        'termino_glosario',
        ['id_glosario'],
        unique=False,
    )

    op.add_column('traduccion', sa.Column('id_glosario', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'traduccion_id_glosario_fkey',
        'traduccion',
        'glosario',
        ['id_glosario'],
        ['id_glosario'],
        ondelete='SET NULL',
    )

    op.add_column(
        'traduccion_documento',
        sa.Column('id_glosario', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'traduccion_documento_id_glosario_fkey',
        'traduccion_documento',
        'glosario',
        ['id_glosario'],
        ['id_glosario'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        'traduccion_documento_id_glosario_fkey',
        'traduccion_documento',
        type_='foreignkey',
    )
    op.drop_column('traduccion_documento', 'id_glosario')

    op.drop_constraint('traduccion_id_glosario_fkey', 'traduccion', type_='foreignkey')
    op.drop_column('traduccion', 'id_glosario')

    op.drop_index(op.f('ix_termino_glosario_id_glosario'), table_name='termino_glosario')
    op.drop_index(
        op.f('ix_termino_glosario_id_termino_glosario'),
        table_name='termino_glosario',
    )
    op.drop_table('termino_glosario')

    op.drop_index(op.f('ix_glosario_id_usuario'), table_name='glosario')
    op.drop_index(op.f('ix_glosario_id_glosario'), table_name='glosario')
    op.drop_table('glosario')

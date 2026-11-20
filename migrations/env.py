from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.configuracion import configuracion
from app.database.base import Base
from app.database.conexion import url_base_datos

import app.models  # noqa: F401


# Configuracion de Alembic
config = context.config


# Configuracion del logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# Metadata de todos los modelos SQLAlchemy
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Ejecuta las migraciones sin crear una conexion."""

    url = url_base_datos.render_as_string(hide_password=False)

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Ejecuta las migraciones usando una conexion."""

    connectable = engine_from_config(
        {
            "sqlalchemy.url": url_base_datos.render_as_string(
                hide_password=False
            )
        },
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
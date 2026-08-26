from collections.abc import Generator

from sqlalchemy import URL, create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.configuracion import configuracion


url_base_datos = URL.create(
    drivername="postgresql+psycopg2",
    username=configuracion.db_user,
    password=configuracion.db_password,
    host=configuracion.db_host,
    port=configuracion.db_port,
    database=configuracion.db_name,
)


motor: Engine = create_engine(
    url_base_datos,
    echo=configuracion.db_echo,
    pool_pre_ping=True,
)


FabricaSesiones = sessionmaker(
    bind=motor,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def obtener_sesion() -> Generator[Session, None, None]:
    """Proporciona una sesion de base de datos."""

    sesion = FabricaSesiones()

    try:
        yield sesion
    finally:
        sesion.close()


def comprobar_conexion() -> None:
    """Comprueba que PostgreSQL responda correctamente."""

    with motor.connect() as conexion:
        resultado = conexion.execute(
            text("SELECT current_database(), current_user")
        )

        nombre_base_datos, usuario = resultado.one()

        print("Conexion realizada correctamente.")
        print(f"Base de datos: {nombre_base_datos}")
        print(f"Usuario: {usuario}")

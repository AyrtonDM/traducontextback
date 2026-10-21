import app.models  # noqa: F401
from app.database.base import Base
from app.database.conexion import FabricaSesiones, motor
from app.seeds.seed_contexto import sembrar_contextos
from app.seeds.seed_rol import sembrar_roles
from app.seeds.seed_idiomas import sembrar_idiomas
from app.seeds.seed_tono import sembrar_tonos
from app.seeds.seed_variante_regional import sembrar_variantes_regionales


def crear_tablas() -> None:
    """Crea las tablas registradas en SQLAlchemy."""

    Base.metadata.create_all(bind=motor)


def inicializar_base_datos() -> None:
    """Inicializa tablas y datos minimos del sistema."""

    crear_tablas()

    with FabricaSesiones() as sesion:
        sembrar_roles(sesion)
        sembrar_contextos(sesion)
        sembrar_idiomas(sesion)
        sembrar_tonos(sesion)
        sembrar_variantes_regionales(sesion)
        sesion.commit()

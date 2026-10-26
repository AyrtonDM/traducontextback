from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.traduccion.configuracion_traduccion import ConfiguracionTraduccion
from app.models.traduccion.contexto import Contexto
from app.models.traduccion.tono import Tono
from app.models.traduccion.variante_regional import VarianteRegional
from app.schemas.configuracion_traduccion import ConfiguracionTraduccionDetalle


def obtener_configuracion_usuario(
    sesion: Session,
    id_usuario: int,
) -> ConfiguracionTraduccion | None:
    """Obtiene la configuracion de traduccion asociada a un usuario."""
    return sesion.scalar(
        select(ConfiguracionTraduccion).where(
            ConfiguracionTraduccion.id_usuario == id_usuario
        )
    )


def armar_detalle_configuracion(
    config: ConfiguracionTraduccion,
    sesion: Session,
) -> ConfiguracionTraduccionDetalle:
    """Construye el esquema de detalle enriquecido de la configuracion."""
    nombre_contexto = None
    if config.id_contexto:
        ctx = sesion.scalar(select(Contexto).where(Contexto.id_contexto == config.id_contexto))
        nombre_contexto = ctx.nombre if ctx else None

    nombre_tono = None
    if config.id_tono:
        t = sesion.scalar(select(Tono).where(Tono.id_tono == config.id_tono))
        nombre_tono = t.nombre if t else None

    nombre_variante = None
    if config.id_variante_regional:
        vr = sesion.scalar(
            select(VarianteRegional).where(
                VarianteRegional.id_variante_regional == config.id_variante_regional
            )
        )
        nombre_variante = vr.nombre if vr else None

    return ConfiguracionTraduccionDetalle(
        id_configuracion_traduccion=config.id_configuracion_traduccion,
        id_contexto=config.id_contexto,
        id_tono=config.id_tono,
        id_variante_regional=config.id_variante_regional,
        id_usuario=config.id_usuario,
        explicar_expresiones=config.explicar_expresiones,
        generar_alternativas=config.generar_alternativas,
        nombre_contexto=nombre_contexto,
        nombre_tono=nombre_tono,
        nombre_variante_regional=nombre_variante,
    )


def guardar_o_actualizar_configuracion(
    sesion: Session,
    id_usuario: int,
    id_contexto: int,
    id_tono: int,
    id_variante_regional: int | None = None,
    explicar_expresiones: bool = False,
    generar_alternativas: bool = False,
) -> ConfiguracionTraduccion:
    """Guarda una nueva configuracion o actualiza la existente para el usuario."""
    # 1. Validar contexto
    contexto = sesion.scalar(
        select(Contexto).where(
            Contexto.id_contexto == id_contexto,
            Contexto.activo.is_(True),
        )
    )
    if not contexto:
        raise ValueError(f"Contexto con id {id_contexto} no encontrado o inactivo.")

    # 2. Validar tono
    tono = sesion.scalar(
        select(Tono).where(
            Tono.id_tono == id_tono,
            Tono.activo.is_(True),
        )
    )
    if not tono:
        raise ValueError(f"Tono con id {id_tono} no encontrado o inactivo.")

    # 3. Validar variante regional si llega
    if id_variante_regional is not None:
        variante = sesion.scalar(
            select(VarianteRegional).where(
                VarianteRegional.id_variante_regional == id_variante_regional,
                VarianteRegional.activo.is_(True),
            )
        )
        if not variante:
            raise ValueError(
                f"Variante regional con id {id_variante_regional} no encontrada o inactiva."
            )

    # 4. Buscar configuracion existente del usuario
    config = sesion.scalar(
        select(ConfiguracionTraduccion).where(
            ConfiguracionTraduccion.id_usuario == id_usuario
        )
    )

    if config:
        config.id_contexto = id_contexto
        config.id_tono = id_tono
        config.id_variante_regional = id_variante_regional
        config.explicar_expresiones = explicar_expresiones
        config.generar_alternativas = generar_alternativas
    else:
        config = ConfiguracionTraduccion(
            id_usuario=id_usuario,
            id_contexto=id_contexto,
            id_tono=id_tono,
            id_variante_regional=id_variante_regional,
            explicar_expresiones=explicar_expresiones,
            generar_alternativas=generar_alternativas,
        )
        sesion.add(config)

    sesion.commit()
    sesion.refresh(config)
    return config


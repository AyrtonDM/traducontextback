"""
Configuracion / preferencias de traduccion del usuario (HU-15 a HU-18 y HU-33).

La fila de `configuracion_traduccion` asociada al usuario guarda sus preferencias
predeterminadas: idioma de destino, contexto, tono, variante regional, glosario y
opciones de enriquecimiento. Una traduccion puntual puede sobrescribir cualquiera
de estos valores sin modificar lo guardado (ver `resolver_configuracion_efectiva`).
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.glosario.glosario import Glosario
from app.models.traduccion.configuracion_traduccion import ConfiguracionTraduccion
from app.models.traduccion.contexto import Contexto
from app.models.traduccion.idioma import Idioma
from app.models.traduccion.tono import Tono
from app.models.traduccion.variante_regional import VarianteRegional
from app.schemas.configuracion_traduccion import ConfiguracionTraduccionDetalle


# ---------------------------------------------------------------------------
# Validaciones reutilizables
# ---------------------------------------------------------------------------


def validar_contexto(sesion: Session, id_usuario: int, id_contexto: int) -> Contexto:
    """El contexto debe estar activo y ser general o propio del usuario."""
    contexto = sesion.scalar(
        select(Contexto).where(
            Contexto.id_contexto == id_contexto,
            Contexto.activo.is_(True),
            (Contexto.id_usuario.is_(None)) | (Contexto.id_usuario == id_usuario),
        )
    )
    if not contexto:
        raise ValueError(f"Contexto con id {id_contexto} no encontrado o inactivo.")
    return contexto


def validar_tono(sesion: Session, id_tono: int) -> Tono:
    tono = sesion.scalar(
        select(Tono).where(
            Tono.id_tono == id_tono,
            Tono.activo.is_(True),
        )
    )
    if not tono:
        raise ValueError(f"Tono con id {id_tono} no encontrado o inactivo.")
    return tono


def validar_variante(sesion: Session, id_variante_regional: int) -> VarianteRegional:
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
    return variante


def obtener_idioma_por_codigo(sesion: Session, codigo: str) -> Idioma:
    codigo_limpio = codigo.strip().lower()
    idioma = sesion.scalar(select(Idioma).where(Idioma.codigo == codigo_limpio))
    if not idioma:
        raise ValueError(f"El idioma de destino '{codigo_limpio}' no esta registrado.")
    return idioma


def validar_variante_compatible(variante: VarianteRegional, idioma: Idioma) -> None:
    if variante.id_idioma != idioma.id_idioma:
        raise ValueError(
            f"La variante regional '{variante.nombre}' no corresponde al idioma de destino "
            f"'{idioma.nombre}'."
        )


def validar_glosario_preferido(
    sesion: Session,
    id_usuario: int,
    id_glosario: int,
    idioma_destino: Idioma | None,
) -> Glosario:
    """El glosario debe ser del usuario y, si hay idioma preferido, de ese idioma de destino."""
    glosario = sesion.scalar(
        select(Glosario).where(
            Glosario.id_glosario == id_glosario,
            Glosario.id_usuario == id_usuario,
        )
    )
    if not glosario:
        raise ValueError(f"Glosario con id {id_glosario} no encontrado.")
    if idioma_destino is not None and glosario.id_idioma_destino != idioma_destino.id_idioma:
        raise ValueError(
            f"El glosario '{glosario.nombre}' no corresponde al idioma de destino "
            f"'{idioma_destino.nombre}'."
        )
    return glosario


# ---------------------------------------------------------------------------
# Consulta y armado de respuesta
# ---------------------------------------------------------------------------


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
    contexto = sesion.get(Contexto, config.id_contexto) if config.id_contexto else None
    tono = sesion.get(Tono, config.id_tono) if config.id_tono else None
    variante = (
        sesion.get(VarianteRegional, config.id_variante_regional)
        if config.id_variante_regional
        else None
    )
    idioma = sesion.get(Idioma, config.id_idioma_destino) if config.id_idioma_destino else None
    glosario = sesion.get(Glosario, config.id_glosario) if config.id_glosario else None

    return ConfiguracionTraduccionDetalle(
        id_configuracion_traduccion=config.id_configuracion_traduccion,
        id_contexto=config.id_contexto,
        id_tono=config.id_tono,
        id_variante_regional=config.id_variante_regional,
        id_usuario=config.id_usuario,
        id_idioma_destino=config.id_idioma_destino,
        id_glosario=config.id_glosario,
        explicar_expresiones=config.explicar_expresiones,
        generar_alternativas=config.generar_alternativas,
        nombre_contexto=contexto.nombre if contexto else None,
        nombre_tono=tono.nombre if tono else None,
        nombre_variante_regional=variante.nombre if variante else None,
        codigo_idioma_destino=idioma.codigo if idioma else None,
        nombre_idioma_destino=idioma.nombre if idioma else None,
        nombre_glosario=glosario.nombre if glosario else None,
    )


# ---------------------------------------------------------------------------
# Guardar / restablecer preferencias
# ---------------------------------------------------------------------------


def guardar_o_actualizar_configuracion(
    sesion: Session,
    id_usuario: int,
    id_contexto: int,
    id_tono: int,
    id_variante_regional: int | None = None,
    explicar_expresiones: bool = False,
    generar_alternativas: bool = False,
    idioma_destino: str | None = None,
    id_glosario: int | None = None,
) -> ConfiguracionTraduccion:
    """
    Guarda una nueva configuracion o actualiza la existente para el usuario.
    `idioma_destino` se guarda como idioma preferido y se usa para validar que la
    variante regional y el glosario sean compatibles (HU-33).
    """
    validar_contexto(sesion, id_usuario, id_contexto)
    validar_tono(sesion, id_tono)

    idioma_db = None
    if idioma_destino and idioma_destino.strip():
        idioma_db = obtener_idioma_por_codigo(sesion, idioma_destino)

    if id_variante_regional is not None:
        variante = validar_variante(sesion, id_variante_regional)
        if idioma_db is not None:
            validar_variante_compatible(variante, idioma_db)

    if id_glosario is not None:
        validar_glosario_preferido(sesion, id_usuario, id_glosario, idioma_db)

    config = obtener_configuracion_usuario(sesion, id_usuario)
    if config is None:
        config = ConfiguracionTraduccion(id_usuario=id_usuario)
        sesion.add(config)

    config.id_contexto = id_contexto
    config.id_tono = id_tono
    config.id_variante_regional = id_variante_regional
    config.explicar_expresiones = explicar_expresiones
    config.generar_alternativas = generar_alternativas
    config.id_idioma_destino = idioma_db.id_idioma if idioma_db else None
    config.id_glosario = id_glosario

    sesion.commit()
    sesion.refresh(config)
    return config


def _contexto_por_defecto(sesion: Session) -> Contexto:
    contexto = sesion.scalar(
        select(Contexto)
        .where(Contexto.activo.is_(True), Contexto.id_usuario.is_(None))
        .order_by(Contexto.id_contexto)
    )
    if not contexto:
        raise ValueError("No hay contextos generales activos para restablecer la configuracion.")
    return contexto


def _tono_por_defecto(sesion: Session) -> Tono:
    tono = sesion.scalar(
        select(Tono).where(Tono.activo.is_(True)).order_by(Tono.id_tono)
    )
    if not tono:
        raise ValueError("No hay tonos activos para restablecer la configuracion.")
    return tono


def restablecer_configuracion(sesion: Session, id_usuario: int) -> ConfiguracionTraduccion:
    """
    Restablece las preferencias a los valores por defecto del sistema: primer contexto
    general y primer tono activos, sin idioma, variante ni glosario, y sin enriquecimiento.

    No se elimina la fila porque las traducciones del historial la referencian.
    """
    contexto = _contexto_por_defecto(sesion)
    tono = _tono_por_defecto(sesion)

    config = obtener_configuracion_usuario(sesion, id_usuario)
    if config is None:
        config = ConfiguracionTraduccion(id_usuario=id_usuario)
        sesion.add(config)

    config.id_contexto = contexto.id_contexto
    config.id_tono = tono.id_tono
    config.id_variante_regional = None
    config.id_idioma_destino = None
    config.id_glosario = None
    config.explicar_expresiones = False
    config.generar_alternativas = False

    sesion.commit()
    sesion.refresh(config)
    return config


# ---------------------------------------------------------------------------
# Configuracion efectiva de una traduccion puntual
# ---------------------------------------------------------------------------


@dataclass
class ConfiguracionEfectiva:
    """Valores con los que se ejecuta una traduccion concreta (no se persisten)."""

    contexto: Contexto | None
    tono: Tono | None
    variante: VarianteRegional | None
    explicar_expresiones: bool
    generar_alternativas: bool


def resolver_configuracion_efectiva(
    sesion: Session,
    id_usuario: int,
    config: ConfiguracionTraduccion,
    sobrescritos: dict,
) -> ConfiguracionEfectiva:
    """
    Combina la configuracion guardada con los valores enviados para una traduccion puntual.
    `sobrescritos` solo contiene los campos que llegaron en la solicitud; un valor None en
    `id_variante_regional` o `id_tono` significa "sin variante" / "sin tono" para esta
    traduccion. La configuracion guardada no se modifica (HU-33).
    """
    if "id_contexto" in sobrescritos and sobrescritos["id_contexto"] is not None:
        contexto = validar_contexto(sesion, id_usuario, sobrescritos["id_contexto"])
    else:
        contexto = sesion.scalar(
            select(Contexto).where(
                Contexto.id_contexto == config.id_contexto,
                Contexto.activo.is_(True),
            )
        )

    if "id_tono" in sobrescritos:
        id_tono = sobrescritos["id_tono"]
        tono = validar_tono(sesion, id_tono) if id_tono is not None else None
    else:
        tono = sesion.get(Tono, config.id_tono) if config.id_tono else None

    if "id_variante_regional" in sobrescritos:
        id_variante = sobrescritos["id_variante_regional"]
        variante = validar_variante(sesion, id_variante) if id_variante is not None else None
    else:
        variante = (
            sesion.get(VarianteRegional, config.id_variante_regional)
            if config.id_variante_regional
            else None
        )

    explicar = sobrescritos.get("explicar_expresiones")
    alternativas = sobrescritos.get("generar_alternativas")

    return ConfiguracionEfectiva(
        contexto=contexto,
        tono=tono,
        variante=variante,
        explicar_expresiones=config.explicar_expresiones if explicar is None else explicar,
        generar_alternativas=config.generar_alternativas if alternativas is None else alternativas,
    )

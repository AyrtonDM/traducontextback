from datetime import date, datetime, time, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, aliased, joinedload

from app.models.traduccion.configuracion_traduccion import ConfiguracionTraduccion
from app.models.traduccion.idioma import Idioma
from app.models.traduccion.traduccion import Traduccion
from app.schemas.traduccion import TraduccionHistorialDetalle


def _escapar_like(texto: str) -> str:
    """Escapa los comodines de LIKE para que se busquen de forma literal."""
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def listar_historial(
    sesion: Session,
    id_usuario: int,
    texto: str | None = None,
    idioma_origen: str | None = None,
    idioma_destino: str | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    solo_favoritos: bool = False,
) -> list[TraduccionHistorialDetalle]:
    """Retorna el historial de traducciones del usuario aplicando los filtros combinados (AND)."""
    if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
        raise ValueError("La fecha desde no puede ser mayor que la fecha hasta.")

    IdiomaOrigen = aliased(Idioma)
    IdiomaDestino = aliased(Idioma)

    consulta = (
        select(Traduccion, IdiomaOrigen.codigo, IdiomaDestino.codigo)
        .join(IdiomaOrigen, Traduccion.id_idioma_origen == IdiomaOrigen.id_idioma)
        .join(IdiomaDestino, Traduccion.id_idioma_destino == IdiomaDestino.id_idioma)
        .options(
            joinedload(Traduccion.configuracion_traduccion).joinedload(ConfiguracionTraduccion.contexto),
            joinedload(Traduccion.configuracion_traduccion).joinedload(ConfiguracionTraduccion.tono),
            joinedload(Traduccion.configuracion_traduccion).joinedload(ConfiguracionTraduccion.variante_regional),
        )
        .where(Traduccion.id_usuario == id_usuario)
    )

    if texto and texto.strip():
        patron = f"%{_escapar_like(texto.strip())}%"
        consulta = consulta.where(
            or_(
                Traduccion.texto_original.ilike(patron, escape="\\"),
                Traduccion.texto_traducido.ilike(patron, escape="\\"),
            )
        )
    if idioma_origen:
        consulta = consulta.where(IdiomaOrigen.codigo == idioma_origen)
    if idioma_destino:
        consulta = consulta.where(IdiomaDestino.codigo == idioma_destino)
    if fecha_desde:
        consulta = consulta.where(
            Traduccion.fecha_creacion >= datetime.combine(fecha_desde, time.min)
        )
    if fecha_hasta:
        consulta = consulta.where(
            Traduccion.fecha_creacion < datetime.combine(fecha_hasta + timedelta(days=1), time.min)
        )
    if solo_favoritos:
        consulta = consulta.where(Traduccion.favorito.is_(True))

    consulta = consulta.order_by(Traduccion.fecha_creacion.desc(), Traduccion.id_traduccion.desc())

    historial: list[TraduccionHistorialDetalle] = []
    for traduccion, codigo_origen, codigo_destino in sesion.execute(consulta).unique().all():
        config = traduccion.configuracion_traduccion
        historial.append(
            TraduccionHistorialDetalle(
                id_traduccion=traduccion.id_traduccion,
                texto_original=traduccion.texto_original,
                texto_traducido=traduccion.texto_traducido,
                fecha_creacion=traduccion.fecha_creacion,
                idioma_origen=codigo_origen,
                idioma_destino=codigo_destino,
                nombre_contexto=config.contexto.nombre if config and config.contexto else None,
                nombre_tono=config.tono.nombre if config and config.tono else None,
                nombre_variante_regional=(
                    config.variante_regional.nombre if config and config.variante_regional else None
                ),
                explicar_expresiones=config.explicar_expresiones if config else False,
                generar_alternativas=config.generar_alternativas if config else False,
                favorito=traduccion.favorito,
            )
        )
    return historial


def obtener_traduccion_usuario(
    sesion: Session,
    id_traduccion: int,
    id_usuario: int,
) -> Traduccion | None:
    """Retorna la traduccion solo si pertenece al usuario indicado."""
    return sesion.scalar(
        select(Traduccion).where(
            Traduccion.id_traduccion == id_traduccion,
            Traduccion.id_usuario == id_usuario,
        )
    )


def definir_favorito(
    sesion: Session,
    traduccion: Traduccion,
    favorito: bool,
) -> Traduccion:
    """Marca o desmarca una traduccion como favorita."""
    traduccion.favorito = favorito
    sesion.commit()
    sesion.refresh(traduccion)
    return traduccion


def eliminar_traduccion(sesion: Session, traduccion: Traduccion) -> None:
    """Elimina una traduccion del historial. Ninguna tabla tiene FK hacia traduccion."""
    sesion.delete(traduccion)
    sesion.commit()

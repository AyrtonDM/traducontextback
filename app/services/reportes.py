"""
Reportes administrativos de actividad (HU-47).

Une en una sola consulta la actividad de los servicios (traducciones de texto, documentos,
conversaciones y sesiones externas de Meet/Zoom) con columnas comunes, para filtrar, totalizar y paginar de forma uniforme.
La misma funcion sirve para la exportacion (HU-48) pidiendo todas las filas sin paginar.

El detalle no incluye el contenido traducido por los usuarios: solo metadatos de la actividad.
"""

import math
from datetime import date, datetime, timezone

try:
    from datetime import UTC
except ImportError:
    UTC = timezone.utc

from sqlalchemy import Date, Integer, String, cast, func, literal, null, select, union_all
from sqlalchemy.orm import Session, aliased

from app.models.conversacion.conversacion import Conversacion
from app.models.conversacion.entorno import Entorno
from app.models.documento.traduccion_documento import TraduccionDocumento
from app.models.integracion.sesion_externa import SesionExterna
from app.models.traduccion.configuracion_traduccion import ConfiguracionTraduccion
from app.models.traduccion.contexto import Contexto
from app.models.traduccion.idioma import Idioma
from app.models.traduccion.traduccion import Traduccion
from app.models.usuario.usuario import Usuario
from app.schemas.reporte import (
    ActividadReporte,
    FiltrosReporte,
    ReporteActividad,
    TipoServicio,
    TotalesReporte,
)
from app.services.dashboard import PeriodoInvalidoError, resolver_periodo


TAMANO_PAGINA_POR_DEFECTO = 20


class FiltroReporteInvalidoError(ValueError):
    pass


class ReporteDemasiadoGrandeError(ValueError):
    """El reporte supera el maximo de filas permitido (exportacion)."""


__all__ = [
    "FiltroReporteInvalidoError",
    "PeriodoInvalidoError",
    "ReporteDemasiadoGrandeError",
    "generar_reporte_actividad",
]


# ---------------------------------------------------------------------------
# Consulta unificada de actividad
# ---------------------------------------------------------------------------


def _consulta_texto():
    return select(
        literal("texto").label("tipo_servicio"),
        Traduccion.id_traduccion.label("id_registro"),
        Traduccion.fecha_creacion.label("fecha"),
        Traduccion.id_usuario.label("id_usuario"),
        Traduccion.id_idioma_origen.label("id_idioma_origen"),
        Traduccion.id_idioma_destino.label("id_idioma_destino"),
        ConfiguracionTraduccion.id_contexto.label("id_contexto"),
        cast(null(), String).label("estado"),
        cast(null(), String).label("detalle"),
    ).outerjoin(
        ConfiguracionTraduccion,
        ConfiguracionTraduccion.id_configuracion_traduccion == Traduccion.id_configuracion_traduccion,
    )


def _consulta_documentos():
    return select(
        literal("documento").label("tipo_servicio"),
        TraduccionDocumento.id_traduccion_documento.label("id_registro"),
        TraduccionDocumento.fecha.label("fecha"),
        TraduccionDocumento.id_usuario.label("id_usuario"),
        TraduccionDocumento.id_idioma_origen.label("id_idioma_origen"),
        TraduccionDocumento.id_idioma_destino.label("id_idioma_destino"),
        # La traduccion de documentos no aplica contexto
        cast(null(), Integer).label("id_contexto"),
        TraduccionDocumento.estado.label("estado"),
        TraduccionDocumento.nombre.label("detalle"),
    )


def _consulta_conversaciones():
    return select(
        literal("conversacion").label("tipo_servicio"),
        Conversacion.id_conversacion.label("id_registro"),
        Conversacion.fecha_inicio.label("fecha"),
        Conversacion.id_usuario.label("id_usuario"),
        Conversacion.id_idioma_origen.label("id_idioma_origen"),
        Conversacion.id_idioma_destino.label("id_idioma_destino"),
        Conversacion.id_contexto.label("id_contexto"),
        Conversacion.estado.label("estado"),
        Entorno.nombre.label("detalle"),
    ).outerjoin(Entorno, Entorno.id_entorno == Conversacion.id_entorno)


def _consulta_sesiones_externas():
    # Detalle: plataforma y referencia de la reunion (sin contenido de lo hablado)
    return select(
        literal("sesion_externa").label("tipo_servicio"),
        SesionExterna.id_sesion_externa.label("id_registro"),
        SesionExterna.fecha_creacion.label("fecha"),
        SesionExterna.id_usuario.label("id_usuario"),
        SesionExterna.id_idioma_origen.label("id_idioma_origen"),
        SesionExterna.id_idioma_destino.label("id_idioma_destino"),
        SesionExterna.id_contexto.label("id_contexto"),
        SesionExterna.estado.label("estado"),
        func.concat(
            func.replace(func.replace(SesionExterna.plataforma, "google_meet", "Google Meet"), "zoom", "Zoom"),
            " · ",
            SesionExterna.referencia_reunion,
        ).label("detalle"),
    )


CONSULTAS_POR_TIPO = {
    "texto": _consulta_texto,
    "documento": _consulta_documentos,
    "conversacion": _consulta_conversaciones,
    "sesion_externa": _consulta_sesiones_externas,
}


def _actividad_filtrada(filtros: FiltrosReporte):
    """Subconsulta con la actividad que cumple todos los filtros (se combinan con AND)."""
    tipos = [filtros.tipo_servicio] if filtros.tipo_servicio else list(CONSULTAS_POR_TIPO)
    consultas = [CONSULTAS_POR_TIPO[tipo]() for tipo in tipos if tipo in CONSULTAS_POR_TIPO]
    if not consultas:
        return None

    actividad = union_all(*consultas).subquery("actividad")
    fecha_local = cast(func.timezone(filtros.zona_horaria, actividad.c.fecha), Date)
    condiciones = [fecha_local.between(filtros.fecha_desde, filtros.fecha_hasta)]
    if filtros.id_idioma_origen is not None:
        condiciones.append(actividad.c.id_idioma_origen == filtros.id_idioma_origen)
    if filtros.id_idioma_destino is not None:
        condiciones.append(actividad.c.id_idioma_destino == filtros.id_idioma_destino)
    if filtros.id_contexto is not None:
        condiciones.append(actividad.c.id_contexto == filtros.id_contexto)

    return select(actividad).where(*condiciones).subquery("actividad_filtrada")


# ---------------------------------------------------------------------------
# Filtros
# ---------------------------------------------------------------------------


def _resolver_filtros(
    sesion: Session,
    fecha_desde: date | None,
    fecha_hasta: date | None,
    zona_horaria: str,
    tipo_servicio: TipoServicio | None,
    id_idioma_origen: int | None,
    id_idioma_destino: int | None,
    id_contexto: int | None,
) -> FiltrosReporte:
    periodo = resolver_periodo(sesion, fecha_desde, fecha_hasta, zona_horaria)

    def nombre_idioma(id_idioma: int | None, rol: str) -> str | None:
        if id_idioma is None:
            return None
        idioma = sesion.get(Idioma, id_idioma)
        if idioma is None:
            raise FiltroReporteInvalidoError(f"El idioma de {rol} indicado no existe.")
        return idioma.nombre

    nombre_contexto = None
    if id_contexto is not None:
        contexto = sesion.get(Contexto, id_contexto)
        if contexto is None:
            raise FiltroReporteInvalidoError("El contexto indicado no existe.")
        nombre_contexto = contexto.nombre

    return FiltrosReporte(
        fecha_desde=periodo.fecha_desde,
        fecha_hasta=periodo.fecha_hasta,
        zona_horaria=periodo.zona_horaria,
        tipo_servicio=tipo_servicio,
        id_idioma_origen=id_idioma_origen,
        nombre_idioma_origen=nombre_idioma(id_idioma_origen, "origen"),
        id_idioma_destino=id_idioma_destino,
        nombre_idioma_destino=nombre_idioma(id_idioma_destino, "destino"),
        id_contexto=id_contexto,
        nombre_contexto=nombre_contexto,
    )


# ---------------------------------------------------------------------------
# Totales y detalle
# ---------------------------------------------------------------------------


def _totales(sesion: Session, actividad) -> TotalesReporte:
    conteo: dict[str, int] = {}
    if actividad is not None:
        conteo = dict(
            sesion.execute(
                select(actividad.c.tipo_servicio, func.count()).group_by(actividad.c.tipo_servicio)
            ).all()
        )
    return TotalesReporte(
        total=sum(conteo.values()),
        texto=conteo.get("texto", 0),
        documento=conteo.get("documento", 0),
        conversacion=conteo.get("conversacion", 0),
        sesion_externa=conteo.get("sesion_externa", 0),
        sesion_externa_disponible=True,
    )


def _detalle(
    sesion: Session,
    actividad,
    zona_horaria: str,
    pagina: int | None,
    tamano_pagina: int,
) -> list[ActividadReporte]:
    if actividad is None:
        return []

    idioma_origen = aliased(Idioma)
    idioma_destino = aliased(Idioma)
    consulta = (
        select(
            actividad,
            func.timezone(zona_horaria, actividad.c.fecha).label("fecha_local"),
            Usuario.nombre.label("nombre_usuario"),
            Usuario.correo.label("correo_usuario"),
            idioma_origen.nombre.label("nombre_idioma_origen"),
            idioma_destino.nombre.label("nombre_idioma_destino"),
            Contexto.nombre.label("nombre_contexto"),
        )
        .join(Usuario, Usuario.id == actividad.c.id_usuario)
        .outerjoin(idioma_origen, idioma_origen.id_idioma == actividad.c.id_idioma_origen)
        .outerjoin(idioma_destino, idioma_destino.id_idioma == actividad.c.id_idioma_destino)
        .outerjoin(Contexto, Contexto.id_contexto == actividad.c.id_contexto)
        .order_by(actividad.c.fecha.desc(), actividad.c.tipo_servicio, actividad.c.id_registro.desc())
    )
    if pagina is not None:
        consulta = consulta.offset((pagina - 1) * tamano_pagina).limit(tamano_pagina)

    return [
        ActividadReporte(
            tipo_servicio=fila.tipo_servicio,
            id_registro=fila.id_registro,
            fecha=fila.fecha,
            fecha_local=fila.fecha_local,
            id_usuario=fila.id_usuario,
            nombre_usuario=fila.nombre_usuario,
            correo_usuario=fila.correo_usuario,
            idioma_origen=fila.nombre_idioma_origen,
            idioma_destino=fila.nombre_idioma_destino,
            contexto=fila.nombre_contexto,
            estado=fila.estado,
            detalle=fila.detalle,
        )
        for fila in sesion.execute(consulta).all()
    ]


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------


def generar_reporte_actividad(
    sesion: Session,
    *,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    zona_horaria: str = "UTC",
    tipo_servicio: TipoServicio | None = None,
    id_idioma_origen: int | None = None,
    id_idioma_destino: int | None = None,
    id_contexto: int | None = None,
    pagina: int | None = 1,
    tamano_pagina: int = TAMANO_PAGINA_POR_DEFECTO,
    maximo_filas: int | None = None,
) -> ReporteActividad:
    """
    Genera el reporte de actividad. Con `pagina=None` devuelve todas las filas (exportacion);
    `maximo_filas` limita ese caso y lanza ReporteDemasiadoGrandeError si se supera.
    Lanza PeriodoInvalidoError o FiltroReporteInvalidoError si los filtros no son validos.
    """
    filtros = _resolver_filtros(
        sesion,
        fecha_desde,
        fecha_hasta,
        zona_horaria,
        tipo_servicio,
        id_idioma_origen,
        id_idioma_destino,
        id_contexto,
    )
    actividad = _actividad_filtrada(filtros)
    totales = _totales(sesion, actividad)
    if maximo_filas is not None and totales.total > maximo_filas:
        raise ReporteDemasiadoGrandeError(
            f"El reporte tiene {totales.total} actividades y el maximo para exportar es "
            f"{maximo_filas}. Acota los filtros para exportarlo."
        )

    if pagina is None:
        tamano_efectivo = max(totales.total, 1)
        total_paginas = 1 if totales.total else 0
    else:
        tamano_efectivo = tamano_pagina
        total_paginas = math.ceil(totales.total / tamano_pagina) if totales.total else 0

    return ReporteActividad(
        filtros=filtros,
        totales=totales,
        actividades=_detalle(sesion, actividad, filtros.zona_horaria, pagina, tamano_pagina),
        pagina=pagina or 1,
        tamano_pagina=tamano_efectivo,
        total_paginas=total_paginas,
        fecha_generacion=datetime.now(UTC),
        fecha_generacion_local=sesion.scalar(
            select(func.timezone(filtros.zona_horaria, func.now()))
        ),
    )

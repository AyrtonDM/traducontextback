"""
Dashboard administrativo (HU-46): indicadores calculados con los datos reales de la plataforma.

El periodo se expresa en fechas locales (`zona_horaria` del navegador del administrador) y es
inclusivo en ambos extremos. Las fechas de la base (timestamptz) se convierten a esa zona antes
de filtrar y agrupar, para que "hoy" y cada dia del grafico coincidan con lo que ve el usuario.
"""

from collections import Counter
from datetime import date, timedelta

from sqlalchemy import Date, cast, func, select, text, union
from sqlalchemy.orm import Session

from app.models.conversacion.conversacion import Conversacion
from app.models.documento.traduccion_documento import TraduccionDocumento
from app.models.integracion.sesion_externa import SesionExterna
from app.models.traduccion.configuracion_traduccion import ConfiguracionTraduccion
from app.models.traduccion.contexto import Contexto
from app.models.traduccion.idioma import Idioma
from app.models.traduccion.traduccion import Traduccion
from app.models.usuario.sesion import Sesion
from app.models.usuario.usuario import Usuario
from app.schemas.dashboard import (
    ContextoUso,
    DashboardResultado,
    IdiomaUso,
    IndicadoresActividad,
    IndicadoresUsuarios,
    PeriodoDashboard,
    PuntoEvolucion,
)


DIAS_PERIODO_POR_DEFECTO = 30
MAXIMO_DIAS_PERIODO = 731
MAXIMO_DIAS_AGRUPACION_DIARIA = 92
LIMITE_RANKING = 5
ESTADO_DOCUMENTO_COMPLETADO = "COMPLETADO"


class PeriodoInvalidoError(ValueError):
    pass


# ---------------------------------------------------------------------------
# Periodo
# ---------------------------------------------------------------------------


def resolver_periodo(
    sesion: Session,
    fecha_desde: date | None,
    fecha_hasta: date | None,
    zona_horaria: str,
) -> PeriodoDashboard:
    # PostgreSQL hace la conversion de fechas, asi que tambien valida la zona horaria
    # (en Windows Python no incluye la base de zonas horarias sin el paquete tzdata).
    zona_valida = sesion.scalar(
        select(func.count()).select_from(text("pg_timezone_names")).where(
            text("name = :zona")
        ),
        {"zona": zona_horaria},
    )
    if not zona_valida:
        raise PeriodoInvalidoError(f"Zona horaria '{zona_horaria}' no valida.")

    hasta = fecha_hasta or sesion.scalar(
        select(cast(func.timezone(zona_horaria, func.now()), Date))
    )
    desde = fecha_desde or (hasta - timedelta(days=DIAS_PERIODO_POR_DEFECTO - 1))

    if desde > hasta:
        raise PeriodoInvalidoError("La fecha inicial no puede ser posterior a la fecha final.")
    if (hasta - desde).days + 1 > MAXIMO_DIAS_PERIODO:
        raise PeriodoInvalidoError("El periodo no puede superar los 2 años.")

    dias = (hasta - desde).days + 1
    return PeriodoDashboard(
        fecha_desde=desde,
        fecha_hasta=hasta,
        zona_horaria=zona_horaria,
        agrupacion="dia" if dias <= MAXIMO_DIAS_AGRUPACION_DIARIA else "mes",
    )


def _fecha_local(columna, zona_horaria: str):
    """Fecha (sin hora) de una columna timestamptz en la zona horaria indicada."""
    return cast(func.timezone(zona_horaria, columna), Date)


def _en_periodo(columna, periodo: PeriodoDashboard):
    fecha = _fecha_local(columna, periodo.zona_horaria)
    return fecha.between(periodo.fecha_desde, periodo.fecha_hasta)


# ---------------------------------------------------------------------------
# Indicadores
# ---------------------------------------------------------------------------


def _contar(sesion: Session, modelo, columna_fecha, periodo: PeriodoDashboard, *filtros) -> int:
    return sesion.scalar(
        select(func.count()).select_from(modelo).where(_en_periodo(columna_fecha, periodo), *filtros)
    ) or 0


def _indicadores_usuarios(sesion: Session, periodo: PeriodoDashboard) -> IndicadoresUsuarios:
    fin_periodo = _fecha_local(Usuario.fecha_creacion, periodo.zona_horaria) <= periodo.fecha_hasta
    total = sesion.scalar(select(func.count()).select_from(Usuario).where(fin_periodo)) or 0
    nuevos = _contar(sesion, Usuario, Usuario.fecha_creacion, periodo)

    # Activo: inicio sesion o uso algun servicio de traduccion durante el periodo
    activos_union = union(
        select(Sesion.id_usuario).where(_en_periodo(Sesion.fecha_inicio, periodo)),
        select(Traduccion.id_usuario).where(_en_periodo(Traduccion.fecha_creacion, periodo)),
        select(TraduccionDocumento.id_usuario).where(_en_periodo(TraduccionDocumento.fecha, periodo)),
        select(Conversacion.id_usuario).where(_en_periodo(Conversacion.fecha_inicio, periodo)),
        select(SesionExterna.id_usuario).where(_en_periodo(SesionExterna.fecha_creacion, periodo)),
    ).subquery()
    activos = sesion.scalar(select(func.count()).select_from(activos_union)) or 0

    return IndicadoresUsuarios(total=total, activos_periodo=activos, nuevos_periodo=nuevos)


def _indicadores_actividad(sesion: Session, periodo: PeriodoDashboard) -> IndicadoresActividad:
    return IndicadoresActividad(
        traducciones_texto=_contar(sesion, Traduccion, Traduccion.fecha_creacion, periodo),
        documentos_traducidos=_contar(
            sesion,
            TraduccionDocumento,
            TraduccionDocumento.fecha,
            periodo,
            TraduccionDocumento.estado == ESTADO_DOCUMENTO_COMPLETADO,
        ),
        conversaciones=_contar(sesion, Conversacion, Conversacion.fecha_inicio, periodo),
        sesiones_externas=_contar(sesion, SesionExterna, SesionExterna.fecha_creacion, periodo),
        sesiones_externas_disponible=True,
    )


def _idiomas_mas_utilizados(sesion: Session, periodo: PeriodoDashboard) -> list[IdiomaUso]:
    """Cada traduccion, documento o conversacion cuenta una vez por su idioma de origen y otra por el de destino."""
    fuentes = (
        (Traduccion, Traduccion.fecha_creacion),
        (TraduccionDocumento, TraduccionDocumento.fecha),
        (Conversacion, Conversacion.fecha_inicio),
        (SesionExterna, SesionExterna.fecha_creacion),
    )
    conteo: Counter[int] = Counter()
    for modelo, columna_fecha in fuentes:
        for columna_idioma in (modelo.id_idioma_origen, modelo.id_idioma_destino):
            filas = sesion.execute(
                select(columna_idioma, func.count())
                .where(_en_periodo(columna_fecha, periodo), columna_idioma.is_not(None))
                .group_by(columna_idioma)
            ).all()
            for id_idioma, total in filas:
                conteo[id_idioma] += total

    if not conteo:
        return []
    idiomas = {
        idioma.id_idioma: idioma
        for idioma in sesion.scalars(select(Idioma).where(Idioma.id_idioma.in_(conteo.keys())))
    }
    return [
        IdiomaUso(
            id_idioma=id_idioma,
            nombre=idiomas[id_idioma].nombre,
            codigo=idiomas[id_idioma].codigo,
            total=total,
        )
        for id_idioma, total in conteo.most_common(LIMITE_RANKING)
        if id_idioma in idiomas
    ]


def _contextos_mas_utilizados(sesion: Session, periodo: PeriodoDashboard) -> list[ContextoUso]:
    """
    Traducciones de texto (contexto de su configuracion) y conversaciones (contexto propio).
    La traduccion de documentos no aplica contexto, por eso no se cuenta aqui.
    """
    conteo: Counter[int] = Counter()
    filas_texto = sesion.execute(
        select(ConfiguracionTraduccion.id_contexto, func.count())
        .join(Traduccion, Traduccion.id_configuracion_traduccion == ConfiguracionTraduccion.id_configuracion_traduccion)
        .where(_en_periodo(Traduccion.fecha_creacion, periodo))
        .group_by(ConfiguracionTraduccion.id_contexto)
    ).all()
    filas_conversacion = sesion.execute(
        select(Conversacion.id_contexto, func.count())
        .where(_en_periodo(Conversacion.fecha_inicio, periodo), Conversacion.id_contexto.is_not(None))
        .group_by(Conversacion.id_contexto)
    ).all()
    filas_externas = sesion.execute(
        select(SesionExterna.id_contexto, func.count())
        .where(_en_periodo(SesionExterna.fecha_creacion, periodo), SesionExterna.id_contexto.is_not(None))
        .group_by(SesionExterna.id_contexto)
    ).all()
    for id_contexto, total in [*filas_texto, *filas_conversacion, *filas_externas]:
        conteo[id_contexto] += total

    if not conteo:
        return []
    contextos = {
        contexto.id_contexto: contexto
        for contexto in sesion.scalars(select(Contexto).where(Contexto.id_contexto.in_(conteo.keys())))
    }
    return [
        ContextoUso(id_contexto=id_contexto, nombre=contextos[id_contexto].nombre, total=total)
        for id_contexto, total in conteo.most_common(LIMITE_RANKING)
        if id_contexto in contextos
    ]


def _evolucion(sesion: Session, periodo: PeriodoDashboard) -> list[PuntoEvolucion]:
    unidad = "day" if periodo.agrupacion == "dia" else "month"

    def serie(columna_fecha, *filtros) -> dict[date, int]:
        bucket = cast(
            func.date_trunc(unidad, func.timezone(periodo.zona_horaria, columna_fecha)), Date
        ).label("bucket")
        filas = sesion.execute(
            select(bucket, func.count())
            .where(_en_periodo(columna_fecha, periodo), *filtros)
            .group_by(bucket)
        ).all()
        return {fecha: total for fecha, total in filas}

    texto = serie(Traduccion.fecha_creacion)
    documentos = serie(
        TraduccionDocumento.fecha, TraduccionDocumento.estado == ESTADO_DOCUMENTO_COMPLETADO
    )
    conversaciones = serie(Conversacion.fecha_inicio)

    return [
        PuntoEvolucion(
            fecha=fecha,
            traducciones_texto=texto.get(fecha, 0),
            documentos=documentos.get(fecha, 0),
            conversaciones=conversaciones.get(fecha, 0),
        )
        for fecha in _fechas_del_periodo(periodo)
    ]


def _fechas_del_periodo(periodo: PeriodoDashboard) -> list[date]:
    """Todos los dias (o meses) del periodo, para que el grafico muestre tambien los ceros."""
    if periodo.agrupacion == "dia":
        dias = (periodo.fecha_hasta - periodo.fecha_desde).days + 1
        return [periodo.fecha_desde + timedelta(days=i) for i in range(dias)]

    fechas = []
    actual = periodo.fecha_desde.replace(day=1)
    while actual <= periodo.fecha_hasta:
        fechas.append(actual)
        actual = (actual.replace(day=28) + timedelta(days=4)).replace(day=1)
    return fechas


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------


def obtener_dashboard(
    sesion: Session,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    zona_horaria: str = "UTC",
) -> DashboardResultado:
    periodo = resolver_periodo(sesion, fecha_desde, fecha_hasta, zona_horaria)
    return DashboardResultado(
        periodo=periodo,
        usuarios=_indicadores_usuarios(sesion, periodo),
        actividad=_indicadores_actividad(sesion, periodo),
        idiomas_mas_utilizados=_idiomas_mas_utilizados(sesion, periodo),
        contextos_mas_utilizados=_contextos_mas_utilizados(sesion, periodo),
        evolucion=_evolucion(sesion, periodo),
    )

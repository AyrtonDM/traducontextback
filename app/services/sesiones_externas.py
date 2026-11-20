"""
HU-36 Configuracion de sesion externa, HU-40 participantes y HU-41 control del servicio.
Ninguna accion actua sobre la reunion de Meet o Zoom: solo sobre el servicio de traduccion.
"""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.cifrado import IntegracionNoConfiguradaError
from app.models.glosario.glosario import Glosario
from app.models.integracion.intervencion_externa import IntervencionExterna
from app.models.integracion.participante_externo import ParticipanteExterno
from app.models.integracion.sesion_externa import (
    ESTADO_ACTIVA,
    ESTADO_CONFIGURADA,
    ESTADO_FINALIZADA,
    ESTADO_PAUSADA,
    SesionExterna,
)
from app.schemas.sesion_externa import (
    ActualizarSesionExternaSolicitud,
    CrearSesionExternaSolicitud,
    ParticipanteExternoDetalle,
    SesionExternaDetalle,
    SincronizacionParticipantesResultado,
)
from app.services import plataformas
from app.services.conversaciones import (
    _obtener_idioma_por_id,
    _par_idiomas_glosario,
    _validar_contexto,
    _validar_glosario,
    _validar_tono,
)
from app.services.entornos import obtener_entorno_activo
from app.services.integraciones import (
    ConexionNoVinculadaError,
    exigir_conexion_vinculada,
    token_vigente,
)
from app.services.plataformas import ErrorPlataformaExterna

PARTICIPANTES_GENERICOS_INICIALES = 2
MAX_PARTICIPANTES = 50


class SesionExternaNoEncontradaError(ValueError):
    """La sesion externa no existe o no pertenece al usuario autenticado."""


class ParticipanteExternoNoEncontradoError(SesionExternaNoEncontradaError):
    """El participante no existe en una sesion externa del usuario."""


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _consulta_sesiones():
    return select(SesionExterna).options(
        selectinload(SesionExterna.idioma_origen),
        selectinload(SesionExterna.idioma_destino),
        selectinload(SesionExterna.contexto),
        selectinload(SesionExterna.entorno),
        selectinload(SesionExterna.tono),
        selectinload(SesionExterna.glosario).selectinload(Glosario.idioma_origen),
        selectinload(SesionExterna.glosario).selectinload(Glosario.idioma_destino),
        selectinload(SesionExterna.participantes),
    )


def armar_detalle_participante(participante: ParticipanteExterno) -> ParticipanteExternoDetalle:
    return ParticipanteExternoDetalle(
        id_participante=participante.id_participante,
        id_sesion_externa=participante.id_sesion_externa,
        nombre=participante.nombre,
        orden=participante.orden,
        generico=participante.generico,
        desde_plataforma=participante.desde_plataforma,
    )


def armar_detalle_sesion(sesion_externa: SesionExterna, total_intervenciones: int = 0) -> SesionExternaDetalle:
    s = sesion_externa
    definicion = plataformas.obtener_plataforma(s.plataforma)
    return SesionExternaDetalle(
        id_sesion_externa=s.id_sesion_externa,
        plataforma=s.plataforma,
        nombre_plataforma=definicion.nombre,
        enlace_reunion=s.enlace_reunion,
        referencia_reunion=s.referencia_reunion,
        url_reunion=plataformas.enlace_publico(s.plataforma, s.referencia_reunion),
        estado=s.estado,
        id_idioma_origen=s.id_idioma_origen,
        id_idioma_destino=s.id_idioma_destino,
        codigo_idioma_origen=s.idioma_origen.codigo if s.idioma_origen else None,
        codigo_idioma_destino=s.idioma_destino.codigo if s.idioma_destino else None,
        nombre_idioma_origen=s.idioma_origen.nombre if s.idioma_origen else None,
        nombre_idioma_destino=s.idioma_destino.nombre if s.idioma_destino else None,
        id_entorno=s.id_entorno,
        nombre_entorno=s.entorno.nombre if s.entorno else None,
        id_contexto=s.id_contexto,
        nombre_contexto=s.contexto.nombre if s.contexto else None,
        id_tono=s.id_tono,
        nombre_tono=s.tono.nombre if s.tono else None,
        id_glosario=s.id_glosario,
        nombre_glosario=s.glosario.nombre if s.glosario else None,
        par_idiomas_glosario=_par_idiomas_glosario(s.glosario),
        descripcion_contexto=s.descripcion_contexto,
        participantes=[armar_detalle_participante(p) for p in s.participantes],
        total_intervenciones=total_intervenciones,
        fecha_creacion=s.fecha_creacion,
        fecha_inicio=s.fecha_inicio,
        fecha_actualizacion=s.fecha_actualizacion,
        fecha_fin=s.fecha_fin,
    )


def contar_intervenciones(sesion: Session, ids: list[int]) -> dict[int, int]:
    if not ids:
        return {}
    filas = sesion.execute(
        select(IntervencionExterna.id_sesion_externa, func.count())
        .where(IntervencionExterna.id_sesion_externa.in_(ids))
        .group_by(IntervencionExterna.id_sesion_externa)
    ).all()
    return {id_sesion: total for id_sesion, total in filas}


def detalle_con_total(sesion: Session, sesion_externa: SesionExterna) -> SesionExternaDetalle:
    totales = contar_intervenciones(sesion, [sesion_externa.id_sesion_externa])
    return armar_detalle_sesion(sesion_externa, totales.get(sesion_externa.id_sesion_externa, 0))


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------


def obtener_sesion_externa(sesion: Session, id_usuario: int, id_sesion_externa: int) -> SesionExterna:
    encontrada = sesion.scalar(
        _consulta_sesiones().where(
            SesionExterna.id_sesion_externa == id_sesion_externa,
            SesionExterna.id_usuario == id_usuario,
        )
    )
    if not encontrada:
        raise SesionExternaNoEncontradaError(
            "Sesión externa no encontrada o no pertenece al usuario autenticado."
        )
    return encontrada


def listar_sesiones_externas(sesion: Session, id_usuario: int, estado: str | None = None) -> list[SesionExterna]:
    """Historial de sesiones externas del usuario, de la mas reciente a la mas antigua."""
    consulta = _consulta_sesiones().where(SesionExterna.id_usuario == id_usuario)
    if estado:
        consulta = consulta.where(SesionExterna.estado == estado)
    consulta = consulta.order_by(SesionExterna.fecha_creacion.desc(), SesionExterna.id_sesion_externa.desc())
    return list(sesion.scalars(consulta).all())


# ---------------------------------------------------------------------------
# Configuracion (HU-36)
# ---------------------------------------------------------------------------


def crear_sesion_externa(sesion: Session, id_usuario: int, datos: CrearSesionExternaSolicitud) -> SesionExterna:
    exigir_conexion_vinculada(sesion, id_usuario, datos.plataforma)
    referencia = plataformas.normalizar_reunion(datos.plataforma, datos.enlace_reunion)
    _obtener_idioma_por_id(sesion, datos.id_idioma_origen)
    _obtener_idioma_por_id(sesion, datos.id_idioma_destino)
    obtener_entorno_activo(sesion, datos.id_entorno)
    if datos.id_contexto is not None:
        _validar_contexto(sesion, id_usuario, datos.id_contexto)
    if datos.id_tono is not None:
        _validar_tono(sesion, datos.id_tono)
    if datos.id_glosario is not None:
        _validar_glosario(sesion, id_usuario, datos.id_glosario, datos.id_idioma_origen, datos.id_idioma_destino)

    nueva = SesionExterna(
        id_usuario=id_usuario,
        plataforma=datos.plataforma,
        enlace_reunion=datos.enlace_reunion.strip(),
        referencia_reunion=referencia,
        estado=ESTADO_CONFIGURADA,
        id_idioma_origen=datos.id_idioma_origen,
        id_idioma_destino=datos.id_idioma_destino,
        id_entorno=datos.id_entorno,
        id_contexto=datos.id_contexto,
        id_tono=datos.id_tono,
        id_glosario=datos.id_glosario,
        descripcion_contexto=datos.descripcion_contexto,
    )
    # HU-40: etiquetas genericas para cuando la plataforma no informe los nombres
    nueva.participantes = [
        ParticipanteExterno(nombre=f"Participante {n}", orden=n, generico=True)
        for n in range(1, PARTICIPANTES_GENERICOS_INICIALES + 1)
    ]
    sesion.add(nueva)
    sesion.commit()
    return obtener_sesion_externa(sesion, id_usuario, nueva.id_sesion_externa)


def actualizar_sesion_externa(
    sesion: Session,
    id_usuario: int,
    id_sesion_externa: int,
    datos: ActualizarSesionExternaSolicitud,
) -> SesionExterna:
    """Antes o durante la reunion; los cambios valen para las intervenciones siguientes."""
    actual = obtener_sesion_externa(sesion, id_usuario, id_sesion_externa)
    if actual.estado == ESTADO_FINALIZADA:
        raise ValueError("La sesión está finalizada; no se puede modificar.")
    campos = datos.model_fields_set

    if campos & {"enlace_reunion", "id_idioma_origen", "id_idioma_destino"}:
        if actual.estado != ESTADO_CONFIGURADA:
            raise ValueError("El enlace y los idiomas solo se pueden cambiar antes de iniciar el servicio.")
        if "enlace_reunion" in campos:
            actual.referencia_reunion = plataformas.normalizar_reunion(actual.plataforma, datos.enlace_reunion)
            actual.enlace_reunion = datos.enlace_reunion.strip()
        origen = datos.id_idioma_origen if "id_idioma_origen" in campos else actual.id_idioma_origen
        destino = datos.id_idioma_destino if "id_idioma_destino" in campos else actual.id_idioma_destino
        if origen == destino:
            raise ValueError("Los idiomas de los participantes deben ser distintos.")
        _obtener_idioma_por_id(sesion, origen)
        _obtener_idioma_por_id(sesion, destino)
        actual.id_idioma_origen, actual.id_idioma_destino = origen, destino
        # Un glosario de otro par deja de ser valido
        if actual.glosario and {actual.glosario.id_idioma_origen, actual.glosario.id_idioma_destino} != {origen, destino}:
            actual.id_glosario = None

    if "id_entorno" in campos:
        obtener_entorno_activo(sesion, datos.id_entorno)
        actual.id_entorno = datos.id_entorno
    if "id_contexto" in campos:
        if datos.id_contexto is not None:
            _validar_contexto(sesion, id_usuario, datos.id_contexto)
        actual.id_contexto = datos.id_contexto
    if "id_tono" in campos:
        if datos.id_tono is not None:
            _validar_tono(sesion, datos.id_tono)
        actual.id_tono = datos.id_tono
    if "id_glosario" in campos:
        if datos.id_glosario is not None:
            _validar_glosario(sesion, id_usuario, datos.id_glosario, actual.id_idioma_origen, actual.id_idioma_destino)
        actual.id_glosario = datos.id_glosario
    if "descripcion_contexto" in campos:
        actual.descripcion_contexto = datos.descripcion_contexto

    actual.fecha_actualizacion = _ahora()
    sesion.commit()
    sesion.expire_all()
    return obtener_sesion_externa(sesion, id_usuario, id_sesion_externa)


# ---------------------------------------------------------------------------
# Control del servicio (HU-41)
# ---------------------------------------------------------------------------


def _cambiar_estado(
    sesion: Session,
    id_usuario: int,
    id_sesion_externa: int,
    permitidos: tuple[str, ...],
    nuevo: str,
    mensaje_error: str,
) -> SesionExterna:
    actual = obtener_sesion_externa(sesion, id_usuario, id_sesion_externa)
    if actual.estado not in permitidos:
        raise ValueError(f"{mensaje_error} Estado actual: {actual.estado}.")
    ahora = _ahora()
    actual.estado = nuevo
    actual.fecha_actualizacion = ahora
    if nuevo == ESTADO_ACTIVA and actual.fecha_inicio is None:
        actual.fecha_inicio = ahora
    if nuevo == ESTADO_FINALIZADA:
        actual.fecha_fin = ahora
    sesion.commit()
    sesion.expire_all()
    return obtener_sesion_externa(sesion, id_usuario, id_sesion_externa)


def iniciar_servicio(sesion: Session, id_usuario: int, id_sesion_externa: int) -> SesionExterna:
    actual = obtener_sesion_externa(sesion, id_usuario, id_sesion_externa)
    exigir_conexion_vinculada(sesion, id_usuario, actual.plataforma)
    return _cambiar_estado(
        sesion, id_usuario, id_sesion_externa, (ESTADO_CONFIGURADA,), ESTADO_ACTIVA,
        "Solo se puede iniciar una sesión configurada.",
    )


def pausar_servicio(sesion: Session, id_usuario: int, id_sesion_externa: int) -> SesionExterna:
    return _cambiar_estado(
        sesion, id_usuario, id_sesion_externa, (ESTADO_ACTIVA,), ESTADO_PAUSADA,
        "Solo se puede pausar un servicio activo.",
    )


def reanudar_servicio(sesion: Session, id_usuario: int, id_sesion_externa: int) -> SesionExterna:
    """Conserva la configuracion y el contexto acumulado (las intervenciones previas)."""
    return _cambiar_estado(
        sesion, id_usuario, id_sesion_externa, (ESTADO_PAUSADA,), ESTADO_ACTIVA,
        "Solo se puede reanudar un servicio pausado.",
    )


def finalizar_servicio(sesion: Session, id_usuario: int, id_sesion_externa: int) -> SesionExterna:
    """La sesion queda registrada en el historial (lista de sesiones externas finalizadas)."""
    return _cambiar_estado(
        sesion, id_usuario, id_sesion_externa, (ESTADO_CONFIGURADA, ESTADO_ACTIVA, ESTADO_PAUSADA),
        ESTADO_FINALIZADA, "La sesión ya está finalizada.",
    )


# ---------------------------------------------------------------------------
# Participantes (HU-40)
# ---------------------------------------------------------------------------


def _exigir_no_finalizada(actual: SesionExterna) -> None:
    if actual.estado == ESTADO_FINALIZADA:
        raise ValueError("La sesión está finalizada; no se puede modificar.")


def _siguiente_orden(sesion: Session, id_sesion_externa: int) -> int:
    ultimo = sesion.scalar(
        select(func.max(ParticipanteExterno.orden)).where(ParticipanteExterno.id_sesion_externa == id_sesion_externa)
    )
    return (ultimo or 0) + 1


def agregar_participante_generico(
    sesion: Session, id_usuario: int, id_sesion_externa: int, nombre: str | None
) -> ParticipanteExterno:
    actual = obtener_sesion_externa(sesion, id_usuario, id_sesion_externa)
    _exigir_no_finalizada(actual)
    if len(actual.participantes) >= MAX_PARTICIPANTES:
        raise ValueError(f"Se admiten como máximo {MAX_PARTICIPANTES} participantes por sesión.")
    orden = _siguiente_orden(sesion, id_sesion_externa)
    participante = ParticipanteExterno(
        id_sesion_externa=id_sesion_externa,
        nombre=nombre or f"Participante {orden}",
        orden=orden,
        generico=True,
    )
    sesion.add(participante)
    sesion.commit()
    return participante


def renombrar_participante(
    sesion: Session, id_usuario: int, id_sesion_externa: int, id_participante: int, nombre: str
) -> ParticipanteExterno:
    """Solo las etiquetas genericas: los nombres informados por la plataforma no se cambian."""
    actual = obtener_sesion_externa(sesion, id_usuario, id_sesion_externa)
    _exigir_no_finalizada(actual)
    participante = next((p for p in actual.participantes if p.id_participante == id_participante), None)
    if not participante:
        raise ParticipanteExternoNoEncontradoError("Participante no encontrado en la sesión indicada.")
    if participante.desde_plataforma:
        raise ValueError("El nombre lo informó la plataforma; solo se pueden renombrar las etiquetas genéricas.")
    participante.nombre = nombre
    actual.fecha_actualizacion = _ahora()
    sesion.commit()
    return participante


def sincronizar_participantes(
    sesion: Session, id_usuario: int, id_sesion_externa: int
) -> SincronizacionParticipantesResultado:
    """
    Agrega los participantes que informe la plataforma (sin duplicar). Si la plataforma no los
    proporciona, no falla: se informa y se siguen usando las etiquetas genericas.
    """
    actual = obtener_sesion_externa(sesion, id_usuario, id_sesion_externa)
    _exigir_no_finalizada(actual)
    definicion = plataformas.obtener_plataforma(actual.plataforma)
    conexion = exigir_conexion_vinculada(sesion, id_usuario, actual.plataforma)

    aviso = None
    encontrados = []
    try:
        encontrados = plataformas.consultar_participantes(
            actual.plataforma, token_vigente(sesion, conexion), actual.referencia_reunion
        )
    except (ErrorPlataformaExterna, ConexionNoVinculadaError, IntegracionNoConfiguradaError) as error:
        aviso = f"{definicion.nombre} no proporcionó los participantes ({error}). Se usan etiquetas genéricas."
    if not encontrados and aviso is None:
        aviso = f"{definicion.nombre} no informó participantes para esta reunión. Se usan etiquetas genéricas."

    existentes = {p.id_externo for p in actual.participantes if p.id_externo}
    agregados = 0
    orden = _siguiente_orden(sesion, id_sesion_externa)
    for encontrado in encontrados:
        if encontrado.id_externo in existentes or len(actual.participantes) + agregados >= MAX_PARTICIPANTES:
            continue
        sesion.add(
            ParticipanteExterno(
                id_sesion_externa=id_sesion_externa,
                nombre=encontrado.nombre[:100],
                orden=orden,
                generico=False,
                desde_plataforma=True,
                id_externo=encontrado.id_externo[:255],
            )
        )
        orden += 1
        agregados += 1
    sesion.commit()
    sesion.expire_all()
    actualizada = obtener_sesion_externa(sesion, id_usuario, id_sesion_externa)
    return SincronizacionParticipantesResultado(
        disponible=bool(encontrados),
        agregados=agregados,
        aviso=aviso,
        participantes=[armar_detalle_participante(p) for p in actualizada.participantes],
    )

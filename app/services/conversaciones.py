from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.conversacion.conversacion import (
    ESTADO_ACTIVA,
    ESTADO_FINALIZADA,
    ESTADO_PAUSADA,
    Conversacion,
)
from app.models.conversacion.participante import (
    ORDEN_PARTICIPANTE_DESTINO,
    ORDEN_PARTICIPANTE_ORIGEN,
    ParticipanteConversacion,
)
from app.models.traduccion.contexto import Contexto
from app.models.traduccion.idioma import Idioma
from app.models.traduccion.tono import Tono
from app.schemas.conversacion import (
    ActualizarConversacionSolicitud,
    ConversacionDetalle,
    IniciarConversacionSolicitud,
    ParticipanteDetalle,
)
from app.services.entornos import obtener_entorno_activo


class ConversacionNoEncontradaError(ValueError):
    """La conversacion no existe o no pertenece al usuario autenticado."""


class ParticipanteNoEncontradoError(ConversacionNoEncontradaError):
    """El participante no existe en una conversacion del usuario autenticado."""


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _obtener_idioma_por_id(sesion: Session, id_idioma: int) -> Idioma:
    idioma = sesion.scalar(select(Idioma).where(Idioma.id_idioma == id_idioma))
    if not idioma:
        raise ValueError(f"Idioma con id {id_idioma} no encontrado.")
    return idioma


def _validar_contexto(sesion: Session, id_usuario: int, id_contexto: int) -> Contexto:
    """El contexto debe estar activo y ser global o un contexto personal del usuario."""
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


def _validar_tono(sesion: Session, id_tono: int) -> Tono:
    """El tono debe existir y estar activo en el catalogo de HU-15."""
    tono = sesion.scalar(
        select(Tono).where(Tono.id_tono == id_tono, Tono.activo.is_(True))
    )
    if not tono:
        raise ValueError(f"Tono con id {id_tono} no encontrado o inactivo.")
    return tono


def _consulta_conversaciones():
    return select(Conversacion).options(
        selectinload(Conversacion.idioma_origen),
        selectinload(Conversacion.idioma_destino),
        selectinload(Conversacion.contexto),
        selectinload(Conversacion.entorno),
        selectinload(Conversacion.tono),
        selectinload(Conversacion.participantes).selectinload(ParticipanteConversacion.idioma),
    )


def armar_detalle_participante(participante: ParticipanteConversacion) -> ParticipanteDetalle:
    return ParticipanteDetalle(
        id_participante=participante.id_participante,
        id_conversacion=participante.id_conversacion,
        nombre=participante.nombre,
        orden=participante.orden,
        id_idioma=participante.id_idioma,
        codigo_idioma=participante.idioma.codigo if participante.idioma else None,
        nombre_idioma=participante.idioma.nombre if participante.idioma else None,
    )


def armar_detalle_conversacion(conversacion: Conversacion) -> ConversacionDetalle:
    return ConversacionDetalle(
        id_conversacion=conversacion.id_conversacion,
        estado=conversacion.estado,
        id_usuario=conversacion.id_usuario,
        id_idioma_origen=conversacion.id_idioma_origen,
        id_idioma_destino=conversacion.id_idioma_destino,
        codigo_idioma_origen=conversacion.idioma_origen.codigo if conversacion.idioma_origen else None,
        codigo_idioma_destino=conversacion.idioma_destino.codigo if conversacion.idioma_destino else None,
        nombre_idioma_origen=conversacion.idioma_origen.nombre if conversacion.idioma_origen else None,
        nombre_idioma_destino=conversacion.idioma_destino.nombre if conversacion.idioma_destino else None,
        id_contexto=conversacion.id_contexto,
        nombre_contexto=conversacion.contexto.nombre if conversacion.contexto else None,
        id_entorno=conversacion.id_entorno,
        nombre_entorno=conversacion.entorno.nombre if conversacion.entorno else None,
        id_tono=conversacion.id_tono,
        nombre_tono=conversacion.tono.nombre if conversacion.tono else None,
        descripcion_contexto=conversacion.descripcion_contexto,
        mantener_contexto=conversacion.mantener_contexto,
        asistencia_conversacional=conversacion.asistencia_conversacional,
        participantes=[armar_detalle_participante(p) for p in conversacion.participantes],
        fecha_inicio=conversacion.fecha_inicio,
        fecha_actualizacion=conversacion.fecha_actualizacion,
        fecha_fin=conversacion.fecha_fin,
    )


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------


def obtener_conversacion_usuario(
    sesion: Session,
    id_usuario: int,
    id_conversacion: int,
) -> Conversacion:
    """Obtiene una conversacion del usuario o lanza ConversacionNoEncontradaError."""
    conversacion = sesion.scalar(
        _consulta_conversaciones().where(
            Conversacion.id_conversacion == id_conversacion,
            Conversacion.id_usuario == id_usuario,
        )
    )
    if not conversacion:
        raise ConversacionNoEncontradaError(
            "Conversacion no encontrada o no pertenece al usuario autenticado."
        )
    return conversacion


def listar_conversaciones_usuario(
    sesion: Session,
    id_usuario: int,
    estado: str | None = None,
) -> list[Conversacion]:
    """Lista las conversaciones del usuario, de la mas reciente a la mas antigua."""
    consulta = _consulta_conversaciones().where(Conversacion.id_usuario == id_usuario)
    if estado:
        consulta = consulta.where(Conversacion.estado == estado)
    consulta = consulta.order_by(
        Conversacion.fecha_inicio.desc(),
        Conversacion.id_conversacion.desc(),
    )
    return list(sesion.scalars(consulta).all())


def exigir_conversacion_activa(
    sesion: Session,
    id_usuario: int,
    id_conversacion: int,
) -> Conversacion:
    """
    Garantiza que la conversacion es del usuario y esta activa.
    Pensada para los futuros endpoints de intervenciones (en pausa o finalizada no se procesan).
    """
    conversacion = obtener_conversacion_usuario(sesion, id_usuario, id_conversacion)
    if conversacion.estado != ESTADO_ACTIVA:
        raise ValueError(
            f"La conversacion esta {conversacion.estado}; no admite nuevas intervenciones."
        )
    return conversacion


# ---------------------------------------------------------------------------
# Ciclo de vida
# ---------------------------------------------------------------------------


def iniciar_conversacion(
    sesion: Session,
    id_usuario: int,
    datos: IniciarConversacionSolicitud,
) -> Conversacion:
    _obtener_idioma_por_id(sesion, datos.id_idioma_origen)
    _obtener_idioma_por_id(sesion, datos.id_idioma_destino)
    if datos.id_contexto is not None:
        _validar_contexto(sesion, id_usuario, datos.id_contexto)
    obtener_entorno_activo(sesion, datos.id_entorno)
    if datos.id_tono is not None:
        _validar_tono(sesion, datos.id_tono)

    conversacion = Conversacion(
        estado=ESTADO_ACTIVA,
        id_usuario=id_usuario,
        id_idioma_origen=datos.id_idioma_origen,
        id_idioma_destino=datos.id_idioma_destino,
        id_contexto=datos.id_contexto,
        id_entorno=datos.id_entorno,
        id_tono=datos.id_tono,
        descripcion_contexto=datos.descripcion_contexto,
        mantener_contexto=datos.mantener_contexto,
        asistencia_conversacional=datos.asistencia_conversacional,
    )
    # HU-31: el participante 1 habla el idioma de origen y el 2 el de destino
    conversacion.participantes = [
        ParticipanteConversacion(
            nombre=f"Participante {ORDEN_PARTICIPANTE_ORIGEN}",
            id_idioma=datos.id_idioma_origen,
            orden=ORDEN_PARTICIPANTE_ORIGEN,
        ),
        ParticipanteConversacion(
            nombre=f"Participante {ORDEN_PARTICIPANTE_DESTINO}",
            id_idioma=datos.id_idioma_destino,
            orden=ORDEN_PARTICIPANTE_DESTINO,
        ),
    ]
    sesion.add(conversacion)
    sesion.commit()
    return obtener_conversacion_usuario(sesion, id_usuario, conversacion.id_conversacion)


def actualizar_conversacion(
    sesion: Session,
    id_usuario: int,
    id_conversacion: int,
    datos: ActualizarConversacionSolicitud,
) -> Conversacion:
    """
    Modifica la configuracion (entorno, contexto, tono, descripcion e interruptores)
    mientras la conversacion no este finalizada. Solo cambia los campos enviados.
    Los idiomas no se modifican.
    """
    conversacion = obtener_conversacion_usuario(sesion, id_usuario, id_conversacion)
    if conversacion.estado == ESTADO_FINALIZADA:
        raise ValueError("La conversacion esta finalizada; no se puede modificar.")

    campos = datos.model_fields_set

    if "id_entorno" in campos and datos.id_entorno is not None:
        obtener_entorno_activo(sesion, datos.id_entorno)
        conversacion.id_entorno = datos.id_entorno

    if "id_contexto" in campos:
        if datos.id_contexto is not None:
            _validar_contexto(sesion, id_usuario, datos.id_contexto)
        conversacion.id_contexto = datos.id_contexto

    if "id_tono" in campos:
        if datos.id_tono is not None:
            _validar_tono(sesion, datos.id_tono)
        conversacion.id_tono = datos.id_tono

    if "descripcion_contexto" in campos:
        conversacion.descripcion_contexto = datos.descripcion_contexto

    if "mantener_contexto" in campos and datos.mantener_contexto is not None:
        conversacion.mantener_contexto = datos.mantener_contexto

    if "asistencia_conversacional" in campos and datos.asistencia_conversacional is not None:
        conversacion.asistencia_conversacional = datos.asistencia_conversacional

    conversacion.fecha_actualizacion = _ahora()
    sesion.commit()
    sesion.expire_all()
    return obtener_conversacion_usuario(sesion, id_usuario, id_conversacion)


def _cambiar_estado(
    sesion: Session,
    id_usuario: int,
    id_conversacion: int,
    estados_permitidos: tuple[str, ...],
    nuevo_estado: str,
    mensaje_error: str,
) -> Conversacion:
    conversacion = obtener_conversacion_usuario(sesion, id_usuario, id_conversacion)
    if conversacion.estado not in estados_permitidos:
        raise ValueError(f"{mensaje_error} Estado actual: {conversacion.estado}.")

    ahora = _ahora()
    conversacion.estado = nuevo_estado
    conversacion.fecha_actualizacion = ahora
    if nuevo_estado == ESTADO_FINALIZADA:
        conversacion.fecha_fin = ahora
    sesion.commit()
    sesion.expire_all()
    return obtener_conversacion_usuario(sesion, id_usuario, id_conversacion)


def pausar_conversacion(sesion: Session, id_usuario: int, id_conversacion: int) -> Conversacion:
    return _cambiar_estado(
        sesion, id_usuario, id_conversacion,
        estados_permitidos=(ESTADO_ACTIVA,),
        nuevo_estado=ESTADO_PAUSADA,
        mensaje_error="Solo se puede pausar una conversacion activa.",
    )


def reanudar_conversacion(sesion: Session, id_usuario: int, id_conversacion: int) -> Conversacion:
    return _cambiar_estado(
        sesion, id_usuario, id_conversacion,
        estados_permitidos=(ESTADO_PAUSADA,),
        nuevo_estado=ESTADO_ACTIVA,
        mensaje_error="Solo se puede reanudar una conversacion pausada.",
    )


def finalizar_conversacion(sesion: Session, id_usuario: int, id_conversacion: int) -> Conversacion:
    return _cambiar_estado(
        sesion, id_usuario, id_conversacion,
        estados_permitidos=(ESTADO_ACTIVA, ESTADO_PAUSADA),
        nuevo_estado=ESTADO_FINALIZADA,
        mensaje_error="La conversacion ya esta finalizada.",
    )


# ---------------------------------------------------------------------------
# Participantes (HU-31)
# ---------------------------------------------------------------------------


def listar_participantes(
    sesion: Session,
    id_usuario: int,
    id_conversacion: int,
) -> list[ParticipanteConversacion]:
    """Participantes de una conversacion del usuario, por orden."""
    conversacion = obtener_conversacion_usuario(sesion, id_usuario, id_conversacion)
    return list(conversacion.participantes)


def renombrar_participante(
    sesion: Session,
    id_usuario: int,
    id_conversacion: int,
    id_participante: int,
    nombre: str,
) -> ParticipanteConversacion:
    """Cambia el nombre o etiqueta de un participante mientras la conversacion no este finalizada."""
    conversacion = obtener_conversacion_usuario(sesion, id_usuario, id_conversacion)
    if conversacion.estado == ESTADO_FINALIZADA:
        raise ValueError("La conversacion esta finalizada; no se puede modificar.")

    participante = next(
        (p for p in conversacion.participantes if p.id_participante == id_participante),
        None,
    )
    if not participante:
        raise ParticipanteNoEncontradoError(
            "Participante no encontrado en la conversacion indicada."
        )

    participante.nombre = nombre
    conversacion.fecha_actualizacion = _ahora()
    sesion.commit()
    sesion.expire_all()
    actualizada = obtener_conversacion_usuario(sesion, id_usuario, id_conversacion)
    return next(p for p in actualizada.participantes if p.id_participante == id_participante)

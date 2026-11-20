"""
Chats entre usuarios (Etapa 1: REST). No confundir con `conversaciones` (interprete de un dispositivo).

Reglas:
- El id_usuario siempre lo aporta el endpoint a partir del token. Quien no es miembro de un chat
  recibe ChatNoEncontradoError (404), igual que si el chat no existiera.
- Enviar un mensaje solo lo guarda ('pendiente'); la deteccion de idioma y la traduccion se hacen
  en segundo plano con su propia sesion de base de datos (`procesar_mensaje`).
- Cada destinatario recibe el mensaje en su idioma de lectura de ese chat (solo NLLB). Si cambia ese
  idioma se retraducen en segundo plano los ultimos mensajes; mientras tanto se entrega el original
  con estado_lectura 'pendiente'.
- El texto de los mensajes nunca se escribe en los logs.
"""

import logging
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.conexion import FabricaSesiones
from app.models.chat.chat import Chat
from app.models.chat.mensaje_chat import (
    ESTADO_MENSAJE_ERROR,
    ESTADO_MENSAJE_PENDIENTE,
    ESTADO_MENSAJE_PROCESADO,
    MensajeChat,
)
from app.models.chat.participante_chat import ParticipanteChat
from app.models.chat.traduccion_mensaje_chat import (
    ESTADO_TRADUCCION_ERROR,
    ESTADO_TRADUCCION_PENDIENTE,
    ESTADO_TRADUCCION_SIN_TRADUCCION,
    ESTADO_TRADUCCION_TRADUCIDO,
    TraduccionMensajeChat,
)
from app.models.traduccion.idioma import Idioma
from app.models.usuario.usuario import Usuario
from app.schemas.chat import ChatDetalle, IdiomaResumen, MensajeChatDetalle, UsuarioChatResumen
from app.services.configuracion_traduccion import obtener_configuracion_usuario
from app.services.traduccion import detector_idioma
from app.services.traduccion_contextual import traducir_con_configuracion
from app.services.usuarios import ESTADO_ACTIVO


logger = logging.getLogger(__name__)

# Busqueda de usuarios
LONGITUD_MINIMA_BUSQUEDA = 2
LIMITE_BUSQUEDA_MAXIMO = 20

# Deteccion de idioma: por debajo de esto se usa el idioma de lectura del remitente
UMBRAL_CONFIANZA_DETECCION = 0.7
LONGITUD_MINIMA_DETECCION = 15
PALABRAS_MINIMAS_DETECCION = 3

# Al cambiar el idioma de lectura se retraducen como maximo estos mensajes recibidos
MENSAJES_A_RETRADUCIR = 50

# Antiabuso: mensajes por usuario en la ultima ventana (se cuenta en la base de datos)
MAXIMO_MENSAJES_POR_MINUTO = 20

# NLLB consume mucha CPU/memoria: como maximo estas traducciones de chat a la vez por proceso
MAXIMO_TRADUCCIONES_SIMULTANEAS = 2
_semaforo_traduccion = threading.BoundedSemaphore(MAXIMO_TRADUCCIONES_SIMULTANEAS)

CODIGO_IDIOMA_POR_DEFECTO = "es"
MENSAJE_ERROR_TRADUCCION = "No se pudo traducir el mensaje."
MENSAJE_ERROR_INTERRUMPIDO = "El procesamiento se interrumpio por un reinicio del servidor."


class ChatNoEncontradoError(ValueError):
    """El chat no existe o el usuario autenticado no es miembro."""


class UsuarioNoDisponibleError(ValueError):
    """El usuario no existe o no esta activo."""


class MensajeNoEncontradoError(ValueError):
    """El mensaje no existe en ese chat."""


class LimiteMensajesError(ValueError):
    """Se supero el numero de mensajes permitidos por minuto."""


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


@contextmanager
def _abrir_sesion() -> Iterator[Session]:
    """Sesion propia para las tareas en segundo plano (la del endpoint ya se cerro)."""
    sesion = FabricaSesiones()
    try:
        yield sesion
    finally:
        sesion.close()


def _detectar(texto: str) -> dict:
    return detector_idioma.detectar(texto)


def _traducir(sesion: Session, id_usuario: int, texto: str, codigo_origen: str, codigo_destino: str) -> str:
    """Solo NLLB: sin glosario, sin modelo de lenguaje (todas las opciones de enriquecimiento apagadas)."""
    resultado = traducir_con_configuracion(
        sesion=sesion,
        id_usuario=id_usuario,
        texto=texto,
        idioma_origen=codigo_origen,
        idioma_destino=codigo_destino,
    )
    return resultado.traduccion


# ---------------------------------------------------------------------------
# Idiomas
# ---------------------------------------------------------------------------


def _idioma_por_codigo(sesion: Session, codigo: str) -> Idioma:
    idioma = sesion.scalar(select(Idioma).where(Idioma.codigo == codigo.strip().lower()))
    if idioma is None:
        raise ValueError(f"El idioma '{codigo}' no existe.")
    return idioma


def _idioma_predeterminado(sesion: Session, id_usuario: int) -> Idioma:
    """Idioma de destino preferido del usuario (HU-33); si no tiene, espanol."""
    configuracion = obtener_configuracion_usuario(sesion, id_usuario)
    if configuracion is not None and configuracion.id_idioma_destino:
        idioma = sesion.get(Idioma, configuracion.id_idioma_destino)
        if idioma is not None:
            return idioma
    idioma = sesion.scalar(select(Idioma).where(Idioma.codigo == CODIGO_IDIOMA_POR_DEFECTO))
    if idioma is None:
        idioma = sesion.scalar(select(Idioma).order_by(Idioma.id_idioma))
    if idioma is None:
        raise ValueError("No hay idiomas registrados en el sistema.")
    return idioma


def _codigos_idioma(sesion: Session) -> dict[int, str]:
    return dict(sesion.execute(select(Idioma.id_idioma, Idioma.codigo)).all())


# ---------------------------------------------------------------------------
# Usuarios y chats
# ---------------------------------------------------------------------------


def buscar_usuarios(sesion: Session, id_usuario: int, texto: str, limite: int) -> list[Usuario]:
    """Usuarios activos cuyo nombre contiene `texto` (sin el propio usuario)."""
    texto = texto.strip()
    if len(texto) < LONGITUD_MINIMA_BUSQUEDA:
        raise ValueError(f"Escribe al menos {LONGITUD_MINIMA_BUSQUEDA} caracteres para buscar.")
    limite = max(1, min(limite, LIMITE_BUSQUEDA_MAXIMO))
    patron = texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return list(
        sesion.scalars(
            select(Usuario)
            .where(
                Usuario.nombre.ilike(f"%{patron}%", escape="\\"),
                Usuario.estado == ESTADO_ACTIVO,
                Usuario.id != id_usuario,
            )
            .order_by(Usuario.nombre, Usuario.id)
            .limit(limite)
        )
    )


def _buscar_chat_del_par(sesion: Session, id_a: int, id_b: int) -> Chat | None:
    menor, mayor = sorted((id_a, id_b))
    return sesion.scalar(
        select(Chat).where(Chat.id_usuario_menor == menor, Chat.id_usuario_mayor == mayor)
    )


def crear_u_obtener_chat(
    sesion: Session,
    id_usuario: int,
    id_otro_usuario: int,
    codigo_idioma_lectura: str | None = None,
) -> tuple[Chat, bool]:
    """
    Devuelve (chat, creado). Idempotente: si el par ya tiene chat se devuelve ese (el idioma
    indicado solo se usa al crearlo; despues se cambia con cambiar_idioma_lectura).
    """
    if id_otro_usuario == id_usuario:
        raise ValueError("No puedes iniciar un chat contigo mismo.")
    otro = sesion.scalar(
        select(Usuario).where(Usuario.id == id_otro_usuario, Usuario.estado == ESTADO_ACTIVO)
    )
    if otro is None:
        raise UsuarioNoDisponibleError("El usuario no existe o no esta disponible.")
    idioma_mio = (
        _idioma_por_codigo(sesion, codigo_idioma_lectura)
        if codigo_idioma_lectura
        else _idioma_predeterminado(sesion, id_usuario)
    )

    existente = _buscar_chat_del_par(sesion, id_usuario, id_otro_usuario)
    if existente is not None:
        return existente, False

    idioma_otro = _idioma_predeterminado(sesion, id_otro_usuario)
    menor, mayor = sorted((id_usuario, id_otro_usuario))
    chat = Chat(id_usuario_menor=menor, id_usuario_mayor=mayor)
    sesion.add(chat)
    try:
        sesion.flush()
        sesion.add_all([
            ParticipanteChat(id_chat=chat.id_chat, id_usuario=id_usuario, id_idioma_lectura=idioma_mio.id_idioma),
            ParticipanteChat(id_chat=chat.id_chat, id_usuario=id_otro_usuario, id_idioma_lectura=idioma_otro.id_idioma),
        ])
        sesion.commit()
    except IntegrityError:
        # Otro request creo el mismo par a la vez: se devuelve ese
        sesion.rollback()
        existente = _buscar_chat_del_par(sesion, id_usuario, id_otro_usuario)
        if existente is None:
            raise
        return existente, False
    sesion.refresh(chat)
    return chat, True


def _participacion(sesion: Session, id_chat: int, id_usuario: int) -> ParticipanteChat:
    participacion = sesion.get(ParticipanteChat, (id_chat, id_usuario))
    if participacion is None:
        raise ChatNoEncontradoError("El chat no existe o no perteneces a el.")
    return participacion


def _otros_participantes(sesion: Session, id_chat: int, id_usuario: int) -> list[ParticipanteChat]:
    return list(
        sesion.scalars(
            select(ParticipanteChat).where(
                ParticipanteChat.id_chat == id_chat,
                ParticipanteChat.id_usuario != id_usuario,
            )
        )
    )


def _contar_no_leidos(sesion: Session, participacion: ParticipanteChat) -> int:
    return sesion.scalar(
        select(func.count(MensajeChat.id_mensaje)).where(
            MensajeChat.id_chat == participacion.id_chat,
            MensajeChat.id_remitente != participacion.id_usuario,
            MensajeChat.id_mensaje > func.coalesce(participacion.id_ultimo_mensaje_leido, 0),
        )
    ) or 0


def detalle_chat(sesion: Session, id_chat: int, id_usuario: int) -> ChatDetalle:
    yo = _participacion(sesion, id_chat, id_usuario)
    chat = sesion.get(Chat, id_chat)
    otro = _otros_participantes(sesion, id_chat, id_usuario)[0]
    usuario_otro = sesion.get(Usuario, otro.id_usuario)
    idioma = sesion.get(Idioma, yo.id_idioma_lectura)

    ultimo = sesion.scalar(
        select(MensajeChat).where(MensajeChat.id_chat == id_chat).order_by(MensajeChat.id_mensaje.desc()).limit(1)
    )
    return ChatDetalle(
        id_chat=chat.id_chat,
        otro_usuario=UsuarioChatResumen(id_usuario=usuario_otro.id, nombre=usuario_otro.nombre),
        mi_idioma_lectura=IdiomaResumen(id_idioma=idioma.id_idioma, codigo=idioma.codigo, nombre=idioma.nombre),
        ultimo_mensaje=detalles_mensajes(sesion, [ultimo], yo)[0] if ultimo else None,
        no_leidos=_contar_no_leidos(sesion, yo),
        fecha_creacion=chat.fecha_creacion,
        fecha_ultimo_mensaje=chat.fecha_ultimo_mensaje,
    )


def listar_chats(sesion: Session, id_usuario: int) -> list[ChatDetalle]:
    """Mis chats, del de actividad mas reciente al mas antiguo."""
    ids = sesion.scalars(
        select(Chat.id_chat)
        .join(ParticipanteChat, ParticipanteChat.id_chat == Chat.id_chat)
        .where(ParticipanteChat.id_usuario == id_usuario)
        .order_by(func.coalesce(Chat.fecha_ultimo_mensaje, Chat.fecha_creacion).desc(), Chat.id_chat.desc())
    ).all()
    return [detalle_chat(sesion, id_chat, id_usuario) for id_chat in ids]


# ---------------------------------------------------------------------------
# Mensajes
# ---------------------------------------------------------------------------


def detalles_mensajes(
    sesion: Session,
    mensajes: list[MensajeChat],
    yo: ParticipanteChat,
) -> list[MensajeChatDetalle]:
    """Arma cada mensaje tal como lo debe ver `yo` (traduccion u original con su estado)."""
    if not mensajes:
        return []
    codigos = _codigos_idioma(sesion)
    traducciones = {
        fila.id_mensaje: fila
        for fila in sesion.scalars(
            select(TraduccionMensajeChat).where(
                TraduccionMensajeChat.id_mensaje.in_([m.id_mensaje for m in mensajes]),
                TraduccionMensajeChat.id_destinatario == yo.id_usuario,
            )
        )
    }

    detalles = []
    for mensaje in mensajes:
        idioma_original = codigos.get(mensaje.id_idioma_detectado) if mensaje.id_idioma_detectado else None
        texto = mensaje.texto_original
        idioma_texto = idioma_original
        fila = traducciones.get(mensaje.id_mensaje)

        if mensaje.id_remitente == yo.id_usuario:
            estado = "propio"
        elif mensaje.estado == ESTADO_MENSAJE_ERROR:
            estado = "error"
        elif mensaje.estado == ESTADO_MENSAJE_PENDIENTE or fila is None:
            estado = "pendiente"
        elif fila.id_idioma_destino != yo.id_idioma_lectura:
            # Se cambio el idioma de lectura y la nueva traduccion aun no esta
            estado = "pendiente"
        elif fila.estado == ESTADO_TRADUCCION_TRADUCIDO and fila.texto_traducido is not None:
            estado = "traducido"
            texto = fila.texto_traducido
            idioma_texto = codigos.get(fila.id_idioma_destino)
        elif fila.estado == ESTADO_TRADUCCION_SIN_TRADUCCION:
            estado = "sin_traduccion"
        elif fila.estado == ESTADO_TRADUCCION_ERROR:
            estado = "error"
        else:
            estado = "pendiente"

        detalles.append(MensajeChatDetalle(
            id_mensaje=mensaje.id_mensaje,
            id_chat=mensaje.id_chat,
            id_remitente=mensaje.id_remitente,
            es_mio=mensaje.id_remitente == yo.id_usuario,
            texto=texto,
            texto_original=mensaje.texto_original,
            idioma_original=idioma_original,
            idioma_texto=idioma_texto,
            estado_lectura=estado,
            fecha_envio=mensaje.fecha_envio,
        ))
    return detalles


def enviar_mensaje(sesion: Session, id_chat: int, id_usuario: int, texto: str) -> tuple[MensajeChat, ParticipanteChat]:
    """Guarda el mensaje como 'pendiente' (la traduccion la hace `procesar_mensaje` despues)."""
    yo = _participacion(sesion, id_chat, id_usuario)
    texto = texto.strip()
    if not texto:
        raise ValueError("El mensaje no puede estar vacio.")

    for otro in _otros_participantes(sesion, id_chat, id_usuario):
        activo = sesion.scalar(
            select(Usuario.id).where(Usuario.id == otro.id_usuario, Usuario.estado == ESTADO_ACTIVO)
        )
        if activo is None:
            raise ValueError("El otro usuario no esta disponible.")

    enviados = sesion.scalar(
        select(func.count(MensajeChat.id_mensaje)).where(
            MensajeChat.id_remitente == id_usuario,
            MensajeChat.fecha_envio >= _ahora() - timedelta(minutes=1),
        )
    ) or 0
    if enviados >= MAXIMO_MENSAJES_POR_MINUTO:
        raise LimiteMensajesError("Estas enviando demasiados mensajes. Espera un momento.")

    ahora = _ahora()
    mensaje = MensajeChat(id_chat=id_chat, id_remitente=id_usuario, texto_original=texto, fecha_envio=ahora)
    sesion.add(mensaje)
    sesion.flush()
    sesion.get(Chat, id_chat).fecha_ultimo_mensaje = ahora
    # Lo propio cuenta como leido
    yo.id_ultimo_mensaje_leido = mensaje.id_mensaje
    yo.fecha_ultimo_acceso = ahora
    sesion.commit()
    sesion.refresh(mensaje)
    return mensaje, yo


def _preparar_traduccion(sesion: Session, mensaje: MensajeChat, id_destinatario: int, id_idioma_destino: int) -> bool:
    """
    Deja la fila de traduccion apuntando al idioma indicado. Devuelve True si hay que traducir
    (queda 'pendiente') y False si el mensaje ya esta en ese idioma ('sin_traduccion').
    """
    fila = sesion.scalar(
        select(TraduccionMensajeChat).where(
            TraduccionMensajeChat.id_mensaje == mensaje.id_mensaje,
            TraduccionMensajeChat.id_destinatario == id_destinatario,
        )
    )
    if fila is None:
        fila = TraduccionMensajeChat(id_mensaje=mensaje.id_mensaje, id_destinatario=id_destinatario)
        sesion.add(fila)
    fila.id_idioma_destino = id_idioma_destino
    fila.texto_traducido = None
    fila.error = None
    if mensaje.id_idioma_detectado == id_idioma_destino:
        fila.estado = ESTADO_TRADUCCION_SIN_TRADUCCION
        return False
    fila.estado = ESTADO_TRADUCCION_PENDIENTE
    return True


def _marcar_desactualizados(sesion: Session, mensajes: list[MensajeChat], yo: ParticipanteChat) -> list[int]:
    """
    Mensajes recibidos ya procesados cuya traduccion no esta en mi idioma de lectura actual:
    se dejan 'pendiente' y se devuelven sus ids para retraducirlos en segundo plano.
    """
    candidatos = [
        m for m in mensajes if m.id_remitente != yo.id_usuario and m.estado == ESTADO_MENSAJE_PROCESADO
    ]
    if not candidatos:
        return []
    actuales = {
        fila.id_mensaje: fila
        for fila in sesion.scalars(
            select(TraduccionMensajeChat).where(
                TraduccionMensajeChat.id_mensaje.in_([m.id_mensaje for m in candidatos]),
                TraduccionMensajeChat.id_destinatario == yo.id_usuario,
            )
        )
    }
    a_traducir = []
    for mensaje in candidatos:
        fila = actuales.get(mensaje.id_mensaje)
        if fila is not None and fila.id_idioma_destino == yo.id_idioma_lectura:
            continue
        if _preparar_traduccion(sesion, mensaje, yo.id_usuario, yo.id_idioma_lectura):
            a_traducir.append(mensaje.id_mensaje)
    return a_traducir


def listar_mensajes(
    sesion: Session,
    id_chat: int,
    id_usuario: int,
    *,
    despues_de: int | None = None,
    antes_de: int | None = None,
    limite: int = 50,
) -> tuple[list[MensajeChatDetalle], bool, list[int]]:
    """
    Pagina de mensajes en orden ascendente y si hay mas. `despues_de`: los nuevos tras ese id
    (para consultar cada pocos segundos); `antes_de` o nada: los mas recientes anteriores a ese id.
    Tambien devuelve los ids que hay que retraducir (traduccion en otro idioma de lectura).
    """
    if despues_de is not None and antes_de is not None:
        raise ValueError("Usa solo uno de los filtros: despues_de o antes_de.")
    yo = _participacion(sesion, id_chat, id_usuario)

    consulta = select(MensajeChat).where(MensajeChat.id_chat == id_chat)
    if despues_de is not None:
        filas = list(sesion.scalars(
            consulta.where(MensajeChat.id_mensaje > despues_de).order_by(MensajeChat.id_mensaje).limit(limite + 1)
        ))
        hay_mas = len(filas) > limite
        mensajes = filas[:limite]
    else:
        if antes_de is not None:
            consulta = consulta.where(MensajeChat.id_mensaje < antes_de)
        filas = list(sesion.scalars(consulta.order_by(MensajeChat.id_mensaje.desc()).limit(limite + 1)))
        hay_mas = len(filas) > limite
        mensajes = list(reversed(filas[:limite]))

    a_traducir = _marcar_desactualizados(sesion, mensajes, yo)
    yo.fecha_ultimo_acceso = _ahora()
    sesion.commit()
    return detalles_mensajes(sesion, mensajes, yo), hay_mas, a_traducir


def cambiar_idioma_lectura(sesion: Session, id_chat: int, id_usuario: int, codigo_idioma: str) -> list[int]:
    """
    Cambia mi idioma de lectura en el chat y deja 'pendiente' la traduccion de los ultimos
    MENSAJES_A_RETRADUCIR mensajes recibidos. Devuelve sus ids para retraducirlos en segundo plano.
    Los mas antiguos se retraducen cuando se consultan (listar_mensajes).
    """
    yo = _participacion(sesion, id_chat, id_usuario)
    idioma = _idioma_por_codigo(sesion, codigo_idioma)
    if yo.id_idioma_lectura == idioma.id_idioma:
        return []
    yo.id_idioma_lectura = idioma.id_idioma
    recientes = list(sesion.scalars(
        select(MensajeChat)
        .where(MensajeChat.id_chat == id_chat, MensajeChat.id_remitente != id_usuario)
        .order_by(MensajeChat.id_mensaje.desc())
        .limit(MENSAJES_A_RETRADUCIR)
    ))
    a_traducir = _marcar_desactualizados(sesion, recientes, yo)
    sesion.commit()
    return a_traducir


def marcar_leido(sesion: Session, id_chat: int, id_usuario: int, id_mensaje: int) -> tuple[int | None, int]:
    """Marca como leido hasta `id_mensaje` (nunca retrocede). Devuelve (ultimo leido, no leidos)."""
    yo = _participacion(sesion, id_chat, id_usuario)
    existe = sesion.scalar(
        select(MensajeChat.id_mensaje).where(MensajeChat.id_mensaje == id_mensaje, MensajeChat.id_chat == id_chat)
    )
    if existe is None:
        raise MensajeNoEncontradoError("El mensaje no existe en este chat.")
    yo.id_ultimo_mensaje_leido = max(yo.id_ultimo_mensaje_leido or 0, id_mensaje)
    yo.fecha_ultimo_acceso = _ahora()
    sesion.commit()
    return yo.id_ultimo_mensaje_leido, _contar_no_leidos(sesion, yo)


# ---------------------------------------------------------------------------
# Segundo plano: deteccion de idioma y traduccion
# ---------------------------------------------------------------------------


def _resolver_idioma(texto: str, codigo_respaldo: str) -> tuple[str, float | None, bool]:
    """
    (codigo, confianza, por_respaldo). Con textos cortos o deteccion poco fiable se usa el idioma
    de lectura del remitente: se asume que escribe en el idioma en que lee.
    """
    if len(texto) < LONGITUD_MINIMA_DETECCION or len(texto.split()) < PALABRAS_MINIMAS_DETECCION:
        return codigo_respaldo, None, True
    try:
        deteccion = _detectar(texto)
    except Exception:  # noqa: BLE001
        return codigo_respaldo, None, True
    confianza = float(deteccion.get("confianza") or 0)
    if confianza < UMBRAL_CONFIANZA_DETECCION:
        return codigo_respaldo, confianza, True
    return deteccion["codigo"], confianza, False


def _traducir_para(sesion: Session, id_mensaje: int, id_destinatario: int) -> None:
    """
    Traduce un mensaje al idioma de lectura actual del destinatario. Si ese idioma cambia mientras
    se traduce, se vuelve a intentar una vez con el nuevo; nunca se guarda una traduccion en un
    idioma que ya no corresponde.
    """
    for _ in range(2):
        sesion.expire_all()
        mensaje = sesion.get(MensajeChat, id_mensaje)
        participante = sesion.get(ParticipanteChat, (mensaje.id_chat, id_destinatario)) if mensaje else None
        if mensaje is None or participante is None or mensaje.estado != ESTADO_MENSAJE_PROCESADO:
            return
        id_destino = participante.id_idioma_lectura
        necesita = _preparar_traduccion(sesion, mensaje, id_destinatario, id_destino)
        codigos = _codigos_idioma(sesion)
        texto, id_remitente = mensaje.texto_original, mensaje.id_remitente
        codigo_origen, codigo_destino = codigos[mensaje.id_idioma_detectado], codigos[id_destino]
        sesion.commit()
        if not necesita:
            return

        try:
            with _semaforo_traduccion:
                traduccion = _traducir(sesion, id_remitente, texto, codigo_origen, codigo_destino)
            error = None
        except Exception as fallo:  # noqa: BLE001
            # Solo el tipo de error: el mensaje de la excepcion podria contener el texto
            logger.warning("No se pudo traducir el mensaje de chat %s (%s)", id_mensaje, type(fallo).__name__)
            traduccion, error = None, MENSAJE_ERROR_TRADUCCION

        sesion.expire_all()
        participante = sesion.get(ParticipanteChat, (mensaje.id_chat, id_destinatario))
        if participante is None:
            return
        if participante.id_idioma_lectura != id_destino:
            continue  # cambio el idioma de lectura mientras se traducia
        fila = sesion.scalar(
            select(TraduccionMensajeChat).where(
                TraduccionMensajeChat.id_mensaje == id_mensaje,
                TraduccionMensajeChat.id_destinatario == id_destinatario,
            )
        )
        if fila is None or fila.id_idioma_destino != id_destino:
            return
        if error:
            fila.estado, fila.error, fila.texto_traducido = ESTADO_TRADUCCION_ERROR, error, None
        else:
            fila.estado, fila.error, fila.texto_traducido = ESTADO_TRADUCCION_TRADUCIDO, None, traduccion
        sesion.commit()
        return


def _procesar_mensaje(sesion: Session, id_mensaje: int) -> None:
    mensaje = sesion.get(MensajeChat, id_mensaje)
    if mensaje is None or mensaje.estado != ESTADO_MENSAJE_PENDIENTE:
        return
    remitente = sesion.get(ParticipanteChat, (mensaje.id_chat, mensaje.id_remitente))
    idioma_respaldo = sesion.get(Idioma, remitente.id_idioma_lectura)
    texto = mensaje.texto_original
    sesion.commit()  # no se deja una transaccion abierta mientras se detecta el idioma

    codigo, confianza, por_respaldo = _resolver_idioma(texto, idioma_respaldo.codigo)
    idioma = sesion.scalar(select(Idioma).where(Idioma.codigo == codigo))
    if idioma is None:
        # Idioma detectado que el sistema no maneja
        idioma, por_respaldo = idioma_respaldo, True

    mensaje = sesion.get(MensajeChat, id_mensaje)
    mensaje.id_idioma_detectado = idioma.id_idioma
    mensaje.confianza_deteccion = confianza
    mensaje.idioma_por_respaldo = por_respaldo
    mensaje.estado = ESTADO_MENSAJE_PROCESADO
    destinatarios = [p.id_usuario for p in _otros_participantes(sesion, mensaje.id_chat, mensaje.id_remitente)]
    sesion.commit()

    for id_destinatario in destinatarios:
        _traducir_para(sesion, id_mensaje, id_destinatario)


def procesar_mensaje(id_mensaje: int) -> None:
    """Tarea en segundo plano tras enviar un mensaje: detecta el idioma y traduce."""
    with _abrir_sesion() as sesion:
        try:
            _procesar_mensaje(sesion, id_mensaje)
        except Exception as fallo:  # noqa: BLE001
            logger.error("Error al procesar el mensaje de chat %s (%s)", id_mensaje, type(fallo).__name__)
            sesion.rollback()
            sesion.execute(
                update(MensajeChat)
                .where(MensajeChat.id_mensaje == id_mensaje, MensajeChat.estado == ESTADO_MENSAJE_PENDIENTE)
                .values(estado=ESTADO_MENSAJE_ERROR)
            )
            sesion.commit()


def retraducir_mensajes(ids_mensajes: list[int], id_destinatario: int) -> None:
    """Tarea en segundo plano tras cambiar el idioma de lectura (o consultar mensajes desactualizados)."""
    with _abrir_sesion() as sesion:
        for id_mensaje in ids_mensajes:
            try:
                _traducir_para(sesion, id_mensaje, id_destinatario)
            except Exception as fallo:  # noqa: BLE001
                logger.error("Error al retraducir el mensaje de chat %s (%s)", id_mensaje, type(fallo).__name__)
                sesion.rollback()


def marcar_pendientes_como_error(sesion: Session) -> tuple[int, int]:
    """
    Al arrancar: las tareas en segundo plano no sobreviven a un reinicio, asi que lo que quedo
    'pendiente' pasa a 'error' (el cliente muestra el original). Devuelve (mensajes, traducciones).
    """
    mensajes = sesion.execute(
        update(MensajeChat)
        .where(MensajeChat.estado == ESTADO_MENSAJE_PENDIENTE)
        .values(estado=ESTADO_MENSAJE_ERROR)
    ).rowcount
    traducciones = sesion.execute(
        update(TraduccionMensajeChat)
        .where(TraduccionMensajeChat.estado == ESTADO_TRADUCCION_PENDIENTE)
        .values(estado=ESTADO_TRADUCCION_ERROR, error=MENSAJE_ERROR_INTERRUMPIDO)
    ).rowcount
    sesion.commit()
    return mensajes, traducciones

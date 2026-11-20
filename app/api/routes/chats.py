from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.database.conexion import obtener_sesion
from app.models.usuario.usuario import Usuario
from app.schemas.chat import (
    ActualizarContextoChatSolicitud,
    BuscarUsuariosRespuesta,
    CambiarIdiomaLecturaSolicitud,
    CrearChatSolicitud,
    EnviarMensajeSolicitud,
    ListaChatsRespuesta,
    ListaMensajesRespuesta,
    MarcarLeidoSolicitud,
    PaginaMensajes,
    RespuestaChat,
    RespuestaLeido,
    RespuestaMensaje,
    ResultadoLeido,
    UsuarioChatResumen,
)
from app.services import chats as servicio
from app.services.chats import (
    ChatNoEncontradoError,
    LimiteMensajesError,
    MensajeNoEncontradoError,
    UsuarioNoDisponibleError,
)
from app.services.usuarios import obtener_usuario_actual


enrutador = APIRouter(prefix="/chats", tags=["chats"])

RESPUESTA_401 = {status.HTTP_401_UNAUTHORIZED: {"description": "El token es invalido, expiro o no fue enviado."}}
RESPUESTA_404_CHAT = {
    status.HTTP_404_NOT_FOUND: {"description": "El chat no existe o no eres miembro (no se distingue)."}
}


def _a_http(error: ValueError) -> HTTPException:
    """NoEncontrado -> 404, limite -> 429, resto de ValueError -> 400."""
    if isinstance(error, (ChatNoEncontradoError, UsuarioNoDisponibleError, MensajeNoEncontradoError)):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, LimiteMensajesError):
        return HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(error))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@enrutador.get(
    "/usuarios",
    response_model=BuscarUsuariosRespuesta,
    summary="Buscar usuarios para chatear (requiere token)",
    description=(
        "Usuarios activos cuyo nombre contiene el texto (minimo 2 caracteres). Solo devuelve id y "
        "nombre; nunca el correo. Excluye al propio usuario."
    ),
    responses=RESPUESTA_401,
)
def buscar_usuarios(
    q: str = Query(..., min_length=servicio.LONGITUD_MINIMA_BUSQUEDA, max_length=100, description="Texto a buscar en el nombre"),
    limite: int = Query(default=10, ge=1, le=servicio.LIMITE_BUSQUEDA_MAXIMO),
    usuario: Usuario = Depends(obtener_usuario_actual),
    sesion: Session = Depends(obtener_sesion),
) -> BuscarUsuariosRespuesta:
    try:
        encontrados = servicio.buscar_usuarios(sesion, usuario.id, q, limite)
    except ValueError as error:
        raise _a_http(error) from error
    return BuscarUsuariosRespuesta(
        mensaje="Usuarios obtenidos correctamente.",
        resultado=[UsuarioChatResumen(id_usuario=u.id, nombre=u.nombre) for u in encontrados],
    )


@enrutador.post(
    "",
    response_model=RespuestaChat,
    status_code=status.HTTP_201_CREATED,
    summary="Crear u obtener el chat con otro usuario (requiere token)",
    description=(
        "Idempotente: si ya existe un chat con ese usuario se devuelve (200); si no, se crea (201). "
        "'codigo_idioma_lectura' solo se usa al crearlo."
    ),
    responses={
        **RESPUESTA_401,
        status.HTTP_200_OK: {"description": "El chat ya existia.", "model": RespuestaChat},
        status.HTTP_400_BAD_REQUEST: {"description": "Chat contigo mismo, idioma o contexto inexistente."},
        status.HTTP_404_NOT_FOUND: {"description": "El usuario no existe o no esta activo."},
    },
)
def crear_chat(
    datos: CrearChatSolicitud,
    respuesta: Response,
    usuario: Usuario = Depends(obtener_usuario_actual),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaChat:
    try:
        campos_contexto = datos.model_dump(include={"id_contexto", "descripcion_contexto"}, exclude_unset=True)
        chat, creado = servicio.crear_u_obtener_chat(
            sesion, usuario.id, datos.id_usuario, datos.codigo_idioma_lectura, campos_contexto
        )
        detalle = servicio.detalle_chat(sesion, chat.id_chat, usuario.id)
    except ValueError as error:
        raise _a_http(error) from error
    if not creado:
        respuesta.status_code = status.HTTP_200_OK
    return RespuestaChat(
        mensaje="Chat creado correctamente." if creado else "Chat obtenido correctamente.",
        resultado=detalle,
    )


@enrutador.get(
    "",
    response_model=ListaChatsRespuesta,
    summary="Listar mis chats (requiere token)",
    description="Del mas reciente al mas antiguo, con el ultimo mensaje (en mi idioma) y los no leidos.",
    responses=RESPUESTA_401,
)
def listar_chats(
    usuario: Usuario = Depends(obtener_usuario_actual),
    sesion: Session = Depends(obtener_sesion),
) -> ListaChatsRespuesta:
    return ListaChatsRespuesta(
        mensaje="Chats obtenidos correctamente.",
        resultado=servicio.listar_chats(sesion, usuario.id),
    )


@enrutador.get(
    "/{id_chat}",
    response_model=RespuestaChat,
    summary="Obtener un chat (requiere token)",
    responses={**RESPUESTA_401, **RESPUESTA_404_CHAT},
)
def obtener_chat(
    id_chat: int,
    usuario: Usuario = Depends(obtener_usuario_actual),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaChat:
    try:
        detalle = servicio.detalle_chat(sesion, id_chat, usuario.id)
    except ValueError as error:
        raise _a_http(error) from error
    return RespuestaChat(mensaje="Chat obtenido correctamente.", resultado=detalle)


@enrutador.patch(
    "/{id_chat}/idioma-lectura",
    response_model=RespuestaChat,
    summary="Cambiar mi idioma de lectura en un chat (requiere token)",
    description=(
        f"Los ultimos {servicio.MENSAJES_A_RETRADUCIR} mensajes recibidos se retraducen en segundo plano; "
        "hasta que esten listos se entrega el original con estado_lectura 'pendiente'."
    ),
    responses={**RESPUESTA_401, **RESPUESTA_404_CHAT, status.HTTP_400_BAD_REQUEST: {"description": "Idioma inexistente."}},
)
def cambiar_idioma_lectura(
    id_chat: int,
    datos: CambiarIdiomaLecturaSolicitud,
    tareas: BackgroundTasks,
    usuario: Usuario = Depends(obtener_usuario_actual),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaChat:
    try:
        a_traducir = servicio.cambiar_idioma_lectura(sesion, id_chat, usuario.id, datos.codigo_idioma)
        detalle = servicio.detalle_chat(sesion, id_chat, usuario.id)
    except ValueError as error:
        raise _a_http(error) from error
    if a_traducir:
        tareas.add_task(servicio.retraducir_mensajes, a_traducir, usuario.id)
    return RespuestaChat(mensaje="Idioma de lectura actualizado correctamente.", resultado=detalle)


@enrutador.patch(
    "/{id_chat}/contexto",
    response_model=RespuestaChat,
    summary="Cambiar el contexto de un chat (requiere token)",
    description=(
        "Contexto de dominio y/o descripcion libre de la conversacion, comun a los dos miembros. Solo "
        "se cambian los campos enviados; null los quita. Con contexto, las traducciones de los "
        "mensajes nuevos se adaptan a el; los mensajes ya traducidos no cambian."
    ),
    responses={**RESPUESTA_401, **RESPUESTA_404_CHAT, status.HTTP_400_BAD_REQUEST: {"description": "Contexto inexistente o inactivo."}},
)
def actualizar_contexto(
    id_chat: int,
    datos: ActualizarContextoChatSolicitud,
    usuario: Usuario = Depends(obtener_usuario_actual),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaChat:
    try:
        servicio.actualizar_contexto(sesion, id_chat, usuario.id, datos.model_dump(exclude_unset=True))
        detalle = servicio.detalle_chat(sesion, id_chat, usuario.id)
    except ValueError as error:
        raise _a_http(error) from error
    return RespuestaChat(mensaje="Contexto del chat actualizado correctamente.", resultado=detalle)


@enrutador.post(
    "/{id_chat}/mensajes",
    response_model=RespuestaMensaje,
    status_code=status.HTTP_201_CREATED,
    summary="Enviar un mensaje (requiere token)",
    description=(
        "Se guarda y se responde al instante. La deteccion de idioma y la traduccion para el otro "
        "usuario se hacen en segundo plano; consultalo con GET /chats/{id_chat}/mensajes. El otro "
        "usuario recibe un aviso MENSAJE_CHAT (bandeja y push) con datos.id_chat."
    ),
    responses={
        **RESPUESTA_401,
        **RESPUESTA_404_CHAT,
        status.HTTP_400_BAD_REQUEST: {"description": "El otro usuario ya no esta disponible."},
        status.HTTP_429_TOO_MANY_REQUESTS: {"description": "Demasiados mensajes por minuto."},
    },
)
def enviar_mensaje(
    id_chat: int,
    datos: EnviarMensajeSolicitud,
    tareas: BackgroundTasks,
    usuario: Usuario = Depends(obtener_usuario_actual),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaMensaje:
    try:
        mensaje, yo = servicio.enviar_mensaje(sesion, id_chat, usuario.id, datos.texto)
    except ValueError as error:
        raise _a_http(error) from error
    detalle = servicio.detalles_mensajes(sesion, [mensaje], yo)[0]
    servicio.notificar_nuevo_mensaje(sesion, mensaje, tareas)
    tareas.add_task(servicio.procesar_mensaje, mensaje.id_mensaje)
    return RespuestaMensaje(mensaje="Mensaje enviado correctamente.", resultado=detalle)


@enrutador.get(
    "/{id_chat}/mensajes",
    response_model=ListaMensajesRespuesta,
    summary="Listar mensajes de un chat (requiere token)",
    description=(
        "Orden ascendente. Con 'despues_de' devuelve los nuevos tras ese id (consulta periodica); con "
        "'antes_de' (o sin filtros) los mas recientes anteriores. 'texto' viene en mi idioma de lectura "
        "cuando estado_lectura es 'traducido'; en los demas casos es el original."
    ),
    responses={**RESPUESTA_401, **RESPUESTA_404_CHAT, status.HTTP_400_BAD_REQUEST: {"description": "Filtros incompatibles."}},
)
def listar_mensajes(
    id_chat: int,
    tareas: BackgroundTasks,
    despues_de: int | None = Query(default=None, ge=0),
    antes_de: int | None = Query(default=None, ge=1),
    limite: int = Query(default=50, ge=1, le=100),
    usuario: Usuario = Depends(obtener_usuario_actual),
    sesion: Session = Depends(obtener_sesion),
) -> ListaMensajesRespuesta:
    try:
        elementos, hay_mas, a_traducir = servicio.listar_mensajes(
            sesion, id_chat, usuario.id, despues_de=despues_de, antes_de=antes_de, limite=limite
        )
    except ValueError as error:
        raise _a_http(error) from error
    if a_traducir:
        tareas.add_task(servicio.retraducir_mensajes, a_traducir, usuario.id)
    return ListaMensajesRespuesta(
        mensaje="Mensajes obtenidos correctamente.",
        resultado=PaginaMensajes(elementos=elementos, hay_mas=hay_mas),
    )


@enrutador.post(
    "/{id_chat}/leido",
    response_model=RespuestaLeido,
    summary="Marcar mensajes como leidos (requiere token)",
    description=(
        "Marca como leidos todos los mensajes hasta 'id_mensaje' inclusive. Nunca retrocede. Si ya no "
        "quedan no leidos, el aviso MENSAJE_CHAT de ese chat queda leido en la bandeja."
    ),
    responses={**RESPUESTA_401, **RESPUESTA_404_CHAT},
)
def marcar_leido(
    id_chat: int,
    datos: MarcarLeidoSolicitud,
    usuario: Usuario = Depends(obtener_usuario_actual),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaLeido:
    try:
        ultimo, no_leidos = servicio.marcar_leido(sesion, id_chat, usuario.id, datos.id_mensaje)
    except ValueError as error:
        raise _a_http(error) from error
    return RespuestaLeido(
        mensaje="Mensajes marcados como leidos.",
        resultado=ResultadoLeido(id_ultimo_mensaje_leido=ultimo, no_leidos=no_leidos),
    )

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.seguridad import requiere_token
from app.database.conexion import obtener_sesion
from app.models.usuario.usuario import Usuario
from app.schemas.asistencia import RespuestaAsistencia, SolicitudAsistencia
from app.schemas.conversacion import (
    ActualizarConversacionSolicitud,
    ActualizarParticipanteSolicitud,
    EstadoConversacion,
    IniciarConversacionSolicitud,
    ListaConversacionesRespuesta,
    ListaParticipantesRespuesta,
    RespuestaConversacion,
    RespuestaParticipante,
)
from app.services.asistencia_conversacional import (
    AsistenciaNoDisponibleError,
    solicitar_asistencia,
)
from app.services.conversaciones import (
    ConversacionNoEncontradaError,
    actualizar_conversacion,
    armar_detalle_conversacion,
    armar_detalle_participante,
    finalizar_conversacion,
    iniciar_conversacion,
    listar_conversaciones_usuario,
    listar_participantes,
    obtener_conversacion_usuario,
    pausar_conversacion,
    reanudar_conversacion,
    renombrar_participante,
)


enrutador = APIRouter(
    prefix="/conversaciones",
    tags=["conversaciones"],
    dependencies=[Depends(requiere_token)],
)

RESPUESTAS_COMUNES = {
    status.HTTP_401_UNAUTHORIZED: {
        "description": "El token es invalido, expiro o no fue enviado."
    },
}
RESPUESTA_404 = {
    status.HTTP_404_NOT_FOUND: {
        "description": "La conversacion no existe o no pertenece al usuario autenticado."
    },
}
RESPUESTA_400_TRANSICION = {
    status.HTTP_400_BAD_REQUEST: {
        "description": "La transicion de estado no es valida para el estado actual."
    },
}


def _error_http(error: ValueError) -> HTTPException:
    """Traduce errores del servicio a respuestas HTTP (404 si no existe, 400 en otro caso)."""
    if isinstance(error, ConversacionNoEncontradaError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@enrutador.post(
    "",
    response_model=RespuestaConversacion,
    status_code=status.HTTP_201_CREATED,
    summary="Iniciar una conversacion (requiere token)",
    description=(
        "Inicia una sesion de conversacion del usuario autenticado con idioma de origen y "
        "destino (distintos), contexto opcional y entorno. La sesion inicia en estado 'activa'."
    ),
    responses={
        **RESPUESTAS_COMUNES,
        status.HTTP_400_BAD_REQUEST: {
            "description": (
                "Idioma, contexto o entorno inexistente o inactivo, o glosario ajeno o de otro par de idiomas."
            )
        },
    },
)
def iniciar_nueva_conversacion(
    datos: IniciarConversacionSolicitud,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaConversacion:
    try:
        conversacion = iniciar_conversacion(sesion=sesion, id_usuario=usuario.id, datos=datos)
    except ValueError as error:
        raise _error_http(error) from error

    return RespuestaConversacion(
        mensaje="Conversacion iniciada correctamente.",
        resultado=armar_detalle_conversacion(conversacion),
    )


@enrutador.get(
    "",
    response_model=ListaConversacionesRespuesta,
    status_code=status.HTTP_200_OK,
    summary="Listar mis conversaciones (requiere token)",
    description=(
        "Retorna las conversaciones del usuario autenticado, de la mas reciente a la mas "
        "antigua. Use 'estado' para filtrar (activa, pausada o finalizada)."
    ),
    responses=RESPUESTAS_COMUNES,
)
def listar_mis_conversaciones(
    estado: EstadoConversacion | None = Query(
        default=None,
        description="Filtrar por estado: activa, pausada o finalizada",
    ),
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> ListaConversacionesRespuesta:
    conversaciones = listar_conversaciones_usuario(
        sesion=sesion,
        id_usuario=usuario.id,
        estado=estado,
    )
    return ListaConversacionesRespuesta(
        mensaje="Conversaciones obtenidas correctamente.",
        resultado=[armar_detalle_conversacion(c) for c in conversaciones],
    )


@enrutador.get(
    "/{id_conversacion}",
    response_model=RespuestaConversacion,
    status_code=status.HTTP_200_OK,
    summary="Consultar una conversacion (requiere token)",
    responses={**RESPUESTAS_COMUNES, **RESPUESTA_404},
)
def consultar_conversacion(
    id_conversacion: int,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaConversacion:
    try:
        conversacion = obtener_conversacion_usuario(
            sesion=sesion,
            id_usuario=usuario.id,
            id_conversacion=id_conversacion,
        )
    except ValueError as error:
        raise _error_http(error) from error

    return RespuestaConversacion(
        mensaje="Conversacion obtenida correctamente.",
        resultado=armar_detalle_conversacion(conversacion),
    )


@enrutador.patch(
    "/{id_conversacion}",
    response_model=RespuestaConversacion,
    status_code=status.HTTP_200_OK,
    summary="Modificar la configuracion de una conversacion (requiere token)",
    description=(
        "Cambia entorno, contexto, tono, glosario, descripcion del contexto y opciones mientras la "
        "conversacion no este finalizada. Solo se modifican los campos enviados; los idiomas no cambian. "
        "El glosario debe ser del usuario y del mismo par de idiomas (en cualquier sentido)."
    ),
    responses={
        **RESPUESTAS_COMUNES,
        **RESPUESTA_404,
        status.HTTP_400_BAD_REQUEST: {
            "description": (
                "Conversacion finalizada, entorno, contexto o tono inexistente o inactivo, o glosario "
                "ajeno o de otro par de idiomas."
            )
        },
    },
)
def modificar_conversacion(
    id_conversacion: int,
    datos: ActualizarConversacionSolicitud,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaConversacion:
    try:
        conversacion = actualizar_conversacion(
            sesion=sesion,
            id_usuario=usuario.id,
            id_conversacion=id_conversacion,
            datos=datos,
        )
    except ValueError as error:
        raise _error_http(error) from error

    return RespuestaConversacion(
        mensaje="Conversacion actualizada correctamente.",
        resultado=armar_detalle_conversacion(conversacion),
    )


@enrutador.post(
    "/{id_conversacion}/pausar",
    response_model=RespuestaConversacion,
    status_code=status.HTTP_200_OK,
    summary="Pausar una conversacion activa (requiere token)",
    description="Mientras la conversacion esta pausada no se procesan nuevas intervenciones.",
    responses={**RESPUESTAS_COMUNES, **RESPUESTA_404, **RESPUESTA_400_TRANSICION},
)
def pausar(
    id_conversacion: int,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaConversacion:
    try:
        conversacion = pausar_conversacion(sesion, usuario.id, id_conversacion)
    except ValueError as error:
        raise _error_http(error) from error

    return RespuestaConversacion(
        mensaje="Conversacion pausada correctamente.",
        resultado=armar_detalle_conversacion(conversacion),
    )


@enrutador.post(
    "/{id_conversacion}/reanudar",
    response_model=RespuestaConversacion,
    status_code=status.HTTP_200_OK,
    summary="Reanudar una conversacion pausada (requiere token)",
    description="La conversacion conserva su configuracion e intervenciones previas.",
    responses={**RESPUESTAS_COMUNES, **RESPUESTA_404, **RESPUESTA_400_TRANSICION},
)
def reanudar(
    id_conversacion: int,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaConversacion:
    try:
        conversacion = reanudar_conversacion(sesion, usuario.id, id_conversacion)
    except ValueError as error:
        raise _error_http(error) from error

    return RespuestaConversacion(
        mensaje="Conversacion reanudada correctamente.",
        resultado=armar_detalle_conversacion(conversacion),
    )


@enrutador.post(
    "/{id_conversacion}/finalizar",
    response_model=RespuestaConversacion,
    status_code=status.HTTP_200_OK,
    summary="Finalizar una conversacion (requiere token)",
    description=(
        "Finaliza una conversacion activa o pausada. Una conversacion finalizada no admite "
        "nuevas intervenciones ni puede reanudarse."
    ),
    responses={**RESPUESTAS_COMUNES, **RESPUESTA_404, **RESPUESTA_400_TRANSICION},
)
def finalizar(
    id_conversacion: int,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaConversacion:
    try:
        conversacion = finalizar_conversacion(sesion, usuario.id, id_conversacion)
    except ValueError as error:
        raise _error_http(error) from error

    return RespuestaConversacion(
        mensaje="Conversacion finalizada correctamente.",
        resultado=armar_detalle_conversacion(conversacion),
    )


# ---------------------------------------------------------------------------
# Participantes (HU-31)
# ---------------------------------------------------------------------------


@enrutador.get(
    "/{id_conversacion}/participantes",
    response_model=ListaParticipantesRespuesta,
    status_code=status.HTTP_200_OK,
    summary="Listar los participantes de una conversacion (requiere token)",
    description="Devuelve los dos participantes de la sesion con su idioma, por orden.",
    responses={**RESPUESTAS_COMUNES, **RESPUESTA_404},
)
def obtener_participantes(
    id_conversacion: int,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> ListaParticipantesRespuesta:
    try:
        participantes = listar_participantes(sesion, usuario.id, id_conversacion)
    except ValueError as error:
        raise _error_http(error) from error

    return ListaParticipantesRespuesta(
        mensaje="Participantes obtenidos correctamente.",
        resultado=[armar_detalle_participante(p) for p in participantes],
    )


@enrutador.patch(
    "/{id_conversacion}/participantes/{id_participante}",
    response_model=RespuestaParticipante,
    status_code=status.HTTP_200_OK,
    summary="Renombrar un participante (requiere token)",
    description="Cambia el nombre o etiqueta de un participante mientras la conversacion no este finalizada.",
    responses={
        **RESPUESTAS_COMUNES,
        status.HTTP_404_NOT_FOUND: {
            "description": "La conversacion o el participante no existen o no pertenecen al usuario."
        },
        status.HTTP_400_BAD_REQUEST: {"description": "La conversacion esta finalizada."},
    },
)
def modificar_participante(
    id_conversacion: int,
    id_participante: int,
    datos: ActualizarParticipanteSolicitud,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaParticipante:
    try:
        participante = renombrar_participante(
            sesion=sesion,
            id_usuario=usuario.id,
            id_conversacion=id_conversacion,
            id_participante=id_participante,
            nombre=datos.nombre,
        )
    except ValueError as error:
        raise _error_http(error) from error

    return RespuestaParticipante(
        mensaje="Participante actualizado correctamente.",
        resultado=armar_detalle_participante(participante),
    )


# ---------------------------------------------------------------------------
# Asistencia conversacional (HU-30)
# ---------------------------------------------------------------------------


@enrutador.post(
    "/{id_conversacion}/asistencia",
    response_model=RespuestaAsistencia,
    status_code=status.HTTP_200_OK,
    summary="Pedir asistencia conversacional (requiere token)",
    description=(
        "Asistencia bajo demanda con la asistencia activada y la conversacion no finalizada. "
        "'explicacion': explica una intervencion (expresiones, referencias e intencion). "
        "'sugerencias': propone respuestas a una intervencion para quien la escucha. "
        "'como_decir': recomienda como expresar la idea de 'texto' en el idioma de 'id_participante' "
        "segun el entorno. Sin 'id_intervencion' se usa la ultima intervencion traducida. "
        "No modifica la conversacion ni bloquea el envio de intervenciones."
    ),
    responses={
        **RESPUESTAS_COMUNES,
        status.HTTP_404_NOT_FOUND: {
            "description": "La conversacion, la intervencion o el participante no existen o no son del usuario."
        },
        status.HTTP_400_BAD_REQUEST: {
            "description": (
                "Conversacion finalizada, asistencia desactivada, intervencion sin traducir o "
                "sin intervenciones traducidas."
            )
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "El modelo de lenguaje no respondio; se puede volver a intentar."
        },
    },
)
def pedir_asistencia(
    id_conversacion: int,
    datos: SolicitudAsistencia,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaAsistencia:
    try:
        resultado = solicitar_asistencia(
            sesion=sesion,
            id_usuario=usuario.id,
            id_conversacion=id_conversacion,
            datos=datos,
        )
    except AsistenciaNoDisponibleError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except ValueError as error:
        raise _error_http(error) from error

    return RespuestaAsistencia(
        mensaje="Asistencia generada correctamente.",
        resultado=resultado,
    )

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.seguridad import requiere_token
from app.database.conexion import obtener_sesion
from app.models.usuario.usuario import Usuario
from app.schemas.intervencion import (
    CrearIntervencionSolicitud,
    ListaIntervencionesRespuesta,
    RespuestaIntervencion,
)
from app.services.conversaciones import ConversacionNoEncontradaError
from app.services.intervenciones import (
    armar_detalle_intervencion,
    crear_intervencion,
    listar_intervenciones,
    reintentar_intervencion,
)


# Las rutas son 'def' (no 'async def'), como /traducciones: FastAPI las ejecuta en un hilo aparte
# y la traduccion con NLLB no bloquea el servidor.
enrutador = APIRouter(
    prefix="/conversaciones",
    tags=["intervenciones"],
    dependencies=[Depends(requiere_token)],
)

RESPUESTAS_COMUNES = {
    status.HTTP_401_UNAUTHORIZED: {
        "description": "El token es invalido, expiro o no fue enviado."
    },
}
RESPUESTA_404 = {
    status.HTTP_404_NOT_FOUND: {
        "description": (
            "La conversacion no existe o no pertenece al usuario, o el participante o la "
            "intervencion no pertenecen a la conversacion."
        )
    },
}


def _error_http(error: ValueError) -> HTTPException:
    """Traduce errores del servicio a respuestas HTTP (404 si no existe, 400 en otro caso)."""
    if isinstance(error, ConversacionNoEncontradaError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


def _mensaje_resultado(estado: str) -> str:
    if estado == "traducida":
        return "Intervencion traducida correctamente."
    return "La intervencion se registro, pero no se pudo traducir."


@enrutador.post(
    "/{id_conversacion}/intervenciones",
    response_model=RespuestaIntervencion,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar y traducir una intervencion escrita (requiere token)",
    description=(
        "Registra la intervencion del participante indicado y la traduce del idioma de ese "
        "participante al idioma del otro participante, con el tono, contexto y entorno de la sesion. "
        "Si la traduccion falla, la intervencion queda en estado 'error' (201) y puede reintentarse. "
        "Sin 'id_participante' la intervencion queda como 'No identificado': se detecta su idioma, "
        "que debe ser uno de los dos de la sesion con confianza suficiente."
    ),
    responses={
        **RESPUESTAS_COMUNES,
        **RESPUESTA_404,
        status.HTTP_400_BAD_REQUEST: {
            "description": (
                "La conversacion esta pausada o finalizada, o no se pudo identificar el idioma "
                "de una intervencion sin participante."
            )
        },
    },
)
def registrar_intervencion(
    id_conversacion: int,
    datos: CrearIntervencionSolicitud,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaIntervencion:
    try:
        intervencion = crear_intervencion(
            sesion=sesion,
            id_usuario=usuario.id,
            id_conversacion=id_conversacion,
            datos=datos,
        )
    except ValueError as error:
        raise _error_http(error) from error

    return RespuestaIntervencion(
        mensaje=_mensaje_resultado(intervencion.estado),
        resultado=armar_detalle_intervencion(intervencion),
    )


@enrutador.get(
    "/{id_conversacion}/intervenciones",
    response_model=ListaIntervencionesRespuesta,
    status_code=status.HTTP_200_OK,
    summary="Listar las intervenciones de una conversacion (requiere token)",
    description=(
        "Devuelve las intervenciones en orden ascendente. Con 'despues_de' (id de una intervencion "
        "de la misma conversacion) devuelve solo las posteriores."
    ),
    responses={**RESPUESTAS_COMUNES, **RESPUESTA_404},
)
def obtener_intervenciones(
    id_conversacion: int,
    despues_de: int | None = Query(
        default=None,
        ge=1,
        description="Id de la ultima intervencion conocida; se devuelven solo las posteriores",
    ),
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> ListaIntervencionesRespuesta:
    try:
        intervenciones = listar_intervenciones(sesion, usuario.id, id_conversacion, despues_de)
    except ValueError as error:
        raise _error_http(error) from error

    return ListaIntervencionesRespuesta(
        mensaje="Intervenciones obtenidas correctamente.",
        resultado=[armar_detalle_intervencion(i) for i in intervenciones],
    )


@enrutador.post(
    "/{id_conversacion}/intervenciones/{id_intervencion}/reintentar",
    response_model=RespuestaIntervencion,
    status_code=status.HTTP_200_OK,
    summary="Reintentar la traduccion de una intervencion (requiere token)",
    description=(
        "Vuelve a traducir una intervencion en estado 'error' (o 'procesando' interrumpida) con la "
        "configuracion actual de la sesion, que debe estar activa."
    ),
    responses={
        **RESPUESTAS_COMUNES,
        **RESPUESTA_404,
        status.HTTP_400_BAD_REQUEST: {
            "description": "La conversacion no esta activa o la intervencion no admite reintento."
        },
    },
)
def reintentar(
    id_conversacion: int,
    id_intervencion: int,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaIntervencion:
    try:
        intervencion = reintentar_intervencion(sesion, usuario.id, id_conversacion, id_intervencion)
    except ValueError as error:
        raise _error_http(error) from error

    return RespuestaIntervencion(
        mensaje=_mensaje_resultado(intervencion.estado),
        resultado=armar_detalle_intervencion(intervencion),
    )

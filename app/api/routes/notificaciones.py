import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.conexion import obtener_sesion
from app.models.usuario.usuario import Usuario
from app.schemas.notificacion import (
    ListaNotificacionesPaginada,
    ListaNotificacionesRespuesta,
    NotificacionDetalle,
    RespuestaMarcarLeidas,
    RespuestaNotificacion,
    ResultadoMarcarLeidas,
)
from app.services.notificaciones import (
    NotificacionNoEncontradaError,
    listar_notificaciones,
    marcar_como_leida,
    marcar_todas_como_leidas,
)
from app.services.usuarios import obtener_usuario_actual


enrutador = APIRouter(prefix="/notificaciones", tags=["notificaciones"])

RESPUESTAS_COMUNES = {
    status.HTTP_401_UNAUTHORIZED: {
        "description": "El token es invalido, expiro o no fue enviado."
    },
}


@enrutador.get(
    "",
    response_model=ListaNotificacionesRespuesta,
    status_code=status.HTTP_200_OK,
    summary="Listar mis notificaciones (requiere token)",
    description=(
        "Bandeja paginada del usuario autenticado, de la mas reciente a la mas antigua. "
        "Incluye 'no_leidas' (total sin leer) para mostrar el contador en la app."
    ),
    responses=RESPUESTAS_COMUNES,
)
def listar_mis_notificaciones(
    solo_no_leidas: bool = Query(default=False, description="Si es True, solo devuelve las no leidas"),
    pagina: int = Query(default=1, ge=1),
    tamano_pagina: int = Query(default=20, ge=1, le=100),
    usuario: Usuario = Depends(obtener_usuario_actual),
    sesion: Session = Depends(obtener_sesion),
) -> ListaNotificacionesRespuesta:
    elementos, total, no_leidas = listar_notificaciones(
        sesion,
        usuario.id,
        solo_no_leidas=solo_no_leidas,
        pagina=pagina,
        tamano_pagina=tamano_pagina,
    )
    return ListaNotificacionesRespuesta(
        mensaje="Notificaciones obtenidas correctamente.",
        resultado=ListaNotificacionesPaginada(
            elementos=[NotificacionDetalle.model_validate(n) for n in elementos],
            total=total,
            no_leidas=no_leidas,
            pagina=pagina,
            tamano_pagina=tamano_pagina,
            total_paginas=math.ceil(total / tamano_pagina) if total else 0,
        ),
    )


@enrutador.patch(
    "/leidas",
    response_model=RespuestaMarcarLeidas,
    status_code=status.HTTP_200_OK,
    summary="Marcar todas mis notificaciones como leidas (requiere token)",
    responses=RESPUESTAS_COMUNES,
)
def marcar_mis_notificaciones_leidas(
    usuario: Usuario = Depends(obtener_usuario_actual),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaMarcarLeidas:
    actualizadas = marcar_todas_como_leidas(sesion, usuario.id)
    return RespuestaMarcarLeidas(
        mensaje="Notificaciones marcadas como leidas.",
        resultado=ResultadoMarcarLeidas(actualizadas=actualizadas),
    )


@enrutador.patch(
    "/{id_notificacion}/leida",
    response_model=RespuestaNotificacion,
    status_code=status.HTTP_200_OK,
    summary="Marcar una notificacion como leida (requiere token)",
    responses={
        **RESPUESTAS_COMUNES,
        status.HTTP_404_NOT_FOUND: {
            "description": "La notificacion no existe o no pertenece al usuario autenticado."
        },
    },
)
def marcar_mi_notificacion_leida(
    id_notificacion: int,
    usuario: Usuario = Depends(obtener_usuario_actual),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaNotificacion:
    try:
        notificacion = marcar_como_leida(sesion, usuario.id, id_notificacion)
    except NotificacionNoEncontradaError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    return RespuestaNotificacion(
        mensaje="Notificacion marcada como leida.",
        resultado=NotificacionDetalle.model_validate(notificacion),
    )

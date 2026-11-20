from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.conexion import obtener_sesion
from app.models.usuario.usuario import Usuario
from app.schemas.notificacion import (
    DispositivoDetalle,
    RegistrarDispositivoSolicitud,
    RespuestaDispositivo,
    RespuestaEliminarDispositivo,
)
from app.services.notificaciones import (
    DispositivoNoEncontradoError,
    eliminar_dispositivo,
    registrar_dispositivo,
)
from app.services.usuarios import obtener_usuario_actual


enrutador = APIRouter(prefix="/dispositivos", tags=["notificaciones"])

RESPUESTAS_COMUNES = {
    status.HTTP_401_UNAUTHORIZED: {
        "description": "El token es invalido, expiro o no fue enviado."
    },
}


@enrutador.post(
    "",
    response_model=RespuestaDispositivo,
    status_code=status.HTTP_200_OK,
    summary="Registrar dispositivo para notificaciones push (requiere token)",
    description=(
        "Registra o actualiza el token de FCM del dispositivo del usuario autenticado. Es idempotente: "
        "si el token ya existe se actualiza y, si pertenecia a otra cuenta, pasa a la cuenta actual. "
        "La app debe llamarlo despues de iniciar sesion y cada vez que FCM renueve el token."
    ),
    responses=RESPUESTAS_COMUNES,
)
def registrar_mi_dispositivo(
    datos: RegistrarDispositivoSolicitud,
    usuario: Usuario = Depends(obtener_usuario_actual),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaDispositivo:
    dispositivo = registrar_dispositivo(
        sesion,
        id_usuario=usuario.id,
        token_fcm=datos.token_fcm,
        plataforma=datos.plataforma,
    )
    return RespuestaDispositivo(
        mensaje="Dispositivo registrado correctamente.",
        resultado=DispositivoDetalle.model_validate(dispositivo),
    )


@enrutador.delete(
    "/{token_fcm}",
    response_model=RespuestaEliminarDispositivo,
    status_code=status.HTTP_200_OK,
    summary="Eliminar dispositivo (requiere token)",
    description=(
        "Elimina el token de FCM del usuario autenticado para que el dispositivo deje de recibir push. "
        "La app debe llamarlo antes de cerrar sesion."
    ),
    responses={
        **RESPUESTAS_COMUNES,
        status.HTTP_404_NOT_FOUND: {
            "description": "El dispositivo no existe o no pertenece al usuario autenticado."
        },
    },
)
def eliminar_mi_dispositivo(
    token_fcm: str,
    usuario: Usuario = Depends(obtener_usuario_actual),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaEliminarDispositivo:
    try:
        eliminar_dispositivo(sesion, id_usuario=usuario.id, token_fcm=token_fcm)
    except DispositivoNoEncontradoError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    return RespuestaEliminarDispositivo(mensaje="Dispositivo eliminado correctamente.")

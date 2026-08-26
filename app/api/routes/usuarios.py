from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.conexion import obtener_sesion
from app.schemas.usuario import (
    RegistroUsuarioRespuesta,
    RegistroUsuarioSolicitud,
    VerificarCodigoRespuesta,
    VerificarCodigoSolicitud,
)
from app.services.usuarios import (
    CodigoVerificacionInvalidoError,
    CorreoYaRegistradoError,
    RolClienteNoExisteError,
    UsuarioYaActivoError,
    registrar_usuario,
    verificar_codigo_usuario,
)
from app.utilities.correo import CorreoNoConfiguradoError, EnvioCorreoError


enrutador = APIRouter(prefix="/usuarios", tags=["usuarios"])


@enrutador.post(
    "/registrar",
    response_model=RegistroUsuarioRespuesta,
    status_code=status.HTTP_201_CREATED,
)
def registrar_nuevo_usuario(
    datos: RegistroUsuarioSolicitud,
    sesion: Session = Depends(obtener_sesion),
) -> RegistroUsuarioRespuesta:
    try:
        usuario = registrar_usuario(sesion, datos)
    except CorreoYaRegistradoError as error:
        sesion.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except RolClienteNoExisteError as error:
        sesion.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error
    except (CorreoNoConfiguradoError, EnvioCorreoError) as error:
        sesion.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"No se pudo enviar el correo de verificacion: {error}",
        ) from error

    return RegistroUsuarioRespuesta(
        id=usuario.id,
        nombre=usuario.nombre,
        correo=usuario.correo,
        estado=usuario.estado,
        mensaje="Usuario registrado. Revisa tu correo para activar la cuenta.",
    )


@enrutador.post(
    "/verificar-codigo",
    response_model=VerificarCodigoRespuesta,
)
def verificar_codigo(
    datos: VerificarCodigoSolicitud,
    sesion: Session = Depends(obtener_sesion),
) -> VerificarCodigoRespuesta:
    try:
        usuario = verificar_codigo_usuario(sesion, datos)
    except (CodigoVerificacionInvalidoError, UsuarioYaActivoError) as error:
        sesion.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    return VerificarCodigoRespuesta(
        id=usuario.id,
        correo=usuario.correo,
        estado=usuario.estado,
        mensaje="Usuario verificado correctamente.",
    )

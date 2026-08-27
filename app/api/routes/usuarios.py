from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.conexion import obtener_sesion
from app.schemas.usuario import (
    ReenviarCodigoRespuesta,
    ReenviarCodigoResultado,
    ReenviarCodigoSolicitud,
    RegistroUsuarioResultado,
    RegistroUsuarioRespuesta,
    RegistroUsuarioSolicitud,
    VerificarCodigoResultado,
    VerificarCodigoRespuesta,
    VerificarCodigoSolicitud,
)
from app.services.usuarios import (
    CodigoVerificacionInvalidoError,
    CorreoYaRegistradoError,
    RolClienteNoExisteError,
    UsuarioNoEncontradoError,
    UsuarioYaActivoError,
    registrar_usuario,
    reenviar_codigo_verificacion,
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
            status_code=obtener_estado_error_correo(error),
            detail=obtener_mensaje_error_correo(error),
        ) from error

    return RegistroUsuarioRespuesta(
        mensaje="Usuario registrado. Revisa tu correo para activar la cuenta.",
        resultado=RegistroUsuarioResultado(
            id=usuario.id,
            nombre=usuario.nombre,
            correo=usuario.correo,
            estado=usuario.estado,
        ),
    )


@enrutador.post(
    "/reenviar-codigo",
    response_model=ReenviarCodigoRespuesta,
)
def reenviar_codigo(
    datos: ReenviarCodigoSolicitud,
    sesion: Session = Depends(obtener_sesion),
) -> ReenviarCodigoRespuesta:
    try:
        usuario = reenviar_codigo_verificacion(sesion, datos)
    except UsuarioNoEncontradoError as error:
        sesion.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except UsuarioYaActivoError as error:
        sesion.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    except (CorreoNoConfiguradoError, EnvioCorreoError) as error:
        sesion.rollback()
        raise HTTPException(
            status_code=obtener_estado_error_correo(error),
            detail=obtener_mensaje_error_correo(error),
        ) from error

    return ReenviarCodigoRespuesta(
        mensaje="Codigo de verificacion reenviado correctamente.",
        resultado=ReenviarCodigoResultado(
            correo=usuario.correo,
            estado=usuario.estado,
        ),
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
        mensaje="Usuario verificado correctamente.",
        resultado=VerificarCodigoResultado(
            id=usuario.id,
            correo=usuario.correo,
            estado=usuario.estado,
        ),
    )


def obtener_estado_error_correo(error: Exception) -> int:
    if isinstance(error, CorreoNoConfiguradoError):
        return status.HTTP_500_INTERNAL_SERVER_ERROR

    return status.HTTP_502_BAD_GATEWAY


def obtener_mensaje_error_correo(error: Exception) -> str:
    return f"No se pudo enviar el correo de verificacion: {error}"

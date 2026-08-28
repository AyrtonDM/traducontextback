from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.conexion import obtener_sesion
from app.api.dependencies import obtener_usuario_actual, requiere_permiso
from app.models.usuario.usuario import Usuario
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
    UsuarioDetalleRespuesta,
    ListaUsuariosRespuesta,
)
from app.services.usuarios import (
    CodigoVerificacionInvalidoError,
    CorreoYaRegistradoError,
    RolUsuarioNoExisteError,
    UsuarioNoEncontradoError,
    UsuarioYaActivoError,
    registrar_usuario,
    reenviar_codigo_verificacion,
    verificar_codigo_usuario,
    obtener_todos_usuarios,
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
    except RolUsuarioNoExisteError as error:
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


@enrutador.get(
    "/me",
    response_model=UsuarioDetalleRespuesta,
    status_code=status.HTTP_200_OK,
)
def obtener_mi_perfil(
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
) -> UsuarioDetalleRespuesta:
    return UsuarioDetalleRespuesta(
        mensaje="Usuario obtenido correctamente.",
        resultado=usuario_actual,
    )


@enrutador.get(
    "",
    response_model=ListaUsuariosRespuesta,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(requiere_permiso("gestionar_usuarios"))],
)
def listar_usuarios(
    sesion: Session = Depends(obtener_sesion),
) -> ListaUsuariosRespuesta:
    usuarios = obtener_todos_usuarios(sesion)
    return ListaUsuariosRespuesta(
        mensaje="Usuarios obtenidos correctamente.",
        resultado=usuarios,
    )


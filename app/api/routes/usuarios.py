import math
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.conexion import obtener_sesion
from app.core.seguridad import requiere_permiso
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
    UsuarioPerfilDetalle,
    RolDetalle,
    CambiarRolUsuarioSolicitud,
    ListaRolesRespuesta,
    ListaUsuariosPaginada,
    UsuarioAdminDetalle,
    UsuarioAdminRespuesta,
    UsuarioAdminResumen,
)
from app.services.usuarios import (
    CodigoVerificacionInvalidoError,
    CorreoYaRegistradoError,
    RolUsuarioNoExisteError,
    UsuarioNoEncontradoError,
    UsuarioYaActivoError,
    UsuarioSuspendidoError,
    OperacionAdministracionInvalidaError,
    RolNoEncontradoError,
    obtener_usuario_actual,
    registrar_usuario,
    reenviar_codigo_verificacion,
    verificar_codigo_usuario,
    obtener_permisos_usuario,
    listar_usuarios_admin,
    obtener_usuario_admin,
    obtener_resumen_actividad_usuario,
    suspender_usuario,
    reactivar_usuario,
    cambiar_rol_usuario,
    listar_roles,
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
    except UsuarioSuspendidoError as error:
        sesion.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(error),
        ) from error
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
    except UsuarioSuspendidoError as error:
        sesion.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(error),
        ) from error
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
    sesion: Session = Depends(obtener_sesion),
) -> UsuarioDetalleRespuesta:
    permisos = obtener_permisos_usuario(sesion, usuario_actual)

    return UsuarioDetalleRespuesta(
        mensaje="Usuario obtenido correctamente.",
        resultado=UsuarioPerfilDetalle(
            id=usuario_actual.id,
            nombre=usuario_actual.nombre,
            correo=usuario_actual.correo,
            estado=usuario_actual.estado,
            rol=RolDetalle.model_validate(usuario_actual.rol),
            permisos=permisos,
        ),
    )


# ---------------------------------------------------------------------------
# Administracion de usuarios (HU-05): solo roles con el permiso gestionar_usuarios
# ---------------------------------------------------------------------------

PERMISO_GESTIONAR_USUARIOS = "gestionar_usuarios"


def _armar_detalle_admin(sesion: Session, usuario: Usuario) -> UsuarioAdminDetalle:
    return UsuarioAdminDetalle(
        id=usuario.id,
        nombre=usuario.nombre,
        correo=usuario.correo,
        estado=usuario.estado,
        fecha_creacion=usuario.fecha_creacion,
        fecha_actualizacion=usuario.fecha_actualizacion,
        foto_perfil=usuario.foto_perfil,
        rol=RolDetalle.model_validate(usuario.rol),
        **obtener_resumen_actividad_usuario(sesion, usuario.id),
    )


def _error_administracion(error: Exception) -> HTTPException:
    if isinstance(error, (UsuarioNoEncontradoError, RolNoEncontradoError)):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@enrutador.get(
    "",
    response_model=ListaUsuariosRespuesta,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(requiere_permiso(PERMISO_GESTIONAR_USUARIOS))],
    summary="Listar usuarios (administrador)",
    description=(
        "Listado paginado de cuentas con nombre, correo, rol, estado y fecha de registro. "
        "Permite buscar por nombre o correo y filtrar por rol y estado. Los filtros se combinan."
    ),
)
def listar_usuarios(
    pagina: int = Query(default=1, ge=1),
    tamano_pagina: int = Query(default=10, ge=1, le=100),
    busqueda: str | None = Query(default=None, max_length=100, description="Nombre o correo"),
    id_rol: int | None = Query(default=None),
    estado: Literal["ACTIVO", "INACTIVO", "SUSPENDIDO"] | None = Query(default=None),
    sesion: Session = Depends(obtener_sesion),
) -> ListaUsuariosRespuesta:
    usuarios, total = listar_usuarios_admin(
        sesion,
        pagina=pagina,
        tamano_pagina=tamano_pagina,
        busqueda=busqueda,
        id_rol=id_rol,
        estado=estado,
    )
    return ListaUsuariosRespuesta(
        mensaje="Usuarios obtenidos correctamente.",
        resultado=ListaUsuariosPaginada(
            elementos=[UsuarioAdminResumen.model_validate(u) for u in usuarios],
            total=total,
            pagina=pagina,
            tamano_pagina=tamano_pagina,
            total_paginas=math.ceil(total / tamano_pagina) if total else 0,
        ),
    )


@enrutador.get(
    "/roles",
    response_model=ListaRolesRespuesta,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(requiere_permiso(PERMISO_GESTIONAR_USUARIOS))],
    summary="Listar roles disponibles (administrador)",
)
def listar_roles_disponibles(
    sesion: Session = Depends(obtener_sesion),
) -> ListaRolesRespuesta:
    return ListaRolesRespuesta(
        mensaje="Roles obtenidos correctamente.",
        resultado=[RolDetalle.model_validate(rol) for rol in listar_roles(sesion)],
    )


@enrutador.get(
    "/{id_usuario}",
    response_model=UsuarioAdminRespuesta,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(requiere_permiso(PERMISO_GESTIONAR_USUARIOS))],
    summary="Detalle de una cuenta (administrador)",
)
def obtener_detalle_usuario(
    id_usuario: int,
    sesion: Session = Depends(obtener_sesion),
) -> UsuarioAdminRespuesta:
    try:
        usuario = obtener_usuario_admin(sesion, id_usuario)
    except UsuarioNoEncontradoError as error:
        raise _error_administracion(error) from error

    return UsuarioAdminRespuesta(
        mensaje="Usuario obtenido correctamente.",
        resultado=_armar_detalle_admin(sesion, usuario),
    )


@enrutador.patch(
    "/{id_usuario}/suspender",
    response_model=UsuarioAdminRespuesta,
    status_code=status.HTTP_200_OK,
    summary="Suspender una cuenta (administrador)",
    description=(
        "Suspende una cuenta activa: el usuario no podra iniciar sesion y sus sesiones activas "
        "se invalidan. No se elimina la informacion asociada. No se puede suspender la propia cuenta."
    ),
)
def suspender_cuenta(
    id_usuario: int,
    administrador: Usuario = Depends(requiere_permiso(PERMISO_GESTIONAR_USUARIOS)),
    sesion: Session = Depends(obtener_sesion),
) -> UsuarioAdminRespuesta:
    try:
        usuario = suspender_usuario(sesion, administrador, id_usuario)
    except (UsuarioNoEncontradoError, OperacionAdministracionInvalidaError) as error:
        sesion.rollback()
        raise _error_administracion(error) from error

    return UsuarioAdminRespuesta(
        mensaje="Cuenta suspendida correctamente.",
        resultado=_armar_detalle_admin(sesion, usuario),
    )


@enrutador.patch(
    "/{id_usuario}/reactivar",
    response_model=UsuarioAdminRespuesta,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(requiere_permiso(PERMISO_GESTIONAR_USUARIOS))],
    summary="Reactivar una cuenta suspendida (administrador)",
)
def reactivar_cuenta(
    id_usuario: int,
    sesion: Session = Depends(obtener_sesion),
) -> UsuarioAdminRespuesta:
    try:
        usuario = reactivar_usuario(sesion, id_usuario)
    except (UsuarioNoEncontradoError, OperacionAdministracionInvalidaError) as error:
        sesion.rollback()
        raise _error_administracion(error) from error

    return UsuarioAdminRespuesta(
        mensaje="Cuenta reactivada correctamente.",
        resultado=_armar_detalle_admin(sesion, usuario),
    )


@enrutador.patch(
    "/{id_usuario}/rol",
    response_model=UsuarioAdminRespuesta,
    status_code=status.HTTP_200_OK,
    summary="Cambiar el rol de un usuario (administrador)",
    description="Cambia el rol de la cuenta. El administrador no puede quitarse su propio rol.",
)
def cambiar_rol(
    id_usuario: int,
    datos: CambiarRolUsuarioSolicitud,
    administrador: Usuario = Depends(requiere_permiso(PERMISO_GESTIONAR_USUARIOS)),
    sesion: Session = Depends(obtener_sesion),
) -> UsuarioAdminRespuesta:
    try:
        usuario = cambiar_rol_usuario(sesion, administrador, id_usuario, datos.id_rol)
    except (
        UsuarioNoEncontradoError,
        RolNoEncontradoError,
        OperacionAdministracionInvalidaError,
    ) as error:
        sesion.rollback()
        raise _error_administracion(error) from error

    return UsuarioAdminRespuesta(
        mensaje="Rol actualizado correctamente.",
        resultado=_armar_detalle_admin(sesion, usuario),
    )

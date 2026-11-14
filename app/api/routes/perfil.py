from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.seguridad import requiere_token
from app.database.conexion import obtener_sesion
from app.models.usuario.usuario import Usuario
from app.schemas.perfil import (
    ActualizarPerfilSolicitud,
    PerfilRespuesta,
)
from app.services.perfil import (
    CorreoEnUsoError,
    actualizar_perfil,
    armar_detalle_perfil,
)


enrutador = APIRouter(
    prefix="/perfil",
    tags=["perfil"],
    dependencies=[Depends(requiere_token)],
)


@enrutador.get(
    "",
    response_model=PerfilRespuesta,
    status_code=status.HTTP_200_OK,
    summary="Consultar mi perfil (requiere token)",
    description=(
        "Retorna la informacion del perfil del usuario autenticado: nombre, correo, "
        "estado, rol, fechas y su configuracion de traduccion. "
        "Requiere cabecera 'Authorization: Bearer <token>'."
    ),
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "El token es invalido, expiro o no fue enviado."
        },
    },
)
def consultar_perfil(
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> PerfilRespuesta:
    return PerfilRespuesta(
        mensaje="Perfil obtenido correctamente.",
        resultado=armar_detalle_perfil(sesion=sesion, usuario=usuario),
    )


@enrutador.patch(
    "",
    response_model=PerfilRespuesta,
    status_code=status.HTTP_200_OK,
    summary="Actualizar mi perfil (requiere token)",
    description=(
        "Actualiza el nombre y/o correo del usuario autenticado. Solo se modifican "
        "los campos enviados. El correo no puede pertenecer a otra cuenta. "
        "Requiere cabecera 'Authorization: Bearer <token>'."
    ),
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "El token es invalido, expiro o no fue enviado."
        },
        status.HTTP_409_CONFLICT: {
            "description": "El correo ya pertenece a otra cuenta."
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Los datos enviados no cumplen el formato requerido."
        },
    },
)
def actualizar_mi_perfil(
    datos: ActualizarPerfilSolicitud,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> PerfilRespuesta:
    try:
        usuario = actualizar_perfil(sesion=sesion, usuario=usuario, datos=datos)
    except CorreoEnUsoError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    return PerfilRespuesta(
        mensaje="Perfil actualizado correctamente.",
        resultado=armar_detalle_perfil(sesion=sesion, usuario=usuario),
    )


from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.seguridad import requiere_token
from app.database.conexion import obtener_sesion
from app.models.usuario.usuario import Usuario
from app.schemas.perfil import (
    ActualizarPerfilSolicitud,
    PerfilRespuesta,
)
from app.services.perfil import (
    TIPOS_MIME_POR_EXTENSION,
    FotoPerfilInvalidaError,
    actualizar_perfil,
    armar_detalle_perfil,
    eliminar_foto_perfil,
    guardar_foto_perfil,
    obtener_ruta_foto,
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
        "Actualiza el nombre del usuario autenticado. El correo no es editable "
        "porque se utiliza para la autenticacion de la cuenta. "
        "Requiere cabecera 'Authorization: Bearer <token>'."
    ),
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "El token es invalido, expiro o no fue enviado."
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
    usuario = actualizar_perfil(sesion=sesion, usuario=usuario, datos=datos)

    return PerfilRespuesta(
        mensaje="Perfil actualizado correctamente.",
        resultado=armar_detalle_perfil(sesion=sesion, usuario=usuario),
    )


@enrutador.get(
    "/foto",
    summary="Obtener mi foto de perfil (requiere token)",
    description="Retorna la imagen de la foto de perfil del usuario autenticado.",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "El usuario no tiene foto de perfil."},
    },
)
def obtener_mi_foto(usuario: Usuario = Depends(requiere_token)) -> FileResponse:
    ruta = obtener_ruta_foto(usuario)
    if ruta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El usuario no tiene foto de perfil.",
        )

    return FileResponse(
        path=str(ruta),
        media_type=TIPOS_MIME_POR_EXTENSION.get(ruta.suffix.lstrip(".").lower(), "image/jpeg"),
        headers={"Cache-Control": "no-store"},
    )


@enrutador.put(
    "/foto",
    response_model=PerfilRespuesta,
    status_code=status.HTTP_200_OK,
    summary="Subir o reemplazar mi foto de perfil (requiere token)",
    description=(
        "Recibe una imagen (JPG, PNG o WEBP, maximo 5 MB) en el campo 'archivo', la guarda "
        "en 'documentos/fotos_perfil' y registra su ruta en el usuario. "
        "Si ya existia una foto, se reemplaza."
    ),
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "description": "La imagen no tiene un formato valido o supera el tamano maximo."
        },
    },
)
def subir_mi_foto(
    archivo: UploadFile = File(..., description="Imagen JPG, PNG o WEBP (max 5 MB)"),
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> PerfilRespuesta:
    try:
        usuario = guardar_foto_perfil(sesion=sesion, usuario=usuario, archivo=archivo)
    except FotoPerfilInvalidaError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    return PerfilRespuesta(
        mensaje="Foto de perfil actualizada correctamente.",
        resultado=armar_detalle_perfil(sesion=sesion, usuario=usuario),
    )


@enrutador.delete(
    "/foto",
    response_model=PerfilRespuesta,
    status_code=status.HTTP_200_OK,
    summary="Eliminar mi foto de perfil (requiere token)",
)
def eliminar_mi_foto(
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> PerfilRespuesta:
    usuario = eliminar_foto_perfil(sesion=sesion, usuario=usuario)
    return PerfilRespuesta(
        mensaje="Foto de perfil eliminada correctamente.",
        resultado=armar_detalle_perfil(sesion=sesion, usuario=usuario),
    )

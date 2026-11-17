from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.seguridad import requiere_token
from app.database.conexion import obtener_sesion
from app.models.usuario.usuario import Usuario
from app.schemas.configuracion_traduccion import (
    GuardarConfiguracionTraduccionSolicitud,
    RespuestaConfiguracionTraduccion,
)
from app.services.configuracion_traduccion import (
    armar_detalle_configuracion,
    guardar_o_actualizar_configuracion,
    obtener_configuracion_usuario,
)


enrutador = APIRouter(
    prefix="/configuracion-traduccion",
    tags=["configuracion-traduccion"],
    dependencies=[Depends(requiere_token)],
)


@enrutador.post(
    "",
    response_model=RespuestaConfiguracionTraduccion,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(requiere_token)],
    summary="Guardar configuracion de traduccion (requiere token)",
    description=(
        "Guarda o actualiza la configuracion de traduccion del usuario autenticado. "
        "Si el usuario ya tiene configuracion la actualiza, de lo contrario la crea. "
        "Requiere cabecera 'Authorization: Bearer <token>'."
    ),
)
def guardar_configuracion(
    datos: GuardarConfiguracionTraduccionSolicitud,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaConfiguracionTraduccion:
    try:
        config = guardar_o_actualizar_configuracion(
            sesion=sesion,
            id_usuario=usuario.id,
            id_contexto=datos.id_contexto,
            id_tono=datos.id_tono,
            id_variante_regional=datos.id_variante_regional,
            explicar_expresiones=datos.explicar_expresiones,
            generar_alternativas=datos.generar_alternativas,
            idioma_destino=datos.idioma_destino,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    detalle = armar_detalle_configuracion(config=config, sesion=sesion)
    return RespuestaConfiguracionTraduccion(
        mensaje="Configuracion guardada correctamente.",
        resultado=detalle,
    )


@enrutador.get(
    "",
    response_model=RespuestaConfiguracionTraduccion,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(requiere_token)],
    summary="Obtener configuracion de traduccion (requiere token)",
    description=(
        "Retorna la configuracion de traduccion del usuario autenticado. "
        "Requiere cabecera 'Authorization: Bearer <token>'."
    ),
)
def obtener_configuracion(
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaConfiguracionTraduccion:
    config = obtener_configuracion_usuario(sesion=sesion, id_usuario=usuario.id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El usuario no tiene una configuracion de traduccion registrada.",
        )

    detalle = armar_detalle_configuracion(config=config, sesion=sesion)
    return RespuestaConfiguracionTraduccion(
        mensaje="Configuracion obtenida correctamente.",
        resultado=detalle,
    )


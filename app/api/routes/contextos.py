from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.seguridad import requiere_token
from app.database.conexion import obtener_sesion
from app.models.usuario.usuario import Usuario
from app.schemas.contexto import (
    GuardarContextoSolicitud,
    ListaContextosRespuesta,
    RespuestaContexto,
)
from app.services.contextos import guardar_nuevo_contexto, obtener_todos_contextos


enrutador = APIRouter(
    prefix="/contextos",
    tags=["contextos"],
    dependencies=[Depends(requiere_token)],
)


@enrutador.get(
    "",
    response_model=ListaContextosRespuesta,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(requiere_token)],
    summary="Listar contextos disponibles (requiere token)",
    description="Retorna la lista de contextos registrados en la tabla contexto. Requiere token Bearer de autenticacion.",
)
def listar_contextos(
    solo_activos: bool = Query(
        default=True,
        description="Filtrar solo contextos activos",
    ),
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> ListaContextosRespuesta:
    contextos = obtener_todos_contextos(
        sesion=sesion,
        solo_activos=solo_activos,
        id_usuario=usuario.id,
    )
    return ListaContextosRespuesta(
        mensaje="Contextos obtenidos correctamente.",
        resultado=contextos,
    )


@enrutador.post(
    "",
    response_model=RespuestaContexto,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(requiere_token)],
    summary="Guardar contexto (requiere token)",
    description="Crea y guarda un nuevo contexto personalizado en la tabla contexto. Requiere token Bearer de autenticacion.",
)
def guardar_contexto(
    datos: GuardarContextoSolicitud,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaContexto:
    try:
        nuevo_contexto = guardar_nuevo_contexto(
            sesion=sesion,
            nombre=datos.nombre,
            descripcion=datos.descripcion,
            id_usuario=usuario.id,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    return RespuestaContexto(
        mensaje="Contexto guardado correctamente.",
        resultado=nuevo_contexto,
    )

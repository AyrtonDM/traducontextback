from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.seguridad import requiere_token
from app.database.conexion import obtener_sesion
from app.models.usuario.usuario import Usuario
from app.schemas.tono import ListaTonosRespuesta
from app.services.tonos import obtener_todos_tonos


enrutador = APIRouter(
    prefix="/tonos",
    tags=["tonos"],
    dependencies=[Depends(requiere_token)],
)


@enrutador.get(
    "",
    response_model=ListaTonosRespuesta,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(requiere_token)],
    summary="Listar tonos disponibles (requiere token)",
    description="Retorna la lista de tonos registrados en la tabla tono. Requiere token Bearer de autenticacion.",
)
def listar_tonos(
    solo_activos: bool = Query(
        default=True,
        description="Filtrar solo tonos activos",
    ),
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> ListaTonosRespuesta:
    tonos = obtener_todos_tonos(sesion=sesion, solo_activos=solo_activos)
    return ListaTonosRespuesta(
        mensaje="Tonos obtenidos correctamente.",
        resultado=tonos,
    )


from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.seguridad import requiere_token
from app.database.conexion import obtener_sesion
from app.models.usuario.usuario import Usuario
from app.schemas.contexto import ListaContextosRespuesta
from app.services.contextos import obtener_todos_contextos


enrutador = APIRouter(prefix="/contextos", tags=["contextos"])


@enrutador.get(
    "",
    response_model=ListaContextosRespuesta,
    status_code=status.HTTP_200_OK,
    summary="Listar contextos disponibles",
    description="Retorna la lista de contextos registrados en la tabla contexto. Requiere token Bearer.",
)
def listar_contextos(
    solo_activos: bool = Query(
        default=True,
        description="Filtrar solo contextos activos",
    ),
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> ListaContextosRespuesta:
    contextos = obtener_todos_contextos(sesion=sesion, solo_activos=solo_activos)
    return ListaContextosRespuesta(
        mensaje="Contextos obtenidos correctamente.",
        resultado=contextos,
    )


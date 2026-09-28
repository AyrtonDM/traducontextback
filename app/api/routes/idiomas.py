from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.conexion import obtener_sesion
from app.schemas.idioma import ListaIdiomasRespuesta
from app.services.idiomas import obtener_todos_idiomas


enrutador = APIRouter(prefix="/idiomas", tags=["idiomas"])


@enrutador.get(
    "",
    response_model=ListaIdiomasRespuesta,
    status_code=status.HTTP_200_OK,
    summary="Listar todos los idiomas",
    description="Retorna la lista de todos los idiomas disponibles para traducción.",
)
def listar_idiomas(
    sesion: Session = Depends(obtener_sesion),
) -> ListaIdiomasRespuesta:
    idiomas = obtener_todos_idiomas(sesion)
    return ListaIdiomasRespuesta(
        mensaje="Idiomas obtenidos correctamente.",
        resultado=idiomas,
    )

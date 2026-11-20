from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.seguridad import requiere_token
from app.database.conexion import obtener_sesion
from app.schemas.entorno import EntornoItem, ListaEntornosRespuesta
from app.services.entornos import obtener_entornos_activos


enrutador = APIRouter(
    prefix="/entornos",
    tags=["entornos"],
    dependencies=[Depends(requiere_token)],
)


@enrutador.get(
    "",
    response_model=ListaEntornosRespuesta,
    status_code=status.HTTP_200_OK,
    summary="Listar entornos de conversacion (requiere token)",
    description=(
        "Retorna los entornos activos en los que puede desarrollarse una conversacion "
        "(reunion, conferencia, clase, entrevista, conversacion informal). Es un catalogo "
        "distinto de los contextos de dominio."
    ),
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "El token es invalido, expiro o no fue enviado."
        },
    },
)
def listar_entornos(
    sesion: Session = Depends(obtener_sesion),
) -> ListaEntornosRespuesta:
    entornos = obtener_entornos_activos(sesion)
    return ListaEntornosRespuesta(
        mensaje="Entornos obtenidos correctamente.",
        resultado=[EntornoItem.model_validate(e) for e in entornos],
    )

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.conexion import obtener_sesion
from app.schemas.idioma import ListaIdiomasRespuesta
from app.schemas.traduccion import (
    SolicitudTraduccion,
    RespuestaTraduccion,
)
from app.services.idiomas import obtener_todos_idiomas
from app.services.traduccion import traducir_texto


enrutador = APIRouter(
    prefix="/traducciones",
    tags=["traducciones"],
)


@enrutador.get(
    "/idiomas",
    response_model=ListaIdiomasRespuesta,
    status_code=status.HTTP_200_OK,
    summary="Listar idiomas disponibles para traducción",
)
def listar_idiomas_traduccion(
    sesion: Session = Depends(obtener_sesion),
) -> ListaIdiomasRespuesta:
    idiomas = obtener_todos_idiomas(sesion)
    return ListaIdiomasRespuesta(
        mensaje="Idiomas obtenidos correctamente.",
        resultado=idiomas,
    )


@enrutador.post(
    "",
    response_model=RespuestaTraduccion,
)
def traducir(
    solicitud: SolicitudTraduccion,
):

    try:

        resultado = traducir_texto(
            texto_origen=solicitud.texto_origen,
            idioma_origen=solicitud.idioma_origen,
            idioma_destino=solicitud.idioma_destino,
        )

        return resultado

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

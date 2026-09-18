from fastapi import APIRouter, HTTPException

from app.schemas.traduccion import (
    SolicitudTraduccion,
    RespuestaTraduccion,
)
from app.services.traduccion import traducir_texto


enrutador = APIRouter(
    prefix="/traducciones",
    tags=["traducciones"],
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
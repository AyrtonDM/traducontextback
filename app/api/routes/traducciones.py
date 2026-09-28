from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.seguridad import requiere_token
from app.database.conexion import obtener_sesion
from app.models.traduccion.contexto import Contexto
from app.models.usuario.usuario import Usuario
from app.schemas.idioma import ListaIdiomasRespuesta
from app.schemas.traduccion import (
    RespuestaTraduccion,
    SolicitudTraduccion,
    TraduccionResultado,
)
from app.services.idiomas import obtener_todos_idiomas
from app.services.motor_contextual import MotorContextual
from app.services.traduccion import traducir_texto


enrutador = APIRouter(
    prefix="/traducciones",
    tags=["traducciones"],
)


@enrutador.get(
    "/idiomas",
    response_model=ListaIdiomasRespuesta,
    status_code=status.HTTP_200_OK,
    summary="Listar idiomas disponibles para traduccion",
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
    status_code=status.HTTP_200_OK,
    summary="Traducir texto (requiere token)",
    description=(
        "Traduce un texto especificando idioma de destino, idioma de origen (opcional) "
        "e id de contexto (opcional). Si no se proporciona idioma de origen, se detecta "
        "automaticamente. Requiere cabecera 'Authorization: Bearer <token>'."
    ),
)
@enrutador.post(
    "/contextual",
    response_model=RespuestaTraduccion,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def traducir(
    solicitud: SolicitudTraduccion,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaTraduccion:

    nombre_contexto = None
    analisis_contextual = None

    if solicitud.id_contexto is not None:
        contexto_db = sesion.scalar(
            select(Contexto).where(
                Contexto.id_contexto == solicitud.id_contexto,
                Contexto.activo.is_(True),
            )
        )
        if not contexto_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contexto con id {solicitud.id_contexto} no encontrado o inactivo.",
            )
        nombre_contexto = contexto_db.nombre

        try:
            motor_contextual = MotorContextual()
            analisis = motor_contextual.analizar(
                contexto=contexto_db.descripcion or contexto_db.nombre,
                texto=solicitud.texto_origen,
            )
            if hasattr(analisis, "model_dump"):
                analisis_contextual = analisis.model_dump()
        except Exception:
            pass

    try:
        resultado = traducir_texto(
            texto_origen=solicitud.texto_origen,
            idioma_origen=solicitud.idioma_origen,
            idioma_destino=solicitud.idioma_destino,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    return RespuestaTraduccion(
        mensaje="Traduccion realizada correctamente.",
        resultado=TraduccionResultado(
            texto_origen=resultado["texto_origen"],
            idioma_origen=resultado["idioma_origen"],
            idioma_destino=resultado["idioma_destino"],
            traduccion=resultado["traduccion"],
            confianza_deteccion=resultado.get("confianza_deteccion"),
            id_contexto=solicitud.id_contexto,
            nombre_contexto=nombre_contexto,
            analisis_contextual=analisis_contextual,
        ),
    )

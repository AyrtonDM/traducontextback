from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.conexion import obtener_sesion
from app.models.usuario.usuario import Usuario
from app.schemas.traduccion import (
    TraduccionSolicitud,
    TraduccionRespuesta,
    ListaTraduccionesRespuesta,
    ListaIdiomasRespuesta,
    ListaContextosRespuesta,
    DeteccionIdiomaSolicitud,
    DeteccionIdiomaRespuesta,
    DeteccionIdiomaResultado,
)
from app.services.detector_idioma import detector_idioma
from app.services.traduccion import servicio_traduccion
from app.services.usuarios import obtener_usuario_actual


enrutador = APIRouter(prefix="/traducciones", tags=["traducciones"])


@enrutador.post(
    "/detectar-idioma",
    response_model=DeteccionIdiomaRespuesta,
    status_code=status.HTTP_200_OK,
    summary="Detectar automaticamente el idioma de un texto",
)
def detectar_idioma(
    datos: DeteccionIdiomaSolicitud,
) -> DeteccionIdiomaRespuesta:
    resultado = detector_idioma.detectar(datos.texto)
    return DeteccionIdiomaRespuesta(
        mensaje="Idioma detectado exitosamente.",
        resultado=DeteccionIdiomaResultado(
            codigo=resultado["codigo"],
            nombre=resultado["nombre"],
            confianza=resultado["confianza"],
        ),
    )


@enrutador.post(
    "/traducir",
    response_model=TraduccionRespuesta,
    status_code=status.HTTP_200_OK,
    summary="Realizar una traduccion contextual con IA",
)
def traducir(
    datos: TraduccionSolicitud,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    sesion: Session = Depends(obtener_sesion),
) -> TraduccionRespuesta:
    resultado = servicio_traduccion.ejecutar_traduccion(
        sesion=sesion,
        datos=datos,
        usuario=usuario_actual,
    )
    return TraduccionRespuesta(
        mensaje="Traduccion completada con exito.",
        resultado=resultado,
    )


@enrutador.get(
    "/recientes",
    response_model=ListaTraduccionesRespuesta,
    status_code=status.HTTP_200_OK,
    summary="Obtener traducciones recientes del usuario actual",
)
def obtener_recientes(
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    sesion: Session = Depends(obtener_sesion),
) -> ListaTraduccionesRespuesta:
    recientes = servicio_traduccion.obtener_recientes(
        sesion=sesion,
        usuario_id=usuario_actual.id,
    )
    return ListaTraduccionesRespuesta(
        mensaje="Traducciones recientes obtenidas correctamente.",
        resultado=recientes,
    )


@enrutador.get(
    "/idiomas",
    response_model=ListaIdiomasRespuesta,
    status_code=status.HTTP_200_OK,
    summary="Listar idiomas soportados",
)
def obtener_idiomas(
    sesion: Session = Depends(obtener_sesion),
) -> ListaIdiomasRespuesta:
    idiomas = servicio_traduccion.obtener_idiomas(sesion)
    return ListaIdiomasRespuesta(
        mensaje="Idiomas obtenidos correctamente.",
        resultado=idiomas,
    )


@enrutador.get(
    "/contextos",
    response_model=ListaContextosRespuesta,
    status_code=status.HTTP_200_OK,
    summary="Listar contextos configurados para el usuario actual",
)
def obtener_contextos(
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    sesion: Session = Depends(obtener_sesion),
) -> ListaContextosRespuesta:
    contextos = servicio_traduccion.obtener_contextos(
        sesion=sesion,
        usuario_id=usuario_actual.id,
    )
    return ListaContextosRespuesta(
        mensaje="Contextos obtenidos correctamente.",
        resultado=contextos,
    )

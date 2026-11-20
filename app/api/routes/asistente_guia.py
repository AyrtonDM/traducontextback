from fastapi import APIRouter, Depends, Query, status

from app.core.seguridad import requiere_token
from app.models.usuario.usuario import Usuario
from app.schemas.asistente_guia import (
    RespuestaBienvenidaGuia,
    RespuestaPreguntaGuia,
    SolicitudPreguntaGuia,
)
from app.services.asistente_guia import (
    asistente_guia_servicio,
    obtener_bienvenida_guia,
)

enrutador = APIRouter(
    prefix="/asistente-guia",
    tags=["asistente-guia"],
    dependencies=[Depends(requiere_token)],
)


@enrutador.get(
    "/bienvenida",
    response_model=RespuestaBienvenidaGuia,
    status_code=status.HTTP_200_OK,
    summary="Obtener saludo y preguntas sugeridas iniciales del chatbot guia (requiere token)",
    description=(
        "Retorna el mensaje de bienvenida y 3 preguntas rapidas adaptadas a la vista "
        "actual donde se encuentre el usuario al abrir la ventana flotante del asistente."
    ),
)
def bienvenida_asistente_guia(
    vista_actual: str | None = Query(
        default=None,
        description="Vista actual del usuario: 'traduccion', 'documentos', 'conversaciones', 'glosarios', 'historial', 'perfil'",
    ),
    usuario: Usuario = Depends(requiere_token),
) -> RespuestaBienvenidaGuia:
    detalle = obtener_bienvenida_guia(vista_actual=vista_actual)
    return RespuestaBienvenidaGuia(
        mensaje="Bienvenida del asistente guia obtenida correctamente.",
        resultado=detalle,
    )


@enrutador.post(
    "/preguntar",
    response_model=RespuestaPreguntaGuia,
    status_code=status.HTTP_200_OK,
    summary="Realizar una consulta al chatbot guia del sistema (requiere token)",
    description=(
        "Responde dudas exclusivamente relacionadas con el uso, herramientas y modulos "
        "del sistema TraduContext. Rechaza consultas ajenas a la plataforma."
    ),
)
def preguntar_asistente_guia(
    solicitud: SolicitudPreguntaGuia,
    usuario: Usuario = Depends(requiere_token),
) -> RespuestaPreguntaGuia:
    resultado = asistente_guia_servicio.responder(solicitud)
    return RespuestaPreguntaGuia(
        mensaje="Respuesta del asistente guia generada correctamente.",
        resultado=resultado,
    )

from pydantic import BaseModel, Field


class MensajeHistorialGuia(BaseModel):
    rol: str = Field(
        ...,
        description="Rol del emisor del mensaje en el chat: 'user' o 'assistant'",
    )
    contenido: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Texto del mensaje",
    )


class SolicitudPreguntaGuia(BaseModel):
    pregunta: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Consulta del usuario sobre el funcionamiento del sistema TraduContext",
    )
    vista_actual: str | None = Field(
        default=None,
        max_length=100,
        description=(
            "Modulo o pantalla donde se encuentra el usuario "
            "(ej: 'traduccion', 'documentos', 'conversaciones', 'glosarios', 'historial', 'perfil')"
        ),
    )
    historial: list[MensajeHistorialGuia] = Field(
        default_factory=list,
        description="Ultimos mensajes de la conversacion con el asistente para mantener el hilo",
    )


class ResultadoPreguntaGuia(BaseModel):
    respuesta: str = Field(
        ...,
        description="Respuesta clara y guiada del asistente sobre el sistema TraduContext",
    )
    sugerencias: list[str] = Field(
        default_factory=list,
        description="Lista de 3 preguntas sugeridas relacionadas para que el usuario pueda pulsar",
    )
    es_tema_sistema: bool = Field(
        default=True,
        description="True si la consulta pertenece al sistema TraduContext, False si fue rechazada por estar fuera de dominio",
    )


class RespuestaPreguntaGuia(BaseModel):
    mensaje: str
    resultado: ResultadoPreguntaGuia


class BienvenidaGuiaDetalle(BaseModel):
    saludo: str
    vista_actual: str
    sugerencias_iniciales: list[str]


class RespuestaBienvenidaGuia(BaseModel):
    mensaje: str
    resultado: BienvenidaGuiaDetalle

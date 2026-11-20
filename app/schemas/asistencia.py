from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


# explicacion: que significa lo dicho (expresiones, referencias, intencion)
# sugerencias: posibles respuestas a una intervencion
# como_decir: como expresar una idea propia segun la situacion (entorno de HU-24)
TipoAsistencia = Literal["explicacion", "sugerencias", "como_decir"]

LONGITUD_MAXIMA_IDEA = 1000


class SolicitudAsistencia(BaseModel):
    """
    Asistencia bajo demanda (HU-30). Para 'explicacion' y 'sugerencias', `id_intervencion` indica la
    intervencion de referencia (si se omite, la ultima traducida). Para 'como_decir' son obligatorios
    `texto` (la idea) y `id_participante` (quien la quiere decir, define el idioma de la respuesta).
    """

    tipo: TipoAsistencia
    id_intervencion: int | None = Field(
        default=None,
        description="Intervencion a explicar o responder (por defecto, la ultima traducida)",
    )
    id_participante: int | None = Field(
        default=None,
        description="Participante que quiere expresar la idea (obligatorio en 'como_decir')",
    )
    texto: str | None = Field(
        default=None,
        max_length=LONGITUD_MAXIMA_IDEA,
        description="Idea que se quiere expresar (obligatorio en 'como_decir')",
    )

    @field_validator("texto")
    @classmethod
    def limpiar_texto(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return valor.strip() or None

    @model_validator(mode="after")
    def validar_por_tipo(self):
        if self.tipo == "como_decir":
            if not self.texto:
                raise ValueError("Escribe la idea que quieres expresar.")
            if self.id_participante is None:
                raise ValueError("Indica que participante quiere expresar la idea.")
        return self


class ElementoAsistencia(BaseModel):
    """
    Un punto de la asistencia. En 'explicacion': `texto` es la expresion o referencia y `nota` su
    explicacion. En 'sugerencias' y 'como_decir': `texto` es la frase propuesta en el idioma de quien
    la dira, `traduccion` su traduccion al idioma del otro participante y `nota` cuando conviene usarla.
    """

    texto: str
    traduccion: str | None = None
    nota: str | None = None


class SalidaAsistenciaLLM(BaseModel):
    """Formato estructurado que devuelve el modelo de lenguaje."""

    resumen: str | None = None
    elementos: list[ElementoAsistencia] = Field(default_factory=list)


class ResultadoAsistencia(BaseModel):
    tipo: TipoAsistencia
    id_conversacion: int
    # Intervencion de referencia (null en 'como_decir')
    id_intervencion: int | None = None
    # Participante que diria las frases propuestas (null en 'explicacion')
    id_participante: int | None = None
    nombre_participante: str | None = None
    # Idioma en que se redacta la asistencia: el de quien escucha en 'explicacion' y el de quien
    # dira las frases en 'sugerencias' y 'como_decir'
    codigo_idioma: str | None = None
    nombre_idioma: str | None = None
    resumen: str | None = None
    elementos: list[ElementoAsistencia] = Field(default_factory=list)


class RespuestaAsistencia(BaseModel):
    mensaje: str
    resultado: ResultadoAsistencia

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, computed_field, field_validator


EstadoIntervencion = Literal["procesando", "traducida", "error"]

LONGITUD_MAXIMA_TEXTO_INTERVENCION = 2000


class CrearIntervencionSolicitud(BaseModel):
    id_participante: int = Field(..., description="Participante que habla (de esta conversacion)")
    texto: str = Field(
        ...,
        max_length=LONGITUD_MAXIMA_TEXTO_INTERVENCION,
        description="Texto de la intervencion en el idioma del participante que habla",
    )

    @field_validator("texto")
    @classmethod
    def validar_texto(cls, valor: str) -> str:
        valor_limpio = valor.strip()
        if not valor_limpio:
            raise ValueError("El texto de la intervencion no puede estar vacio.")
        return valor_limpio


class IntervencionDetalle(BaseModel):
    id_intervencion: int
    id_conversacion: int
    id_participante: int | None = None
    nombre_participante: str | None = None
    orden_participante: int | None = None
    orden: int
    texto_original: str
    texto_traducido: str | None = None
    id_idioma_origen: int
    id_idioma_destino: int
    codigo_idioma_origen: str | None = None
    codigo_idioma_destino: str | None = None
    nombre_idioma_origen: str | None = None
    nombre_idioma_destino: str | None = None
    estado: EstadoIntervencion
    mensaje_error: str | None = None
    fecha_creacion: datetime
    fecha_actualizacion: datetime | None = None

    @computed_field
    @property
    def id(self) -> int:
        return self.id_intervencion


class RespuestaIntervencion(BaseModel):
    mensaje: str
    resultado: IntervencionDetalle


class ListaIntervencionesRespuesta(BaseModel):
    mensaje: str
    resultado: list[IntervencionDetalle]

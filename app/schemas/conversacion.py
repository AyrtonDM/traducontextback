from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator


EstadoConversacion = Literal["activa", "pausada", "finalizada"]

LONGITUD_MAXIMA_DESCRIPCION_CONTEXTO = 1000


def _limpiar_texto_opcional(valor: str | None) -> str | None:
    if valor is None:
        return None
    valor_limpio = valor.strip()
    return valor_limpio or None


class IniciarConversacionSolicitud(BaseModel):
    id_idioma_origen: int = Field(..., description="ID del idioma de origen")
    id_idioma_destino: int = Field(..., description="ID del idioma de destino")
    id_contexto: int | None = Field(
        default=None,
        description="ID del contexto de dominio (opcional, como en HU-13)",
    )
    id_entorno: int = Field(..., description="ID del entorno de la conversacion (HU-24)")
    id_tono: int | None = Field(default=None, description="ID del tono (catalogo de HU-15, opcional)")
    id_glosario: int | None = Field(
        default=None,
        description="ID de un glosario del usuario para el par de idiomas de la conversacion (HU-32, opcional)",
    )
    descripcion_contexto: str | None = Field(
        default=None,
        max_length=LONGITUD_MAXIMA_DESCRIPCION_CONTEXTO,
        description="Situacion, audiencia o terminologia de la conversacion (HU-29, opcional)",
    )
    mantener_contexto: bool = Field(default=True, description="Mantener contexto de la conversacion")
    asistencia_conversacional: bool = Field(default=False, description="Asistencia conversacional")

    @field_validator("descripcion_contexto")
    @classmethod
    def limpiar_descripcion(cls, valor: str | None) -> str | None:
        return _limpiar_texto_opcional(valor)

    @model_validator(mode="after")
    def validar_idiomas(self):
        if self.id_idioma_origen == self.id_idioma_destino:
            raise ValueError("El idioma de origen y el de destino deben ser distintos.")
        return self


class ActualizarConversacionSolicitud(BaseModel):
    """
    Configuracion modificable de una sesion no finalizada. Solo se cambian los campos enviados;
    id_contexto, id_tono, id_glosario y descripcion_contexto admiten null para quitarlos. Los idiomas no cambian.
    """

    id_entorno: int | None = Field(default=None, description="Nuevo entorno de la conversacion")
    id_contexto: int | None = Field(default=None, description="Nuevo contexto de dominio (null lo quita)")
    id_tono: int | None = Field(default=None, description="Nuevo tono (null lo quita)")
    id_glosario: int | None = Field(default=None, description="Nuevo glosario (HU-32, null lo quita)")
    descripcion_contexto: str | None = Field(
        default=None,
        max_length=LONGITUD_MAXIMA_DESCRIPCION_CONTEXTO,
        description="Nueva descripcion personalizada del contexto (null la quita)",
    )
    mantener_contexto: bool | None = None
    asistencia_conversacional: bool | None = None

    @field_validator("descripcion_contexto")
    @classmethod
    def limpiar_descripcion(cls, valor: str | None) -> str | None:
        return _limpiar_texto_opcional(valor)

    @model_validator(mode="after")
    def validar_campos(self):
        if not self.model_fields_set:
            raise ValueError("Debe enviar al menos un campo para actualizar.")
        for campo in ("id_entorno", "mantener_contexto", "asistencia_conversacional"):
            if campo in self.model_fields_set and getattr(self, campo) is None:
                raise ValueError(f"El campo {campo} no puede ser nulo.")
        return self


class ActualizarParticipanteSolicitud(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100, description="Nombre o etiqueta del participante")

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, valor: str) -> str:
        valor_limpio = valor.strip()
        if not valor_limpio:
            raise ValueError("El nombre del participante no puede estar vacio.")
        return valor_limpio


class ParticipanteDetalle(BaseModel):
    id_participante: int
    id_conversacion: int
    nombre: str
    orden: int
    id_idioma: int
    codigo_idioma: str | None = None
    nombre_idioma: str | None = None


class ConversacionDetalle(BaseModel):
    id_conversacion: int
    estado: EstadoConversacion
    id_usuario: int
    id_idioma_origen: int
    id_idioma_destino: int
    codigo_idioma_origen: str | None = None
    codigo_idioma_destino: str | None = None
    nombre_idioma_origen: str | None = None
    nombre_idioma_destino: str | None = None
    id_contexto: int | None = None
    nombre_contexto: str | None = None
    id_entorno: int
    nombre_entorno: str | None = None
    id_tono: int | None = None
    nombre_tono: str | None = None
    id_glosario: int | None = None
    nombre_glosario: str | None = None
    # Sentido en el que se aplica el glosario, por ejemplo "ES → EN"
    par_idiomas_glosario: str | None = None
    descripcion_contexto: str | None = None
    mantener_contexto: bool = True
    asistencia_conversacional: bool = False
    participantes: list[ParticipanteDetalle] = []
    fecha_inicio: datetime
    fecha_actualizacion: datetime | None = None
    fecha_fin: datetime | None = None

    @computed_field
    @property
    def id(self) -> int:
        return self.id_conversacion


class RespuestaConversacion(BaseModel):
    mensaje: str
    resultado: ConversacionDetalle


class ListaConversacionesRespuesta(BaseModel):
    mensaje: str
    resultado: list[ConversacionDetalle]


class RespuestaParticipante(BaseModel):
    mensaje: str
    resultado: ParticipanteDetalle


class ListaParticipantesRespuesta(BaseModel):
    mensaje: str
    resultado: list[ParticipanteDetalle]

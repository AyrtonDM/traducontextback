from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator

from app.schemas.integracion import Plataforma


EstadoSesionExterna = Literal["configurada", "activa", "pausada", "finalizada"]
EstadoIntervencionExterna = Literal["procesando", "traducida", "error"]

LONGITUD_MAXIMA_DESCRIPCION = 1000


def _limpiar(valor: str | None) -> str | None:
    if valor is None:
        return None
    return valor.strip() or None


class CrearSesionExternaSolicitud(BaseModel):
    """Configuracion de la sesion (HU-36). El cliente la precarga con las preferencias (HU-33)."""

    plataforma: Plataforma
    enlace_reunion: str = Field(..., min_length=1, max_length=2000, description="Enlace o identificador")
    id_idioma_origen: int
    id_idioma_destino: int
    id_entorno: int
    id_contexto: int | None = None
    id_tono: int | None = None
    id_glosario: int | None = None
    descripcion_contexto: str | None = Field(default=None, max_length=LONGITUD_MAXIMA_DESCRIPCION)

    @field_validator("descripcion_contexto")
    @classmethod
    def limpiar_descripcion(cls, valor: str | None) -> str | None:
        return _limpiar(valor)

    @model_validator(mode="after")
    def validar_idiomas(self):
        if self.id_idioma_origen == self.id_idioma_destino:
            raise ValueError("Los idiomas de los participantes deben ser distintos.")
        return self


class ActualizarSesionExternaSolicitud(BaseModel):
    """
    Cambios de configuracion antes o durante la reunion (HU-36); se aplican a las intervenciones
    siguientes. Los idiomas y el enlace solo se cambian antes de iniciar el servicio.
    id_contexto, id_tono, id_glosario y descripcion_contexto admiten null para quitarlos.
    """

    enlace_reunion: str | None = Field(default=None, min_length=1, max_length=2000)
    id_idioma_origen: int | None = None
    id_idioma_destino: int | None = None
    id_entorno: int | None = None
    id_contexto: int | None = None
    id_tono: int | None = None
    id_glosario: int | None = None
    descripcion_contexto: str | None = Field(default=None, max_length=LONGITUD_MAXIMA_DESCRIPCION)

    @field_validator("descripcion_contexto")
    @classmethod
    def limpiar_descripcion(cls, valor: str | None) -> str | None:
        return _limpiar(valor)

    @model_validator(mode="after")
    def validar(self):
        if not self.model_fields_set:
            raise ValueError("Debe enviar al menos un campo para actualizar.")
        for campo in ("enlace_reunion", "id_idioma_origen", "id_idioma_destino", "id_entorno"):
            if campo in self.model_fields_set and getattr(self, campo) is None:
                raise ValueError(f"El campo {campo} no puede ser nulo.")
        return self


class ParticipanteExternoDetalle(BaseModel):
    id_participante: int
    id_sesion_externa: int
    nombre: str
    orden: int
    generico: bool
    desde_plataforma: bool


class SesionExternaDetalle(BaseModel):
    id_sesion_externa: int
    plataforma: Plataforma
    nombre_plataforma: str
    enlace_reunion: str
    referencia_reunion: str
    url_reunion: str
    estado: EstadoSesionExterna
    id_idioma_origen: int
    id_idioma_destino: int
    codigo_idioma_origen: str | None = None
    codigo_idioma_destino: str | None = None
    nombre_idioma_origen: str | None = None
    nombre_idioma_destino: str | None = None
    id_entorno: int
    nombre_entorno: str | None = None
    id_contexto: int | None = None
    nombre_contexto: str | None = None
    id_tono: int | None = None
    nombre_tono: str | None = None
    id_glosario: int | None = None
    nombre_glosario: str | None = None
    par_idiomas_glosario: str | None = None
    descripcion_contexto: str | None = None
    participantes: list[ParticipanteExternoDetalle] = []
    total_intervenciones: int = 0
    fecha_creacion: datetime
    fecha_inicio: datetime | None = None
    fecha_actualizacion: datetime | None = None
    fecha_fin: datetime | None = None

    @computed_field
    @property
    def id(self) -> int:
        return self.id_sesion_externa


class SesionExternaRespuesta(BaseModel):
    mensaje: str
    resultado: SesionExternaDetalle


class ListaSesionesExternasRespuesta(BaseModel):
    mensaje: str
    resultado: list[SesionExternaDetalle]


class CrearParticipanteExternoSolicitud(BaseModel):
    nombre: str | None = Field(default=None, max_length=100, description="Si se omite: 'Participante N'")

    @field_validator("nombre")
    @classmethod
    def limpiar_nombre(cls, valor: str | None) -> str | None:
        return _limpiar(valor)


class RenombrarParticipanteExternoSolicitud(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, valor: str) -> str:
        limpio = valor.strip()
        if not limpio:
            raise ValueError("El nombre del participante no puede estar vacio.")
        return limpio


class ParticipanteExternoRespuesta(BaseModel):
    mensaje: str
    resultado: ParticipanteExternoDetalle


class ListaParticipantesExternosRespuesta(BaseModel):
    mensaje: str
    resultado: list[ParticipanteExternoDetalle]


class SincronizacionParticipantesResultado(BaseModel):
    # False si la plataforma no informo participantes (se siguen usando etiquetas genericas)
    disponible: bool
    agregados: int
    aviso: str | None = None
    participantes: list[ParticipanteExternoDetalle]


class SincronizacionParticipantesRespuesta(BaseModel):
    mensaje: str
    resultado: SincronizacionParticipantesResultado


class IntervencionExternaDetalle(BaseModel):
    id_intervencion: int
    id_sesion_externa: int
    id_participante: int | None = None
    # null = no se pudo determinar el hablante (no se asigna una identidad incorrecta)
    nombre_participante: str | None = None
    orden: int
    texto_original: str
    texto_traducido: str | None = None
    codigo_idioma_origen: str | None = None
    codigo_idioma_destino: str | None = None
    nombre_idioma_origen: str | None = None
    nombre_idioma_destino: str | None = None
    estado: EstadoIntervencionExterna
    mensaje_error: str | None = None
    fecha_creacion: datetime
    fecha_actualizacion: datetime | None = None

    @computed_field
    @property
    def id(self) -> int:
        return self.id_intervencion


class IntervencionExternaRespuesta(BaseModel):
    mensaje: str
    # null si el fragmento de audio no tenia voz
    resultado: IntervencionExternaDetalle | None = None


class ListaIntervencionesExternasRespuesta(BaseModel):
    mensaje: str
    resultado: list[IntervencionExternaDetalle]


class AsignarParticipanteSolicitud(BaseModel):
    id_participante: int | None = Field(..., description="Participante que hablo; null = sin identificar")

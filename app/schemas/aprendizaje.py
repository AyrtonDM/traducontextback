from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator


TipoCorreccion = Literal["correccion", "alternativa"]

LONGITUD_MAXIMA_TEXTO = 5000


class EstadoAprendizaje(BaseModel):
    activo: bool
    total_correcciones: int


class RespuestaEstadoAprendizaje(BaseModel):
    mensaje: str
    resultado: EstadoAprendizaje


class CambiarAprendizajeSolicitud(BaseModel):
    activo: bool = Field(..., description="Activa o desactiva el aprendizaje de preferencias")


class RegistrarCorreccionSolicitud(BaseModel):
    """
    Correccion manual del resultado ('correccion') o alternativa elegida ('alternativa', HU-18).
    Los idiomas se indican por codigo (como en /traducciones).
    """

    tipo: TipoCorreccion = "correccion"
    texto_original: str = Field(..., max_length=LONGITUD_MAXIMA_TEXTO)
    traduccion_generada: str = Field(..., max_length=LONGITUD_MAXIMA_TEXTO)
    traduccion_corregida: str = Field(..., max_length=LONGITUD_MAXIMA_TEXTO)
    idioma_origen: str = Field(..., min_length=2, max_length=10)
    idioma_destino: str = Field(..., min_length=2, max_length=10)

    @field_validator("texto_original", "traduccion_generada", "traduccion_corregida")
    @classmethod
    def validar_texto(cls, valor: str) -> str:
        valor_limpio = valor.strip()
        if not valor_limpio:
            raise ValueError("Los textos de la correccion no pueden estar vacios.")
        return valor_limpio

    @field_validator("idioma_origen", "idioma_destino")
    @classmethod
    def normalizar_idioma(cls, valor: str) -> str:
        return valor.strip().lower()

    @model_validator(mode="after")
    def validar_cambio(self):
        if self.idioma_origen == self.idioma_destino:
            raise ValueError("El idioma de origen y el de destino deben ser distintos.")
        if self.traduccion_corregida == self.traduccion_generada:
            raise ValueError("La correccion es igual a la traduccion generada; no hay nada que aprender.")
        return self


class CorreccionDetalle(BaseModel):
    id_correccion: int
    tipo: TipoCorreccion
    texto_original: str
    traduccion_generada: str
    traduccion_corregida: str
    codigo_idioma_origen: str | None = None
    codigo_idioma_destino: str | None = None
    nombre_idioma_origen: str | None = None
    nombre_idioma_destino: str | None = None
    fecha_creacion: datetime
    fecha_actualizacion: datetime | None = None

    @computed_field
    @property
    def id(self) -> int:
        return self.id_correccion


class RespuestaCorreccion(BaseModel):
    mensaje: str
    # null si el aprendizaje esta desactivado (no se registra nada)
    resultado: CorreccionDetalle | None = None


class ListaCorreccionesRespuesta(BaseModel):
    mensaje: str
    resultado: list[CorreccionDetalle]


class EliminarCorreccionesResultado(BaseModel):
    eliminadas: int


class RespuestaEliminarCorrecciones(BaseModel):
    mensaje: str
    resultado: EliminarCorreccionesResultado

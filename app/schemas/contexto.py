from typing import Literal
from pydantic import BaseModel, Field, computed_field, field_validator


class TerminoContextual(BaseModel):
    texto: str
    significado: str
    accion: Literal[
        "conservar",
        "traducir"
    ]


class AnalisisContextual(BaseModel):
    dominio: str
    terminos_relevantes: list[TerminoContextual]


class GuardarContextoSolicitud(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100, description="Nombre del contexto")
    descripcion: str | None = Field(default=None, description="Descripcion del contexto")

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, valor: str) -> str:
        valor_limpio = valor.strip()
        if not valor_limpio:
            raise ValueError("El nombre del contexto no puede estar vacio.")
        return valor_limpio


class ContextoDetalle(BaseModel):
    model_config = {"from_attributes": True}

    id_contexto: int
    nombre: str
    descripcion: str | None = None
    personalizado: bool = False
    activo: bool = True
    id_usuario: int | None = None

    @computed_field
    @property
    def id(self) -> int:
        return self.id_contexto


class RespuestaContexto(BaseModel):
    mensaje: str
    resultado: ContextoDetalle


class ListaContextosRespuesta(BaseModel):
    mensaje: str
    resultado: list[ContextoDetalle]

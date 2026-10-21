from typing import Literal
from pydantic import BaseModel, computed_field


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


class ContextoDetalle(BaseModel):
    model_config = {"from_attributes": True}

    id_contexto: int
    nombre: str
    descripcion: str | None = None
    personalizado: bool = False
    activo: bool = True


class ListaContextosRespuesta(BaseModel):
    mensaje: str
    resultado: list[ContextoDetalle]

from pydantic import BaseModel
from typing import Literal


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
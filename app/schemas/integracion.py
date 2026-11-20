from datetime import datetime
from typing import Literal

from pydantic import BaseModel


Plataforma = Literal["google_meet", "zoom"]
EstadoConexion = Literal["vinculada", "no_vinculada", "expirada"]


class PermisoPlataforma(BaseModel):
    alcance: str
    descripcion: str


class PlataformaDetalle(BaseModel):
    """Plataforma compatible y estado de la conexion del usuario (HU-35). Nunca incluye tokens."""

    plataforma: Plataforma
    nombre: str
    # False si el servidor no tiene las credenciales OAuth de la plataforma
    configurada: bool
    estado: EstadoConexion
    cuenta_externa: str | None = None
    fecha_vinculacion: datetime | None = None
    permisos: list[PermisoPlataforma]


class ListaPlataformasRespuesta(BaseModel):
    mensaje: str
    resultado: list[PlataformaDetalle]


class PlataformaRespuesta(BaseModel):
    mensaje: str
    resultado: PlataformaDetalle


class AutorizacionResultado(BaseModel):
    plataforma: Plataforma
    # Pantalla oficial de autorizacion de la plataforma; el navegador debe abrirla
    url_autorizacion: str
    permisos: list[PermisoPlataforma]


class AutorizacionRespuesta(BaseModel):
    mensaje: str
    resultado: AutorizacionResultado

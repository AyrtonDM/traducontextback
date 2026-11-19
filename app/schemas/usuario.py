import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RegistroUsuarioSolicitud(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    correo: str = Field(max_length=255)
    contrasena: str = Field(min_length=8, max_length=72)

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, valor: str) -> str:
        valor = " ".join(valor.strip().split())

        if not valor:
            raise ValueError("El nombre es obligatorio.")

        return valor

    @field_validator("correo")
    @classmethod
    def validar_correo(cls, valor: str) -> str:
        valor = valor.strip().lower()

        if not PATRON_CORREO.fullmatch(valor):
            raise ValueError("El correo no tiene un formato valido.")

        return valor

    @field_validator("contrasena")
    @classmethod
    def validar_contrasena(cls, valor: str) -> str:
        if not any(caracter.isalpha() for caracter in valor):
            raise ValueError("La contrasena debe incluir al menos una letra.")

        if not any(caracter.isdigit() for caracter in valor):
            raise ValueError("La contrasena debe incluir al menos un numero.")

        return valor


class RegistroUsuarioResultado(BaseModel):
    id: int
    nombre: str
    correo: str
    estado: str


class RegistroUsuarioRespuesta(BaseModel):
    mensaje: str
    resultado: RegistroUsuarioResultado


class VerificarCodigoSolicitud(BaseModel):
    correo: str = Field(max_length=255)
    codigo: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")

    @field_validator("correo")
    @classmethod
    def validar_correo(cls, valor: str) -> str:
        valor = valor.strip().lower()

        if not PATRON_CORREO.fullmatch(valor):
            raise ValueError("El correo no tiene un formato valido.")

        return valor


class VerificarCodigoResultado(BaseModel):
    id: int
    correo: str
    estado: str


class VerificarCodigoRespuesta(BaseModel):
    mensaje: str
    resultado: VerificarCodigoResultado


class ReenviarCodigoSolicitud(BaseModel):
    correo: str = Field(max_length=255)

    @field_validator("correo")
    @classmethod
    def validar_correo(cls, valor: str) -> str:
        valor = valor.strip().lower()

        if not PATRON_CORREO.fullmatch(valor):
            raise ValueError("El correo no tiene un formato valido.")

        return valor


class ReenviarCodigoResultado(BaseModel):
    correo: str
    estado: str


class ReenviarCodigoRespuesta(BaseModel):
    mensaje: str
    resultado: ReenviarCodigoResultado


class RolDetalle(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    nombre: str


class UsuarioDetalle(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    nombre: str
    correo: str
    estado: str
    rol: RolDetalle


class UsuarioPerfilDetalle(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    nombre: str
    correo: str
    estado: str
    rol: RolDetalle
    permisos: list[str]


class UsuarioDetalleRespuesta(BaseModel):
    mensaje: str
    resultado: UsuarioPerfilDetalle




# ---------------------------------------------------------------------------
# Administracion de usuarios (HU-05)
# ---------------------------------------------------------------------------


class UsuarioAdminResumen(BaseModel):
    """Fila del listado de administracion."""

    model_config = {"from_attributes": True}
    id: int
    nombre: str
    correo: str
    estado: str
    fecha_creacion: datetime
    rol: RolDetalle


class UsuarioAdminDetalle(UsuarioAdminResumen):
    """Detalle de una cuenta para el administrador."""

    fecha_actualizacion: datetime | None = None
    foto_perfil: str | None = None
    ultimo_acceso: datetime | None = None
    sesiones_activas: int = 0
    total_traducciones: int = 0
    total_documentos: int = 0
    total_conversaciones: int = 0
    total_glosarios: int = 0


class ListaUsuariosPaginada(BaseModel):
    elementos: list[UsuarioAdminResumen]
    total: int
    pagina: int
    tamano_pagina: int
    total_paginas: int


class ListaUsuariosRespuesta(BaseModel):
    mensaje: str
    resultado: ListaUsuariosPaginada


class UsuarioAdminRespuesta(BaseModel):
    mensaje: str
    resultado: UsuarioAdminDetalle


class CambiarRolUsuarioSolicitud(BaseModel):
    id_rol: int = Field(..., gt=0, description="ID del nuevo rol")


class ListaRolesRespuesta(BaseModel):
    mensaje: str
    resultado: list[RolDetalle]

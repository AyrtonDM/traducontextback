import re

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
    permisos: list[str]


class UsuarioDetalleRespuesta(BaseModel):
    mensaje: str
    resultado: UsuarioDetalle


class ListaUsuariosRespuesta(BaseModel):
    mensaje: str
    resultado: list[UsuarioDetalle]


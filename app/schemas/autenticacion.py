from pydantic import BaseModel, Field, field_validator
import re

PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class LoginSolicitud(BaseModel):
    correo: str = Field(max_length=255)
    contrasena: str = Field(min_length=1)

    @field_validator("correo")
    @classmethod
    def validar_correo(cls, valor: str) -> str:
        valor = valor.strip().lower()
        if not PATRON_CORREO.fullmatch(valor):
            raise ValueError("El correo no tiene un formato valido.")
        return valor


class LoginResultado(BaseModel):
    token: str


class LoginRespuesta(BaseModel):
    mensaje: str
    resultado: list[LoginResultado]


class LogoutRespuesta(BaseModel):
    mensaje: str
    resultado: None = None


class SolicitarRecuperacionSolicitud(BaseModel):
    correo: str = Field(max_length=255)

    @field_validator("correo")
    @classmethod
    def validar_correo(cls, valor: str) -> str:
        valor = valor.strip().lower()
        if not PATRON_CORREO.fullmatch(valor):
            raise ValueError("El correo no tiene un formato valido.")
        return valor


class SolicitarRecuperacionRespuesta(BaseModel):
    mensaje: str
    resultado: None = None


class ValidarCodigoRecuperacionSolicitud(BaseModel):
    correo: str = Field(max_length=255)
    codigo: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")

    @field_validator("correo")
    @classmethod
    def validar_correo(cls, valor: str) -> str:
        valor = valor.strip().lower()
        if not PATRON_CORREO.fullmatch(valor):
            raise ValueError("El correo no tiene un formato valido.")
        return valor


class ValidarCodigoRecuperacionRespuesta(BaseModel):
    mensaje: str
    resultado: None = None


class RestablecerContrasenaSolicitud(BaseModel):
    correo: str = Field(max_length=255)
    codigo: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")
    nueva_contrasena: str = Field(min_length=8, max_length=72)

    @field_validator("correo")
    @classmethod
    def validar_correo(cls, valor: str) -> str:
        valor = valor.strip().lower()
        if not PATRON_CORREO.fullmatch(valor):
            raise ValueError("El correo no tiene un formato valido.")
        return valor

    @field_validator("nueva_contrasena")
    @classmethod
    def validar_nueva_contrasena(cls, valor: str) -> str:
        if not any(caracter.isalpha() for caracter in valor):
            raise ValueError("La contrasena debe incluir al menos una letra.")
        if not any(caracter.isdigit() for caracter in valor):
            raise ValueError("La contrasena debe incluir al menos un numero.")
        return valor


class RestablecerContrasenaRespuesta(BaseModel):
    mensaje: str
    resultado: None = None

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

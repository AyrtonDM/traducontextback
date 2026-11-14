from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.configuracion_traduccion import ConfiguracionTraduccionDetalle
from app.schemas.usuario import PATRON_CORREO, RolDetalle


class PerfilDetalle(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    nombre: str
    correo: str
    estado: str
    rol: RolDetalle
    fecha_creacion: datetime
    fecha_actualizacion: datetime | None = None
    configuracion_traduccion: ConfiguracionTraduccionDetalle | None = None


class PerfilRespuesta(BaseModel):
    mensaje: str
    resultado: PerfilDetalle


class ActualizarPerfilSolicitud(BaseModel):
    nombre: str | None = Field(default=None, max_length=100, description="Nombre completo")
    correo: str | None = Field(default=None, max_length=255, description="Correo electronico")

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, valor: str | None) -> str | None:
        if valor is None:
            return None

        valor = " ".join(valor.strip().split())

        if len(valor) < 2:
            raise ValueError("El nombre debe tener al menos 2 caracteres.")

        return valor

    @field_validator("correo")
    @classmethod
    def validar_correo(cls, valor: str | None) -> str | None:
        if valor is None:
            return None

        valor = valor.strip().lower()

        if not PATRON_CORREO.fullmatch(valor):
            raise ValueError("El correo no tiene un formato valido.")

        return valor

    @model_validator(mode="after")
    def validar_algun_campo(self) -> "ActualizarPerfilSolicitud":
        if self.nombre is None and self.correo is None:
            raise ValueError(
                "Debe enviar al menos un dato para actualizar (nombre o correo)."
            )
        return self


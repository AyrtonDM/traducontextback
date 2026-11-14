from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.configuracion_traduccion import ConfiguracionTraduccionDetalle
from app.schemas.usuario import RolDetalle


class PerfilDetalle(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    nombre: str
    correo: str
    estado: str
    rol: RolDetalle
    fecha_creacion: datetime
    fecha_actualizacion: datetime | None = None
    url_foto_perfil: str | None = None
    configuracion_traduccion: ConfiguracionTraduccionDetalle | None = None


class PerfilRespuesta(BaseModel):
    mensaje: str
    resultado: PerfilDetalle


class ActualizarPerfilSolicitud(BaseModel):
    # El correo no es editable: se usa para la autenticacion de la cuenta
    nombre: str = Field(max_length=100, description="Nombre completo")

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, valor: str) -> str:
        valor = " ".join(valor.strip().split())

        if len(valor) < 2:
            raise ValueError("El nombre debe tener al menos 2 caracteres.")

        return valor

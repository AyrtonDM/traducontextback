from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Dispositivos push
# ---------------------------------------------------------------------------


class RegistrarDispositivoSolicitud(BaseModel):
    token_fcm: str = Field(
        ...,
        min_length=1,
        max_length=512,
        description="Token de registro de Firebase Cloud Messaging del dispositivo",
    )
    plataforma: Literal["android", "ios", "web"] = Field(
        ..., description="Plataforma del dispositivo: android, ios o web (navegador)"
    )

    @field_validator("token_fcm")
    @classmethod
    def validar_token(cls, valor: str) -> str:
        valor_limpio = valor.strip()
        if not valor_limpio:
            raise ValueError("El token de FCM no puede estar vacio.")
        return valor_limpio


class DispositivoDetalle(BaseModel):
    """El token no se devuelve: el cliente ya lo conoce."""

    model_config = {"from_attributes": True}

    id_dispositivo: int
    plataforma: str
    activo: bool
    fecha_registro: datetime
    fecha_ultimo_uso: datetime | None = None


class RespuestaDispositivo(BaseModel):
    mensaje: str
    resultado: DispositivoDetalle


class RespuestaEliminarDispositivo(BaseModel):
    mensaje: str
    resultado: None = None


# ---------------------------------------------------------------------------
# Notificaciones
# ---------------------------------------------------------------------------


class NotificacionDetalle(BaseModel):
    model_config = {"from_attributes": True}

    id_notificacion: int
    tipo: str
    titulo: str
    cuerpo: str
    datos: dict[str, Any] | None = None
    leida: bool
    fecha_creacion: datetime
    fecha_lectura: datetime | None = None


class ListaNotificacionesPaginada(BaseModel):
    elementos: list[NotificacionDetalle]
    total: int
    no_leidas: int
    pagina: int
    tamano_pagina: int
    total_paginas: int


class ListaNotificacionesRespuesta(BaseModel):
    mensaje: str
    resultado: ListaNotificacionesPaginada


class RespuestaNotificacion(BaseModel):
    mensaje: str
    resultado: NotificacionDetalle


class ResultadoMarcarLeidas(BaseModel):
    actualizadas: int


class RespuestaMarcarLeidas(BaseModel):
    mensaje: str
    resultado: ResultadoMarcarLeidas

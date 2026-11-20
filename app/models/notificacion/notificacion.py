from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, false, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


TIPO_DOCUMENTO_LISTO = "DOCUMENTO_LISTO"
TIPO_DOCUMENTO_ERROR = "DOCUMENTO_ERROR"
TIPO_SISTEMA = "SISTEMA"
# Chats entre usuarios: una entrada por chat en la bandeja (se actualiza con cada mensaje)
TIPO_MENSAJE_CHAT = "MENSAJE_CHAT"
TIPOS_NOTIFICACION = (TIPO_DOCUMENTO_LISTO, TIPO_DOCUMENTO_ERROR, TIPO_SISTEMA, TIPO_MENSAJE_CHAT)


class Notificacion(Base):
    """
    Notificacion dirigida a un usuario. Se guarda siempre en la base de datos (bandeja de la app)
    y, si hay credenciales de Firebase, tambien se envia por push.
    `datos` solo lleva identificadores (p. ej. id_traduccion_documento), nunca texto traducido.
    """

    __tablename__ = "notificacion"
    __table_args__ = (
        CheckConstraint(
            "tipo IN ('DOCUMENTO_LISTO', 'DOCUMENTO_ERROR', 'SISTEMA', 'MENSAJE_CHAT')",
            name="ck_notificacion_tipo",
        ),
        Index("ix_notificacion_usuario_leida_fecha", "id_usuario", "leida", "fecha_creacion"),
    )

    id_notificacion: Mapped[int] = mapped_column(primary_key=True, index=True)
    id_usuario: Mapped[int] = mapped_column(
        ForeignKey("usuario.id", ondelete="CASCADE"),
        nullable=False,
    )
    tipo: Mapped[str] = mapped_column(String(40), nullable=False)
    titulo: Mapped[str] = mapped_column(String(150), nullable=False)
    cuerpo: Mapped[str] = mapped_column(String(500), nullable=False)
    datos: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    leida: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=false(),
        nullable=False,
    )
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    fecha_lectura: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    usuario = relationship("Usuario", back_populates="notificaciones")

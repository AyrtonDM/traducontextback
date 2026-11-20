from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index, String, false, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


ESTADO_MENSAJE_PENDIENTE = "pendiente"
ESTADO_MENSAJE_PROCESADO = "procesado"
ESTADO_MENSAJE_ERROR = "error"

LONGITUD_MAXIMA_MENSAJE = 2000


class MensajeChat(Base):
    """
    Mensaje tal como lo escribio el remitente. El idioma se detecta en segundo plano
    ('pendiente' -> 'procesado' o 'error'); si el texto es corto o la deteccion no es fiable se
    usa el idioma de lectura del remitente en ese chat (`idioma_por_respaldo`).
    """

    __tablename__ = "mensaje_chat"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('pendiente', 'procesado', 'error')",
            name="ck_mensaje_chat_estado",
        ),
        Index("ix_mensaje_chat_chat_mensaje", "id_chat", "id_mensaje"),
        Index("ix_mensaje_chat_remitente_fecha", "id_remitente", "fecha_envio"),
    )

    id_mensaje: Mapped[int] = mapped_column(primary_key=True, index=True)
    id_chat: Mapped[int] = mapped_column(
        ForeignKey("chat.id_chat", ondelete="CASCADE"),
        nullable=False,
    )
    id_remitente: Mapped[int] = mapped_column(
        ForeignKey("usuario.id", ondelete="CASCADE"),
        nullable=False,
    )
    texto_original: Mapped[str] = mapped_column(String(LONGITUD_MAXIMA_MENSAJE), nullable=False)
    id_idioma_detectado: Mapped[int | None] = mapped_column(
        ForeignKey("idioma.id_idioma", ondelete="SET NULL"),
        nullable=True,
    )
    confianza_deteccion: Mapped[float | None] = mapped_column(Float, nullable=True)
    idioma_por_respaldo: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=false(),
        nullable=False,
    )
    estado: Mapped[str] = mapped_column(
        String(20),
        default=ESTADO_MENSAJE_PENDIENTE,
        server_default=ESTADO_MENSAJE_PENDIENTE,
        nullable=False,
    )
    fecha_envio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    chat = relationship("Chat", back_populates="mensajes")
    idioma_detectado = relationship("Idioma")
    traducciones = relationship(
        "TraduccionMensajeChat",
        back_populates="mensaje",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

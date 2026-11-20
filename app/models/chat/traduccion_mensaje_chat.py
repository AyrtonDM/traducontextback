from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


ESTADO_TRADUCCION_PENDIENTE = "pendiente"
ESTADO_TRADUCCION_TRADUCIDO = "traducido"
ESTADO_TRADUCCION_SIN_TRADUCCION = "sin_traduccion"
ESTADO_TRADUCCION_ERROR = "error"


class TraduccionMensajeChat(Base):
    """
    Traduccion de un mensaje para un destinatario, en su idioma de lectura de ese chat.
    'sin_traduccion': el mensaje ya estaba en ese idioma y se entrega el original.
    """

    __tablename__ = "traduccion_mensaje_chat"
    __table_args__ = (
        UniqueConstraint("id_mensaje", "id_destinatario", name="uq_traduccion_mensaje_chat_destinatario"),
        CheckConstraint(
            "estado IN ('pendiente', 'traducido', 'sin_traduccion', 'error')",
            name="ck_traduccion_mensaje_chat_estado",
        ),
    )

    id_traduccion: Mapped[int] = mapped_column(primary_key=True, index=True)
    id_mensaje: Mapped[int] = mapped_column(
        ForeignKey("mensaje_chat.id_mensaje", ondelete="CASCADE"),
        nullable=False,
    )
    id_destinatario: Mapped[int] = mapped_column(
        ForeignKey("usuario.id", ondelete="CASCADE"),
        nullable=False,
    )
    id_idioma_destino: Mapped[int] = mapped_column(
        ForeignKey("idioma.id_idioma"),
        nullable=False,
    )
    texto_traducido: Mapped[str | None] = mapped_column(Text, nullable=True)
    estado: Mapped[str] = mapped_column(
        String(20),
        default=ESTADO_TRADUCCION_PENDIENTE,
        server_default=ESTADO_TRADUCCION_PENDIENTE,
        nullable=False,
    )
    # Mensaje generico para el cliente; nunca incluye el texto del mensaje
    error: Mapped[str | None] = mapped_column(String(300), nullable=True)
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    mensaje = relationship("MensajeChat", back_populates="traducciones")

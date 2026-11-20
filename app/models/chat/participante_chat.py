from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class ParticipanteChat(Base):
    """
    Miembro de un chat con su idioma de lectura en ese chat. Los no leidos se calculan con
    `id_ultimo_mensaje_leido` (mensajes del otro con id mayor), sin una marca por mensaje.
    """

    __tablename__ = "participante_chat"
    __table_args__ = (
        Index("ix_participante_chat_usuario", "id_usuario"),
    )

    id_chat: Mapped[int] = mapped_column(
        ForeignKey("chat.id_chat", ondelete="CASCADE"),
        primary_key=True,
    )
    id_usuario: Mapped[int] = mapped_column(
        ForeignKey("usuario.id", ondelete="CASCADE"),
        primary_key=True,
    )
    id_idioma_lectura: Mapped[int] = mapped_column(
        ForeignKey("idioma.id_idioma"),
        nullable=False,
    )
    # Sin FK a mensaje_chat para no crear una dependencia circular; solo se compara con ids
    id_ultimo_mensaje_leido: Mapped[int | None] = mapped_column(nullable=True)
    fecha_union: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    fecha_ultimo_acceso: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    chat = relationship("Chat", back_populates="participantes")
    usuario = relationship("Usuario")
    idioma_lectura = relationship("Idioma")

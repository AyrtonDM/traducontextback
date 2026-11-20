from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Chat(Base):
    """
    Chat 1 a 1 entre dos usuarios. El par se guarda ordenado (menor < mayor) y es unico, asi
    A->B y B->A son siempre el mismo chat. No confundir con `conversacion` (interprete de un
    solo dispositivo).
    """

    __tablename__ = "chat"
    __table_args__ = (
        UniqueConstraint("id_usuario_menor", "id_usuario_mayor", name="uq_chat_par_usuarios"),
        CheckConstraint("id_usuario_menor < id_usuario_mayor", name="ck_chat_par_ordenado"),
        Index("ix_chat_usuario_mayor", "id_usuario_mayor"),
    )

    id_chat: Mapped[int] = mapped_column(primary_key=True, index=True)
    id_usuario_menor: Mapped[int] = mapped_column(
        ForeignKey("usuario.id", ondelete="CASCADE"),
        nullable=False,
    )
    id_usuario_mayor: Mapped[int] = mapped_column(
        ForeignKey("usuario.id", ondelete="CASCADE"),
        nullable=False,
    )
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    fecha_ultimo_mensaje: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    participantes = relationship(
        "ParticipanteChat",
        back_populates="chat",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    mensajes = relationship(
        "MensajeChat",
        back_populates="chat",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

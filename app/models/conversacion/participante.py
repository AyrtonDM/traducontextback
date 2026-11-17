from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


ORDEN_PARTICIPANTE_ORIGEN = 1
ORDEN_PARTICIPANTE_DESTINO = 2


class ParticipanteConversacion(Base):
    """
    Participante de una conversacion (HU-31). Cada sesion tiene dos:
    el 1 habla el idioma de origen y el 2 el de destino.
    """

    __tablename__ = "participante_conversacion"
    __table_args__ = (
        UniqueConstraint("id_conversacion", "orden", name="uq_participante_conversacion_orden"),
        CheckConstraint("orden IN (1, 2)", name="ck_participante_conversacion_orden"),
    )

    id_participante: Mapped[int] = mapped_column(primary_key=True, index=True)
    id_conversacion: Mapped[int] = mapped_column(
        ForeignKey("conversacion.id_conversacion", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    id_idioma: Mapped[int] = mapped_column(
        ForeignKey("idioma.id_idioma"),
        nullable=False,
    )
    orden: Mapped[int] = mapped_column(nullable=False)

    conversacion = relationship("Conversacion", back_populates="participantes")
    idioma = relationship("Idioma")

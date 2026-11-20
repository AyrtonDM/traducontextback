from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class ParticipanteExterno(Base):
    """
    Participante de una sesion externa (HU-40). Puede venir de la plataforma (nombre real) o ser una
    etiqueta generica ('Participante 1', 'Participante 2'...) que el usuario puede renombrar.
    """

    __tablename__ = "participante_externo"
    __table_args__ = (
        UniqueConstraint("id_sesion_externa", "orden", name="uq_participante_externo_orden"),
    )

    id_participante: Mapped[int] = mapped_column(primary_key=True, index=True)
    id_sesion_externa: Mapped[int] = mapped_column(
        ForeignKey("sesion_externa.id_sesion_externa", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    orden: Mapped[int] = mapped_column(nullable=False)
    # True si la etiqueta es generica (renombrable); False si el nombre lo informo la plataforma
    generico: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Identificador del participante en la plataforma, para no duplicarlo al sincronizar
    id_externo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    desde_plataforma: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )

    sesion = relationship("SesionExterna", back_populates="participantes")

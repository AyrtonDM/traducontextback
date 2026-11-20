from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class IntervencionExterna(Base):
    """
    Intervencion transcrita de una reunion externa (HU-37) y su traduccion (HU-38).
    Sin participante = no se pudo determinar el hablante (HU-40: no se asigna una identidad incorrecta).
    Si no se identifico el idioma, los idiomas quedan en null y el estado en 'error'.
    """

    __tablename__ = "intervencion_externa"
    __table_args__ = (
        UniqueConstraint("id_sesion_externa", "orden", name="uq_intervencion_externa_orden"),
        CheckConstraint(
            "estado IN ('procesando', 'traducida', 'error')",
            name="ck_intervencion_externa_estado",
        ),
    )

    id_intervencion: Mapped[int] = mapped_column(primary_key=True, index=True)
    id_sesion_externa: Mapped[int] = mapped_column(
        ForeignKey("sesion_externa.id_sesion_externa", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    id_participante: Mapped[int | None] = mapped_column(
        ForeignKey("participante_externo.id_participante", ondelete="SET NULL"),
        nullable=True,
    )
    orden: Mapped[int] = mapped_column(nullable=False)
    texto_original: Mapped[str] = mapped_column(Text, nullable=False)
    texto_traducido: Mapped[str | None] = mapped_column(Text, nullable=True)
    id_idioma_origen: Mapped[int | None] = mapped_column(ForeignKey("idioma.id_idioma"), nullable=True)
    id_idioma_destino: Mapped[int | None] = mapped_column(ForeignKey("idioma.id_idioma"), nullable=True)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="procesando")
    mensaje_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    fecha_actualizacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sesion = relationship("SesionExterna", back_populates="intervenciones")
    participante = relationship("ParticipanteExterno")
    idioma_origen = relationship("Idioma", foreign_keys=[id_idioma_origen])
    idioma_destino = relationship("Idioma", foreign_keys=[id_idioma_destino])

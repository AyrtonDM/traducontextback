from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


ESTADO_PROCESANDO = "procesando"
ESTADO_TRADUCIDA = "traducida"
ESTADO_ERROR = "error"
ESTADOS_INTERVENCION = (ESTADO_PROCESANDO, ESTADO_TRADUCIDA, ESTADO_ERROR)


class Intervencion(Base):
    """
    Intervencion escrita de una conversacion (HU-26, HU-27, HU-31): texto original del
    participante que habla y su traduccion al idioma del otro participante.
    """

    __tablename__ = "intervencion"
    __table_args__ = (
        UniqueConstraint("id_conversacion", "orden", name="uq_intervencion_conversacion_orden"),
        CheckConstraint(
            "estado IN ('procesando', 'traducida', 'error')",
            name="ck_intervencion_estado",
        ),
        CheckConstraint(
            "id_idioma_origen <> id_idioma_destino",
            name="ck_intervencion_idiomas_distintos",
        ),
    )

    id_intervencion: Mapped[int] = mapped_column(primary_key=True, index=True)
    id_conversacion: Mapped[int] = mapped_column(
        ForeignKey("conversacion.id_conversacion", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    # SET NULL: si no se puede identificar al hablante la intervencion se conserva (HU-31)
    id_participante: Mapped[int | None] = mapped_column(
        ForeignKey("participante_conversacion.id_participante", ondelete="SET NULL"),
        nullable=True,
    )
    orden: Mapped[int] = mapped_column(nullable=False)
    texto_original: Mapped[str] = mapped_column(Text, nullable=False)
    texto_traducido: Mapped[str | None] = mapped_column(Text, nullable=True)
    id_idioma_origen: Mapped[int] = mapped_column(
        ForeignKey("idioma.id_idioma"),
        nullable=False,
    )
    id_idioma_destino: Mapped[int] = mapped_column(
        ForeignKey("idioma.id_idioma"),
        nullable=False,
    )
    estado: Mapped[str] = mapped_column(
        String(20),
        default=ESTADO_PROCESANDO,
        server_default=ESTADO_PROCESANDO,
        nullable=False,
    )
    mensaje_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    fecha_actualizacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    conversacion = relationship("Conversacion", back_populates="intervenciones")
    participante = relationship("ParticipanteConversacion")
    idioma_origen = relationship("Idioma", foreign_keys=[id_idioma_origen])
    idioma_destino = relationship("Idioma", foreign_keys=[id_idioma_destino])

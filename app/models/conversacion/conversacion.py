from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, Text, func, true, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


ESTADO_ACTIVA = "activa"
ESTADO_PAUSADA = "pausada"
ESTADO_FINALIZADA = "finalizada"
ESTADOS_CONVERSACION = (ESTADO_ACTIVA, ESTADO_PAUSADA, ESTADO_FINALIZADA)


class Conversacion(Base):
    """
    Sesion de conversacion de un usuario con sus idiomas, contexto y entorno.
    Sus participantes e intervenciones se eliminan en cascada con ella.
    """

    __tablename__ = "conversacion"
    __table_args__ = (
        CheckConstraint(
            "id_idioma_origen <> id_idioma_destino",
            name="ck_conversacion_idiomas_distintos",
        ),
        CheckConstraint(
            "estado IN ('activa', 'pausada', 'finalizada')",
            name="ck_conversacion_estado",
        ),
    )

    id_conversacion: Mapped[int] = mapped_column(primary_key=True, index=True)
    estado: Mapped[str] = mapped_column(
        String(20),
        default=ESTADO_ACTIVA,
        server_default=ESTADO_ACTIVA,
        nullable=False,
    )
    fecha_inicio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    fecha_actualizacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    fecha_fin: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    id_usuario: Mapped[int] = mapped_column(
        ForeignKey("usuario.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    id_idioma_origen: Mapped[int] = mapped_column(
        ForeignKey("idioma.id_idioma"),
        nullable=False,
    )
    id_idioma_destino: Mapped[int] = mapped_column(
        ForeignKey("idioma.id_idioma"),
        nullable=False,
    )
    id_contexto: Mapped[int | None] = mapped_column(
        ForeignKey("contexto.id_contexto", ondelete="SET NULL"),
        nullable=True,
    )
    id_entorno: Mapped[int] = mapped_column(
        ForeignKey("entorno.id_entorno"),
        nullable=False,
    )
    id_tono: Mapped[int | None] = mapped_column(
        ForeignKey("tono.id_tono", ondelete="SET NULL"),
        nullable=True,
    )
    # HU-32: glosario del usuario; se aplica a las intervenciones en el mismo sentido que su par de idiomas.
    # Si se elimina el glosario, la conversacion queda sin glosario.
    id_glosario: Mapped[int | None] = mapped_column(
        ForeignKey("glosario.id_glosario", ondelete="SET NULL"),
        nullable=True,
    )
    # Descripcion personalizada del contexto: situacion, audiencia o terminologia (HU-29)
    descripcion_contexto: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Preferencias guardadas en la sesion; su efecto llega con HU-29 (contexto acumulado) y HU-30
    mantener_contexto: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=true(),
        nullable=False,
    )
    asistencia_conversacional: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=false(),
        nullable=False,
    )

    usuario = relationship("Usuario", back_populates="conversaciones")
    idioma_origen = relationship("Idioma", foreign_keys=[id_idioma_origen])
    idioma_destino = relationship("Idioma", foreign_keys=[id_idioma_destino])
    contexto = relationship("Contexto")
    entorno = relationship("Entorno", back_populates="conversaciones")
    tono = relationship("Tono")
    glosario = relationship("Glosario")
    participantes = relationship(
        "ParticipanteConversacion",
        back_populates="conversacion",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ParticipanteConversacion.orden",
    )
    intervenciones = relationship(
        "Intervencion",
        back_populates="conversacion",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Intervencion.orden",
    )

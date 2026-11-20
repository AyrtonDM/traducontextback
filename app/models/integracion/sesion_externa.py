from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


ESTADO_CONFIGURADA = "configurada"
ESTADO_ACTIVA = "activa"
ESTADO_PAUSADA = "pausada"
ESTADO_FINALIZADA = "finalizada"
ESTADOS_SESION_EXTERNA = (ESTADO_CONFIGURADA, ESTADO_ACTIVA, ESTADO_PAUSADA, ESTADO_FINALIZADA)


class SesionExterna(Base):
    """
    Sesion de traduccion asociada a una reunion de Google Meet o Zoom (HU-36 a HU-41).
    'configurada' -> 'activa' <-> 'pausada' -> 'finalizada'. Al finalizar queda en el historial.
    Sus participantes e intervenciones se eliminan en cascada con ella.
    """

    __tablename__ = "sesion_externa"
    __table_args__ = (
        CheckConstraint(
            "plataforma IN ('google_meet', 'zoom')",
            name="ck_sesion_externa_plataforma",
        ),
        CheckConstraint(
            "estado IN ('configurada', 'activa', 'pausada', 'finalizada')",
            name="ck_sesion_externa_estado",
        ),
        CheckConstraint(
            "id_idioma_origen <> id_idioma_destino",
            name="ck_sesion_externa_idiomas_distintos",
        ),
    )

    id_sesion_externa: Mapped[int] = mapped_column(primary_key=True, index=True)
    id_usuario: Mapped[int] = mapped_column(
        ForeignKey("usuario.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    plataforma: Mapped[str] = mapped_column(String(20), nullable=False)
    # Lo que escribio el usuario y la referencia normalizada (codigo de Meet o ID numerico de Zoom)
    enlace_reunion: Mapped[str] = mapped_column(Text, nullable=False)
    referencia_reunion: Mapped[str] = mapped_column(String(64), nullable=False)
    estado: Mapped[str] = mapped_column(
        String(20),
        default=ESTADO_CONFIGURADA,
        server_default=ESTADO_CONFIGURADA,
        nullable=False,
    )
    # Idiomas de los participantes: la traduccion es bidireccional entre ambos
    id_idioma_origen: Mapped[int] = mapped_column(ForeignKey("idioma.id_idioma"), nullable=False)
    id_idioma_destino: Mapped[int] = mapped_column(ForeignKey("idioma.id_idioma"), nullable=False)
    id_contexto: Mapped[int | None] = mapped_column(
        ForeignKey("contexto.id_contexto", ondelete="SET NULL"),
        nullable=True,
    )
    id_entorno: Mapped[int] = mapped_column(ForeignKey("entorno.id_entorno"), nullable=False)
    id_tono: Mapped[int | None] = mapped_column(
        ForeignKey("tono.id_tono", ondelete="SET NULL"),
        nullable=True,
    )
    id_glosario: Mapped[int | None] = mapped_column(
        ForeignKey("glosario.id_glosario", ondelete="SET NULL"),
        nullable=True,
    )
    descripcion_contexto: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    fecha_inicio: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fecha_actualizacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fecha_fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    usuario = relationship("Usuario", back_populates="sesiones_externas")
    idioma_origen = relationship("Idioma", foreign_keys=[id_idioma_origen])
    idioma_destino = relationship("Idioma", foreign_keys=[id_idioma_destino])
    contexto = relationship("Contexto")
    entorno = relationship("Entorno")
    tono = relationship("Tono")
    glosario = relationship("Glosario")
    participantes = relationship(
        "ParticipanteExterno",
        back_populates="sesion",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ParticipanteExterno.orden",
    )
    intervenciones = relationship(
        "IntervencionExterna",
        back_populates="sesion",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="IntervencionExterna.orden",
    )

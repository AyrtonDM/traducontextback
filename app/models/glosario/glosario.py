from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Glosario(Base):
    """Glosario personalizado de un usuario para un par de idiomas concreto."""

    __tablename__ = "glosario"
    __table_args__ = (
        CheckConstraint(
            "id_idioma_origen <> id_idioma_destino",
            name="ck_glosario_idiomas_distintos",
        ),
    )

    id_glosario: Mapped[int] = mapped_column(primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    fecha_actualizacion: Mapped[datetime | None] = mapped_column(
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

    usuario = relationship("Usuario", back_populates="glosarios")
    idioma_origen = relationship("Idioma", foreign_keys=[id_idioma_origen])
    idioma_destino = relationship("Idioma", foreign_keys=[id_idioma_destino])
    terminos = relationship(
        "TerminoGlosario",
        back_populates="glosario",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="TerminoGlosario.id_termino_glosario",
    )
    traducciones = relationship("Traduccion", back_populates="glosario")
    traducciones_documento = relationship(
        "TraduccionDocumento",
        back_populates="glosario",
    )

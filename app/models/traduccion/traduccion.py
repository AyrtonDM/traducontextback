from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Traduccion(Base):
    __tablename__ = "traduccion"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    texto_original: Mapped[str] = mapped_column(Text, nullable=False)
    texto_traducido: Mapped[str] = mapped_column(Text, nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    id_contexto: Mapped[int] = mapped_column(
        ForeignKey("contexto.id"),
        nullable=False,
    )
    id_idioma_origen: Mapped[int] = mapped_column(
        ForeignKey("idioma.id"),
        nullable=False,
    )
    id_idioma_destino: Mapped[int] = mapped_column(
        ForeignKey("idioma.id"),
        nullable=False,
    )

    contexto = relationship("Contexto", back_populates="traducciones")
    idioma_origen = relationship(
        "Idioma",
        foreign_keys=[id_idioma_origen],
        back_populates="traducciones_origen",
    )
    idioma_destino = relationship(
        "Idioma",
        foreign_keys=[id_idioma_destino],
        back_populates="traducciones_destino",
    )
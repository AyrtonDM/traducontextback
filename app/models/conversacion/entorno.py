from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Entorno(Base):
    """
    Entorno en el que se desarrolla una conversacion (reunion, clase, entrevista, etc.).
    Es un catalogo distinto de los contextos de dominio (tabla 'contexto').
    """

    __tablename__ = "entorno"

    id_entorno: Mapped[int] = mapped_column(primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    activo: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    conversaciones = relationship("Conversacion", back_populates="entorno")

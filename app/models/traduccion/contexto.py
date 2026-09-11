from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Contexto(Base):
    __tablename__ = "contexto"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    id_usuario: Mapped[int] = mapped_column(ForeignKey("usuario.id"), nullable=False)

    usuario = relationship("Usuario", back_populates="contextos")
    traducciones = relationship(
        "Traduccion",
        back_populates="contexto",
        cascade="all, delete-orphan",
    )
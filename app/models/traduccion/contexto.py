from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Contexto(Base):
    __tablename__ = "contexto"

    id_contexto: Mapped[int] = mapped_column(primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    personalizado: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    activo: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    id_usuario: Mapped[int | None] = mapped_column(
        ForeignKey("usuario.id"),
        nullable=True,
    )

    usuario = relationship("Usuario", back_populates="contextos")
    configuraciones_traduccion = relationship(
        "ConfiguracionTraduccion",
        back_populates="contexto",
        cascade="all, delete-orphan",
    )

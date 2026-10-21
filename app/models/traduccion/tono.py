from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Tono(Base):
    __tablename__ = "tono"

    id_tono: Mapped[int] = mapped_column(primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    activo: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    configuraciones_traduccion = relationship(
        "ConfiguracionTraduccion",
        back_populates="tono",
        cascade="all, delete-orphan",
    )


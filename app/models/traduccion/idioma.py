from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Idioma(Base):
    __tablename__ = "idioma"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    codigo: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)

    traducciones_origen = relationship(
        "Traduccion",
        foreign_keys="Traduccion.id_idioma_origen",
        back_populates="idioma_origen",
    )
    traducciones_destino = relationship(
        "Traduccion",
        foreign_keys="Traduccion.id_idioma_destino",
        back_populates="idioma_destino",
    )
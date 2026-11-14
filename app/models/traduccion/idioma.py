from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Idioma(Base):
    __tablename__ = "idioma"

    id_idioma: Mapped[int] = mapped_column(primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    codigo: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)

    variantes_regionales = relationship(
        "VarianteRegional",
        back_populates="idioma",
        cascade="all, delete-orphan",
    )
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
    documentos_origen = relationship(
        "TraduccionDocumento",
        foreign_keys="TraduccionDocumento.id_idioma_origen",
        back_populates="idioma_origen",
    )
    documentos_destino = relationship(
        "TraduccionDocumento",
        foreign_keys="TraduccionDocumento.id_idioma_destino",
        back_populates="idioma_destino",
    )

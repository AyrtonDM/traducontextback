from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class VarianteRegional(Base):
    __tablename__ = "variante_regional"

    id_variante_regional: Mapped[int] = mapped_column(primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    activo: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    id_idioma: Mapped[int] = mapped_column(
        ForeignKey("idioma.id_idioma"),
        nullable=False,
    )

    idioma = relationship("Idioma", back_populates="variantes_regionales")
    configuraciones_traduccion = relationship(
        "ConfiguracionTraduccion",
        back_populates="variante_regional",
        cascade="all, delete-orphan",
    )


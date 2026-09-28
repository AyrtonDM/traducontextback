from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class ConfiguracionTraduccion(Base):
    __tablename__ = "configuracion_traduccion"

    id_configuracion_traduccion: Mapped[int] = mapped_column(primary_key=True, index=True)
    id_contexto: Mapped[int] = mapped_column(
        ForeignKey("contexto.id_contexto"),
        nullable=False,
    )

    contexto = relationship("Contexto", back_populates="configuraciones_traduccion")
    traducciones = relationship(
        "Traduccion",
        back_populates="configuracion_traduccion",
        cascade="all, delete-orphan",
    )

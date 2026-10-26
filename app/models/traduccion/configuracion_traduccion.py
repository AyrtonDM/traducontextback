from sqlalchemy import Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class ConfiguracionTraduccion(Base):
    __tablename__ = "configuracion_traduccion"

    id_configuracion_traduccion: Mapped[int] = mapped_column(primary_key=True, index=True)
    explicar_expresiones: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    generar_alternativas: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    id_contexto: Mapped[int] = mapped_column(
        ForeignKey("contexto.id_contexto"),
        nullable=False,
    )
    id_tono: Mapped[int | None] = mapped_column(
        ForeignKey("tono.id_tono"),
        nullable=True,
    )
    id_variante_regional: Mapped[int | None] = mapped_column(
        ForeignKey("variante_regional.id_variante_regional"),
        nullable=True,
    )
    id_usuario: Mapped[int | None] = mapped_column(
        ForeignKey("usuario.id"),
        unique=True,
        index=True,
        nullable=True,
    )

    contexto = relationship("Contexto", back_populates="configuraciones_traduccion")
    tono = relationship("Tono", back_populates="configuraciones_traduccion")
    variante_regional = relationship(
        "VarianteRegional",
        back_populates="configuraciones_traduccion",
    )
    usuario = relationship(
        "Usuario",
        back_populates="configuraciones_traduccion",
    )
    traducciones = relationship(
        "Traduccion",
        back_populates="configuracion_traduccion",
        cascade="all, delete-orphan",
    )

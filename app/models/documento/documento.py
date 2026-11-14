from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Documento(Base):
    __tablename__ = "documento"

    id_documento: Mapped[int] = mapped_column(primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    tipo_mime: Mapped[str] = mapped_column(String(100), nullable=False)
    extension: Mapped[str] = mapped_column(String(20), nullable=False)
    tamano: Mapped[int] = mapped_column(BigInteger, nullable=False)
    ruta_archivo: Mapped[str] = mapped_column(String(500), nullable=False)
    fecha_carga: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    id_usuario: Mapped[int] = mapped_column(
        ForeignKey("usuario.id"),
        nullable=False,
    )
    id_idioma_origen: Mapped[int | None] = mapped_column(
        ForeignKey("idioma.id_idioma"),
        nullable=True,
    )
    id_configuracion_traduccion: Mapped[int | None] = mapped_column(
        ForeignKey("configuracion_traduccion.id_configuracion_traduccion"),
        nullable=True,
    )

    usuario = relationship(
        "Usuario",
        back_populates="documentos",
    )
    idioma_origen = relationship(
        "Idioma",
        foreign_keys=[id_idioma_origen],
        back_populates="documentos",
    )
    configuracion_traduccion = relationship(
        "ConfiguracionTraduccion",
        back_populates="documentos",
    )
    traducciones_documento = relationship(
        "TraduccionDocumento",
        back_populates="documento",
    )

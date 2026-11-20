from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class TraduccionDocumento(Base):
    __tablename__ = "traduccion_documento"

    id_traduccion_documento: Mapped[int] = mapped_column(primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    extension: Mapped[str] = mapped_column(String(20), nullable=False)
    estado: Mapped[str] = mapped_column(String(30), default="COMPLETADO", nullable=False)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    ruta_archivo: Mapped[str] = mapped_column(String(500), nullable=False)
    id_documento: Mapped[int | None] = mapped_column(
        ForeignKey("documento.id_documento", ondelete="SET NULL"),
        nullable=True,
    )
    id_usuario: Mapped[int] = mapped_column(
        ForeignKey("usuario.id"),
        nullable=False,
    )
    id_idioma_origen: Mapped[int] = mapped_column(
        ForeignKey("idioma.id_idioma"),
        nullable=False,
    )
    id_idioma_destino: Mapped[int] = mapped_column(
        ForeignKey("idioma.id_idioma"),
        nullable=False,
    )
    # Un solo glosario por traduccion (si se elimina el glosario, se conserva la traduccion)
    id_glosario: Mapped[int | None] = mapped_column(
        ForeignKey("glosario.id_glosario", ondelete="SET NULL"),
        nullable=True,
    )

    documento = relationship(
        "Documento",
        back_populates="traducciones_documento",
    )
    usuario = relationship(
        "Usuario",
        back_populates="traducciones_documento",
    )
    idioma_origen = relationship(
        "Idioma",
        foreign_keys=[id_idioma_origen],
        back_populates="documentos_origen",
    )
    idioma_destino = relationship(
        "Idioma",
        foreign_keys=[id_idioma_destino],
        back_populates="documentos_destino",
    )
    glosario = relationship(
        "Glosario",
        back_populates="traducciones_documento",
    )

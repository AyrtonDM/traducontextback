from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class CodigoVerificacion(Base):
    __tablename__ = "codigo_verificacion"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    id_usuario: Mapped[int] = mapped_column(
        ForeignKey("usuario.id"),
        index=True,
        nullable=False,
    )
    codigo: Mapped[str] = mapped_column(String(6), index=True, nullable=False)
    expira_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    utilizado: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    usuario = relationship("Usuario", back_populates="codigos_verificacion")

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Rol(Base):
    __tablename__ = "rol"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    usuarios = relationship("Usuario", back_populates="rol")
    rol_permisos = relationship(
        "RolPermiso",
        back_populates="rol",
        cascade="all, delete-orphan",
    )

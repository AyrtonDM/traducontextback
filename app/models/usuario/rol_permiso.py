from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class RolPermiso(Base):
    __tablename__ = "rol_permiso"
    __table_args__ = (
        UniqueConstraint("id_rol", "id_permiso", name="uq_rol_permiso"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    id_rol: Mapped[int] = mapped_column(ForeignKey("rol.id"), nullable=False)
    id_permiso: Mapped[int] = mapped_column(
        ForeignKey("permiso.id"),
        nullable=False,
    )

    rol = relationship("Rol", back_populates="rol_permisos")
    permiso = relationship("Permiso", back_populates="rol_permisos")

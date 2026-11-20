from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


PLATAFORMA_GOOGLE_MEET = "google_meet"
PLATAFORMA_ZOOM = "zoom"
PLATAFORMAS = (PLATAFORMA_GOOGLE_MEET, PLATAFORMA_ZOOM)


class ConexionPlataforma(Base):
    """
    Vinculacion OAuth de un usuario con Google Meet o Zoom (HU-35). Los tokens se guardan cifrados
    (Fernet) y nunca se devuelven al cliente. Una conexion por usuario y plataforma.
    """

    __tablename__ = "conexion_plataforma"
    __table_args__ = (
        UniqueConstraint("id_usuario", "plataforma", name="uq_conexion_plataforma_usuario"),
        CheckConstraint(
            "plataforma IN ('google_meet', 'zoom')",
            name="ck_conexion_plataforma_plataforma",
        ),
    )

    id_conexion: Mapped[int] = mapped_column(primary_key=True, index=True)
    id_usuario: Mapped[int] = mapped_column(
        ForeignKey("usuario.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    plataforma: Mapped[str] = mapped_column(String(20), nullable=False)
    access_token_cifrado: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token_cifrado: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_expiracion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Permisos concedidos, separados por espacios (como los devuelve OAuth)
    alcances: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Correo o nombre de la cuenta externa, solo para mostrarlo
    cuenta_externa: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    fecha_actualizacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    usuario = relationship("Usuario", back_populates="conexiones_plataforma")

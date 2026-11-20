from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, func, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Usuario(Base):
    __tablename__ = "usuario"
    __table_args__ = (
        CheckConstraint(
            "estado in ('ACTIVO', 'INACTIVO', 'SUSPENDIDO')",
            name="ck_usuario_estado",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    correo: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    contrasena: Mapped[str] = mapped_column(String(255), nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    fecha_actualizacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    estado: Mapped[str] = mapped_column(
        String(20),
        default="INACTIVO",
        nullable=False,
    )
    # Ruta relativa (desde la raiz del backend) de la foto en documentos/fotos_perfil
    foto_perfil: Mapped[str | None] = mapped_column(String(500), nullable=True)
    id_rol: Mapped[int] = mapped_column(ForeignKey("rol.id"), nullable=False)
    # HU-34: si esta activo, se registran y se aplican sus correcciones en las siguientes traducciones
    aprendizaje_activo: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=true(),
        nullable=False,
    )

    rol = relationship("Rol", back_populates="usuarios")
    codigos_verificacion = relationship(
        "CodigoVerificacion",
        back_populates="usuario",
        cascade="all, delete-orphan",
    )
    sesiones = relationship(
        "Sesion",
        back_populates="usuario",
        cascade="all, delete-orphan",
    )
    traducciones = relationship(
        "Traduccion",
        back_populates="usuario",
        cascade="all, delete-orphan",
    )
    contextos = relationship(
        "Contexto",
        back_populates="usuario",
    )
    configuraciones_traduccion = relationship(
        "ConfiguracionTraduccion",
        back_populates="usuario",
    )
    documentos = relationship(
        "Documento",
        back_populates="usuario",
        cascade="all, delete-orphan",
    )
    traducciones_documento = relationship(
        "TraduccionDocumento",
        back_populates="usuario",
        cascade="all, delete-orphan",
    )
    glosarios = relationship(
        "Glosario",
        back_populates="usuario",
        cascade="all, delete-orphan",
    )
    conversaciones = relationship(
        "Conversacion",
        back_populates="usuario",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    correcciones_traduccion = relationship(
        "CorreccionTraduccion",
        back_populates="usuario",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    conexiones_plataforma = relationship(
        "ConexionPlataforma",
        back_populates="usuario",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    sesiones_externas = relationship(
        "SesionExterna",
        back_populates="usuario",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, func, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


PLATAFORMA_ANDROID = "android"
PLATAFORMA_IOS = "ios"
PLATAFORMAS_PUSH = (PLATAFORMA_ANDROID, PLATAFORMA_IOS)


class DispositivoPush(Base):
    """
    Dispositivo movil registrado para recibir notificaciones push por FCM.
    El token de FCM es unico: si otro usuario inicia sesion en el mismo telefono,
    el registro se reasigna a ese usuario. Al fallar un envio por token invalido
    el dispositivo se marca como inactivo.
    """

    __tablename__ = "dispositivo_push"
    __table_args__ = (
        CheckConstraint(
            "plataforma IN ('android', 'ios')",
            name="ck_dispositivo_push_plataforma",
        ),
        Index("ix_dispositivo_push_usuario_activo", "id_usuario", "activo"),
    )

    id_dispositivo: Mapped[int] = mapped_column(primary_key=True, index=True)
    id_usuario: Mapped[int] = mapped_column(
        ForeignKey("usuario.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_fcm: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    plataforma: Mapped[str] = mapped_column(String(20), nullable=False)
    activo: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=true(),
        nullable=False,
    )
    fecha_registro: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    fecha_ultimo_uso: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    usuario = relationship("Usuario", back_populates="dispositivos_push")

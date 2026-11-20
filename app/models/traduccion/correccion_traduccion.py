from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


TIPO_CORRECCION = "correccion"
TIPO_ALTERNATIVA = "alternativa"
TIPOS_CORRECCION = (TIPO_CORRECCION, TIPO_ALTERNATIVA)


class CorreccionTraduccion(Base):
    """
    Aprendizaje de preferencias (HU-34): correccion manual del usuario sobre una traduccion o
    alternativa que eligio (HU-18). Orienta las siguientes traducciones del mismo usuario y par de
    idiomas. Es solo del usuario que la genero y se elimina con su cuenta.
    """

    __tablename__ = "correccion_traduccion"
    __table_args__ = (
        CheckConstraint(
            "tipo IN ('correccion', 'alternativa')",
            name="ck_correccion_traduccion_tipo",
        ),
        CheckConstraint(
            "id_idioma_origen <> id_idioma_destino",
            name="ck_correccion_traduccion_idiomas_distintos",
        ),
        Index(
            "ix_correccion_traduccion_usuario_par",
            "id_usuario",
            "id_idioma_origen",
            "id_idioma_destino",
        ),
    )

    id_correccion: Mapped[int] = mapped_column(primary_key=True, index=True)
    id_usuario: Mapped[int] = mapped_column(
        ForeignKey("usuario.id", ondelete="CASCADE"),
        nullable=False,
    )
    id_idioma_origen: Mapped[int] = mapped_column(ForeignKey("idioma.id_idioma"), nullable=False)
    id_idioma_destino: Mapped[int] = mapped_column(ForeignKey("idioma.id_idioma"), nullable=False)
    texto_original: Mapped[str] = mapped_column(Text, nullable=False)
    traduccion_generada: Mapped[str] = mapped_column(Text, nullable=False)
    traduccion_corregida: Mapped[str] = mapped_column(Text, nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False, default=TIPO_CORRECCION)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    fecha_actualizacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    usuario = relationship("Usuario", back_populates="correcciones_traduccion")
    idioma_origen = relationship("Idioma", foreign_keys=[id_idioma_origen])
    idioma_destino = relationship("Idioma", foreign_keys=[id_idioma_destino])

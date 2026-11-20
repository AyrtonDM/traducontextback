from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class TerminoGlosario(Base):
    """
    Termino de un glosario con su regla de traduccion:
    - conservar_original=True  -> el termino se mantiene tal cual en la traduccion.
    - conservar_original=False -> el termino se reemplaza por traduccion_preferida.
    """

    __tablename__ = "termino_glosario"
    __table_args__ = (
        CheckConstraint(
            "conservar_original OR traduccion_preferida IS NOT NULL",
            name="ck_termino_glosario_regla",
        ),
    )

    id_termino_glosario: Mapped[int] = mapped_column(primary_key=True, index=True)
    termino_origen: Mapped[str] = mapped_column(String(255), nullable=False)
    traduccion_preferida: Mapped[str | None] = mapped_column(String(255), nullable=True)
    conservar_original: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    distinguir_mayusculas: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    nota: Mapped[str | None] = mapped_column(Text, nullable=True)
    id_glosario: Mapped[int] = mapped_column(
        ForeignKey("glosario.id_glosario", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    glosario = relationship("Glosario", back_populates="terminos")

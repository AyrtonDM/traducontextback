from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.idiomas import IDIOMAS
from app.models.traduccion.idioma import Idioma


def sembrar_idiomas(sesion: Session) -> None:
    """Crea los idiomas base en la base de datos si no existen."""
    codigos_existentes = set(
        sesion.scalars(select(Idioma.codigo)).all()
    )

    for codigo, nombre in IDIOMAS.items():
        if codigo not in codigos_existentes:
            sesion.add(
                Idioma(
                    codigo=codigo,
                    nombre=nombre,
                )
            )

    sesion.flush()

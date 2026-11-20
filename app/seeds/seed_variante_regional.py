from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.traduccion.idioma import Idioma
from app.models.traduccion.variante_regional import VarianteRegional
from app.seeds.seed_idiomas import sembrar_idiomas


VARIANTES_BASE = (
    ("Bolivia", "es-BO", "es"),
    ("Mexico", "es-MX", "es"),
    ("Espana", "es-ES", "es"),
    ("Estados Unidos", "en-US", "en"),
    ("Reino Unido", "en-GB", "en"),
)


def sembrar_variantes_regionales(sesion: Session) -> None:
    """Crea las variantes regionales base si no existen."""
    idiomas_db = {
        idioma.codigo: idioma.id_idioma
        for idioma in sesion.scalars(select(Idioma)).all()
    }

    if not idiomas_db:
        sembrar_idiomas(sesion)
        sesion.flush()
        idiomas_db = {
            idioma.codigo: idioma.id_idioma
            for idioma in sesion.scalars(select(Idioma)).all()
        }

    codigos_existentes = set(
        sesion.scalars(select(VarianteRegional.codigo)).all()
    )

    for nombre, codigo, codigo_idioma in VARIANTES_BASE:
        if codigo not in codigos_existentes:
            id_idioma = idiomas_db.get(codigo_idioma)
            if id_idioma is not None:
                sesion.add(
                    VarianteRegional(
                        nombre=nombre,
                        codigo=codigo,
                        activo=True,
                        id_idioma=id_idioma,
                    )
                )

    sesion.flush()


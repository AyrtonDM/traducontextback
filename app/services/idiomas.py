from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.traduccion.idioma import Idioma
from app.seeds.seed_idiomas import sembrar_idiomas


def obtener_todos_idiomas(sesion: Session) -> list[Idioma]:
    """Retorna la lista de todos los idiomas disponibles en el sistema ordenados alfabéticamente.
    
    Si la tabla esta vacia, realiza la siembra inicial de idiomas.
    """
    idiomas = list(sesion.scalars(select(Idioma).order_by(Idioma.nombre.asc())).all())
    if not idiomas:
        sembrar_idiomas(sesion)
        sesion.commit()
        idiomas = list(sesion.scalars(select(Idioma).order_by(Idioma.nombre.asc())).all())

    return idiomas

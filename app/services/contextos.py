from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.traduccion.contexto import Contexto
from app.seeds.seed_contexto import sembrar_contextos


def obtener_todos_contextos(sesion: Session, solo_activos: bool = True) -> list[Contexto]:
    """Retorna la lista de contextos registrados en el sistema."""
    consulta = select(Contexto)
    if solo_activos:
        consulta = consulta.where(Contexto.activo.is_(True))
    consulta = consulta.order_by(Contexto.id_contexto.asc())

    contextos = list(sesion.scalars(consulta).all())
    if not contextos:
        sembrar_contextos(sesion)
        sesion.commit()
        contextos = list(sesion.scalars(consulta).all())

    return contextos


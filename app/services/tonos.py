from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.traduccion.tono import Tono
from app.seeds.seed_tono import sembrar_tonos


def obtener_todos_tonos(sesion: Session, solo_activos: bool = True) -> list[Tono]:
    """Retorna la lista de tonos registrados en el sistema."""
    consulta = select(Tono)
    if solo_activos:
        consulta = consulta.where(Tono.activo.is_(True))
    consulta = consulta.order_by(Tono.id_tono.asc())

    tonos = list(sesion.scalars(consulta).all())
    if not tonos:
        sembrar_tonos(sesion)
        sesion.commit()
        tonos = list(sesion.scalars(consulta).all())

    return tonos


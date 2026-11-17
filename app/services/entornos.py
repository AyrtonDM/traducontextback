from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conversacion.entorno import Entorno


def obtener_entornos_activos(sesion: Session) -> list[Entorno]:
    """Lista los entornos de conversacion activos, ordenados por id."""
    return list(
        sesion.scalars(
            select(Entorno)
            .where(Entorno.activo.is_(True))
            .order_by(Entorno.id_entorno)
        ).all()
    )


def obtener_entorno_activo(sesion: Session, id_entorno: int) -> Entorno:
    """Obtiene un entorno activo o lanza ValueError."""
    entorno = sesion.scalar(
        select(Entorno).where(
            Entorno.id_entorno == id_entorno,
            Entorno.activo.is_(True),
        )
    )
    if not entorno:
        raise ValueError(f"Entorno con id {id_entorno} no encontrado o inactivo.")
    return entorno

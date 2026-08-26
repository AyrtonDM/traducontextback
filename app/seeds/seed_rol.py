from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.usuario.rol import Rol


ROLES_INICIALES = ("ADMINISTRADOR", "CLIENTE")


def sembrar_roles(sesion: Session) -> None:
    """Crea los roles base si aun no existen."""

    roles_existentes = set(
        sesion.scalars(
            select(Rol.nombre).where(Rol.nombre.in_(ROLES_INICIALES))
        ).all()
    )

    for nombre_rol in ROLES_INICIALES:
        if nombre_rol not in roles_existentes:
            sesion.add(Rol(nombre=nombre_rol))

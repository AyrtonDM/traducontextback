from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.usuario.rol import Rol
from app.models.usuario.permiso import Permiso
from app.models.usuario.rol_permiso import RolPermiso


ROLES_INICIALES = ("ADMINISTRADOR", "USUARIO")
PERMISOS_INICIALES = [
    {
        "nombre": "gestionar_usuarios",
        "descripcion": "Permite listar, crear, editar y eliminar usuarios",
    }
]


def sembrar_roles(sesion: Session) -> None:
    """Crea los roles y permisos base si aun no existen, y asocia permisos a roles."""

    # 1. Sembrar Roles
    roles_existentes = set(
        sesion.scalars(
            select(Rol.nombre).where(Rol.nombre.in_(ROLES_INICIALES))
        ).all()
    )

    for nombre_rol in ROLES_INICIALES:
        if nombre_rol not in roles_existentes:
            sesion.add(Rol(nombre=nombre_rol))

    sesion.flush()

    # 2. Sembrar Permisos
    nombres_permisos = [p["nombre"] for p in PERMISOS_INICIALES]
    permisos_existentes = set(
        sesion.scalars(
            select(Permiso.nombre).where(Permiso.nombre.in_(nombres_permisos))
        ).all()
    )

    for p_info in PERMISOS_INICIALES:
        if p_info["nombre"] not in permisos_existentes:
            sesion.add(Permiso(nombre=p_info["nombre"], descripcion=p_info["descripcion"]))

    sesion.flush()

    # 3. Asociar permisos a roles (gestionar_usuarios -> ADMINISTRADOR)
    rol_admin = sesion.scalar(select(Rol).where(Rol.nombre == "ADMINISTRADOR"))
    permiso_gestionar = sesion.scalar(select(Permiso).where(Permiso.nombre == "gestionar_usuarios"))

    if rol_admin and permiso_gestionar:
        asociacion_existente = sesion.scalar(
            select(RolPermiso)
            .where(RolPermiso.id_rol == rol_admin.id)
            .where(RolPermiso.id_permiso == permiso_gestionar.id)
        )
        if not asociacion_existente:
            sesion.add(RolPermiso(id_rol=rol_admin.id, id_permiso=permiso_gestionar.id))

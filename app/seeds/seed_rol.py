from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.usuario.rol import Rol
from app.models.usuario.permiso import Permiso
from app.models.usuario.rol_permiso import RolPermiso


ROLES_OFICIALES = ["ADMINISTRADOR", "USUARIO"]

PERMISOS_ADMIN = [
    "gestionar_usuarios",
    "administrar_planes",
    "ver_dashboard",
    "generar_reportes",
]


def sembrar_roles(sesion: Session) -> None:
    """Crea los roles y permisos base del sistema."""
    try:
        # 1. Asegurar la existencia de los roles oficiales
        for nombre_rol in ROLES_OFICIALES:
            rol_existente = sesion.scalar(
                select(Rol).where(Rol.nombre == nombre_rol)
            )

            if rol_existente is None:
                sesion.add(Rol(nombre=nombre_rol))

        sesion.flush()

        # Obtener el rol Administrador
        rol_admin = sesion.scalar(
            select(Rol).where(Rol.nombre == "ADMINISTRADOR")
        )

        # 2. Crear los permisos del sistema
        for nombre_permiso in PERMISOS_ADMIN:
            permiso_existente = sesion.scalar(
                select(Permiso).where(Permiso.nombre == nombre_permiso)
            )

            if permiso_existente is None:
                sesion.add(
                    Permiso(
                        nombre=nombre_permiso,
                        descripcion=(
                            f"Permiso para "
                            f"{nombre_permiso.replace('_', ' ')}"
                        ),
                    )
                )

        sesion.flush()

        # 3. Asignar los permisos al rol Administrador
        if rol_admin is not None:
            for nombre_permiso in PERMISOS_ADMIN:
                permiso = sesion.scalar(
                    select(Permiso).where(
                        Permiso.nombre == nombre_permiso
                    )
                )

                if permiso is not None:
                    asociacion = sesion.scalar(
                        select(RolPermiso)
                        .where(RolPermiso.id_rol == rol_admin.id)
                        .where(RolPermiso.id_permiso == permiso.id)
                    )

                    if asociacion is None:
                        sesion.add(
                            RolPermiso(
                                id_rol=rol_admin.id,
                                id_permiso=permiso.id,
                            )
                        )

        sesion.commit()

    except Exception:
        sesion.rollback()
        raise
from sqlalchemy import select, delete, update
from sqlalchemy.orm import Session

from app.models.usuario.rol import Rol
from app.models.usuario.permiso import Permiso
from app.models.usuario.rol_permiso import RolPermiso
from app.models.usuario.usuario import Usuario

ROLES_OFICIALES = ["ADMINISTRADOR", "USUARIO"]
PERMISOS_ADMIN = ["gestionar_usuarios", "administrar_planes", "ver_dashboard"]


def sembrar_roles(sesion: Session) -> None:
    """Crea los roles base, limpia roles obsoletos, y configura los permisos del sistema."""
    try:
        # 1. Asegurar la existencia de los dos roles oficiales
        for nombre_rol in ROLES_OFICIALES:
            rol_existente = sesion.scalar(select(Rol).where(Rol.nombre == nombre_rol))
            if not rol_existente:
                sesion.add(Rol(nombre=nombre_rol))
        sesion.flush()

        rol_usuario = sesion.scalar(select(Rol).where(Rol.nombre == "USUARIO"))
        rol_admin = sesion.scalar(select(Rol).where(Rol.nombre == "ADMINISTRADOR"))
        rol_cliente = sesion.scalar(select(Rol).where(Rol.nombre == "CLIENTE"))

        # 2. Migración: Si existe el rol CLIENTE obsoleto
        if rol_cliente is not None:
            # Reasignar usuarios asignados a CLIENTE hacia USUARIO
            if rol_usuario is not None:
                sesion.execute(
                    update(Usuario)
                    .where(Usuario.id_rol == rol_cliente.id)
                    .values(id_rol=rol_usuario.id)
                )

            # Eliminar mapeos de rol_permiso del rol CLIENTE
            sesion.execute(
                delete(RolPermiso).where(RolPermiso.id_rol == rol_cliente.id)
            )

            # Eliminar el rol CLIENTE
            sesion.execute(
                delete(Rol).where(Rol.id == rol_cliente.id)
            )
            sesion.flush()

        # 3. Sembrar Permisos
        for nombre_permiso in PERMISOS_ADMIN:
            permiso_existente = sesion.scalar(select(Permiso).where(Permiso.nombre == nombre_permiso))
            if not permiso_existente:
                sesion.add(
                    Permiso(
                        nombre=nombre_permiso,
                        descripcion=f"Permiso para {nombre_permiso.replace('_', ' ')}"
                    )
                )
        sesion.flush()

        # 4. Vincular todos los permisos administrativos al rol ADMINISTRADOR
        if rol_admin is not None:
            for nombre_permiso in PERMISOS_ADMIN:
                permiso = sesion.scalar(select(Permiso).where(Permiso.nombre == nombre_permiso))
                if permiso is not None:
                    asociacion = sesion.scalar(
                        select(RolPermiso)
                        .where(RolPermiso.id_rol == rol_admin.id)
                        .where(RolPermiso.id_permiso == permiso.id)
                    )
                    if not asociacion:
                        sesion.add(RolPermiso(id_rol=rol_admin.id, id_permiso=permiso.id))

        sesion.commit()
    except Exception as e:
        sesion.rollback()
        raise e

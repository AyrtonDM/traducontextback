from datetime import datetime, timezone
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.conexion import obtener_sesion
from app.models.usuario.usuario import Usuario
from app.models.usuario.sesion import Sesion
from app.models.usuario.rol_permiso import RolPermiso
from app.models.usuario.permiso import Permiso


def obtener_usuario_actual(
    authorization: str = Header(..., description="Token Bearer de autorizacion"),
    sesion_db: Session = Depends(obtener_sesion),
) -> Usuario:
    """Valida el token de sesion y retorna el usuario actual con su rol."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Formato de autorizacion invalido. Use 'Bearer <token>'.",
        )

    token = authorization.split(" ")[1]

    # Buscar sesion activa
    sesion_usuario = sesion_db.scalar(
        select(Sesion)
        .where(Sesion.token == token)
        .where(Sesion.estado == "ACTIVA")
    )

    if sesion_usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de sesion invalido o ya cerrado.",
        )

    # Verificar expiracion
    # Si la fecha de expiracion no tiene zona horaria, nos aseguramos de que coincida
    ahora = datetime.now(timezone.utc)
    if sesion_usuario.fecha_expiracion.tzinfo is None:
        ahora = ahora.replace(tzinfo=None)

    if sesion_usuario.fecha_expiracion < ahora:
        # Actualizar estado de la sesion a EXPIRADA
        sesion_usuario.estado = "EXPIRADA"
        sesion_db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La sesion ha expirado.",
        )

    # Buscar usuario
    usuario = sesion_db.scalar(
        select(Usuario)
        .where(Usuario.id == sesion_usuario.id_usuario)
        .where(Usuario.estado == "ACTIVO")
    )

    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inactivo o no encontrado.",
        )

    return usuario


def requiere_rol(*roles_permitidos: str):
    """Dependency factory para validar que el usuario tenga uno de los roles permitidos."""
    def dependencia(usuario: Usuario = Depends(obtener_usuario_actual)) -> Usuario:
        if usuario.rol.nombre not in roles_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos suficientes para realizar esta accion.",
            )
        return usuario
    return dependencia


def requiere_permiso(permiso_requerido: str):
    """Dependency factory para validar que el rol del usuario tenga el permiso requerido."""
    def dependencia(
        usuario: Usuario = Depends(obtener_usuario_actual),
        sesion_db: Session = Depends(obtener_sesion),
    ) -> Usuario:
        # Verificar si el rol del usuario tiene el permiso requerido
        tiene_permiso = sesion_db.scalar(
            select(RolPermiso)
            .join(Permiso)
            .where(RolPermiso.id_rol == usuario.id_rol)
            .where(Permiso.nombre == permiso_requerido)
        ) is not None

        if not tiene_permiso:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes los permisos necesarios para realizar esta accion.",
            )
        return usuario
    return dependencia

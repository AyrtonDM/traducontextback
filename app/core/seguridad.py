import secrets
import base64
import hashlib
from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.utilities.seguridad import ITERACIONES_HASH
from app.database.conexion import obtener_sesion
from app.models.usuario.usuario import Usuario
from app.models.usuario.rol_permiso import RolPermiso
from app.models.usuario.permiso import Permiso


def verificar_contrasena(contrasena: str, hash_almacenado: str) -> bool:
    """Verifica si la contraseña coincide con el hash almacenado."""
    try:
        partes = hash_almacenado.split("$")
        if len(partes) != 4 or partes[0] != "pbkdf2_sha256":
            return False

        iteraciones = int(partes[1])
        salt = base64.b64decode(partes[2].encode("ascii"))
        hash_original = base64.b64decode(partes[3].encode("ascii"))

        hash_calculado = hashlib.pbkdf2_hmac(
            "sha256",
            contrasena.encode("utf-8"),
            salt,
            iteraciones,
        )
        return secrets.compare_digest(hash_original, hash_calculado)
    except Exception:
        return False


def generar_token_sesion() -> str:
    """Genera un token seguro y único de sesión."""
    return secrets.token_urlsafe(64)


def requiere_rol(*roles_permitidos: str):
    """Dependency factory para validar que el usuario tenga uno de los roles permitidos."""
    # Importamos aqui para evitar dependencia circular
    from app.services.usuarios import obtener_usuario_actual
    
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
    # Importamos aqui para evitar dependencia circular
    from app.services.usuarios import obtener_usuario_actual
    
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

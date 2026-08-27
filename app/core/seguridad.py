import secrets
import base64
import hashlib
from app.utilities.seguridad import ITERACIONES_HASH


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

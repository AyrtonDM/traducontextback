import base64
import hashlib
import secrets


ITERACIONES_HASH = 260000


def hashear_contrasena(contrasena: str) -> str:
    """Genera un hash seguro para almacenar contrasenas."""

    salt = secrets.token_bytes(16)
    hash_contrasena = hashlib.pbkdf2_hmac(
        "sha256",
        contrasena.encode("utf-8"),
        salt,
        ITERACIONES_HASH,
    )

    salt_texto = base64.b64encode(salt).decode("ascii")
    hash_texto = base64.b64encode(hash_contrasena).decode("ascii")

    return f"pbkdf2_sha256${ITERACIONES_HASH}${salt_texto}${hash_texto}"


def generar_codigo_verificacion() -> str:
    """Genera un codigo numerico de 6 digitos."""

    return f"{secrets.randbelow(1000000):06d}"

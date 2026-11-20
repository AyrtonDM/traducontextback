"""
Cifrado simetrico (Fernet) para los tokens OAuth de las integraciones (HU-35) y para firmar el
parametro 'state' del flujo OAuth (protege contra CSRF y caduca). La clave viene de la variable de
entorno CLAVE_CIFRADO_TOKENS; nunca se guarda en el codigo.
"""

import json

from cryptography.fernet import Fernet, InvalidToken

from app.core.configuracion import configuracion


class IntegracionNoConfiguradaError(RuntimeError):
    """Falta la clave de cifrado o las credenciales OAuth de la plataforma."""


class EstadoOAuthInvalidoError(ValueError):
    """El 'state' de OAuth no es valido, fue alterado o caduco."""


def _fernet() -> Fernet:
    clave = (configuracion.clave_cifrado_tokens or "").strip()
    if not clave:
        raise IntegracionNoConfiguradaError(
            "Las integraciones no estan configuradas: falta CLAVE_CIFRADO_TOKENS en el servidor."
        )
    try:
        return Fernet(clave.encode())
    except (ValueError, TypeError) as error:
        raise IntegracionNoConfiguradaError("CLAVE_CIFRADO_TOKENS no es una clave Fernet valida.") from error


def cifrado_disponible() -> bool:
    try:
        _fernet()
        return True
    except IntegracionNoConfiguradaError:
        return False


def cifrar(texto: str) -> str:
    return _fernet().encrypt(texto.encode()).decode()


def descifrar(texto_cifrado: str) -> str:
    try:
        return _fernet().decrypt(texto_cifrado.encode()).decode()
    except InvalidToken as error:
        raise IntegracionNoConfiguradaError(
            "No se pudo descifrar un token guardado (¿cambio CLAVE_CIFRADO_TOKENS?). Vuelve a vincular la cuenta."
        ) from error


def firmar_estado(datos: dict) -> str:
    """Empaqueta y cifra datos para el 'state' de OAuth (incluye la marca de tiempo de Fernet)."""
    return cifrar(json.dumps(datos, separators=(",", ":")))


def leer_estado(estado: str, vigencia_segundos: int) -> dict:
    try:
        contenido = _fernet().decrypt(estado.encode(), ttl=vigencia_segundos)
        datos = json.loads(contenido)
    except (InvalidToken, ValueError) as error:
        raise EstadoOAuthInvalidoError(
            "La solicitud de autorizacion no es valida o caduco. Vuelve a intentarlo."
        ) from error
    if not isinstance(datos, dict):
        raise EstadoOAuthInvalidoError("La solicitud de autorizacion no es valida.")
    return datos

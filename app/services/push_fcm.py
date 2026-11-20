"""
Envio de notificaciones push con Firebase Cloud Messaging (M1).

Las credenciales se leen solo de la variable de entorno FIREBASE_CREDENCIALES (ruta al JSON de la
cuenta de servicio o el JSON completo). Si no esta definida, o si firebase-admin no esta instalado,
el envio se omite sin error: las notificaciones quedan guardadas en la base de datos igualmente.
"""

import json
import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.configuracion import RUTA_BASE, configuracion


logger = logging.getLogger(__name__)

NOMBRE_APP_FIREBASE = "traducontext"

_candado = threading.Lock()
_app_firebase: Any = None
_inicializacion_intentada = False


@dataclass
class ResultadoEnvioPush:
    enviados: int = 0
    fallidos: int = 0
    # Tokens que FCM ya no reconoce (app desinstalada, token rotado): se desactivan
    tokens_invalidos: list[str] = field(default_factory=list)


def _cargar_credenciales(valor: str):
    from firebase_admin import credentials

    valor = valor.strip()
    if valor.startswith("{"):
        return credentials.Certificate(json.loads(valor))
    ruta = Path(valor)
    if not ruta.is_absolute():
        # Rutas relativas a la raiz del backend, sin depender del directorio desde el que se arranque
        ruta = RUTA_BASE / ruta
    return credentials.Certificate(str(ruta))


def obtener_app_firebase() -> Any:
    """Inicializa Firebase una sola vez. Devuelve None si no hay credenciales o no se pudo."""
    global _app_firebase, _inicializacion_intentada

    if _inicializacion_intentada:
        return _app_firebase

    with _candado:
        if _inicializacion_intentada:
            return _app_firebase
        _inicializacion_intentada = True

        if not configuracion.firebase_credenciales.strip():
            logger.info("FIREBASE_CREDENCIALES no definida: las notificaciones push estan desactivadas.")
            return None
        try:
            import firebase_admin

            _app_firebase = firebase_admin.initialize_app(
                _cargar_credenciales(configuracion.firebase_credenciales),
                name=NOMBRE_APP_FIREBASE,
            )
        except ImportError:
            logger.warning("firebase-admin no esta instalado: las notificaciones push estan desactivadas.")
        except Exception:
            # Nunca se registra el contenido de la credencial
            logger.exception("No se pudo inicializar Firebase: las notificaciones push estan desactivadas.")
        return _app_firebase


def push_disponible() -> bool:
    return obtener_app_firebase() is not None


def enviar_a_tokens(
    tokens: list[str],
    titulo: str,
    cuerpo: str,
    datos: dict[str, str],
) -> ResultadoEnvioPush:
    """
    Envia la misma notificacion a varios dispositivos. No lanza excepciones por errores de FCM:
    devuelve cuantos se enviaron y que tokens son invalidos.
    """
    resultado = ResultadoEnvioPush()
    app = obtener_app_firebase()
    if app is None or not tokens:
        return resultado

    from firebase_admin import exceptions, messaging

    mensaje = messaging.MulticastMessage(
        tokens=tokens,
        notification=messaging.Notification(title=titulo, body=cuerpo),
        data=datos,
        android=messaging.AndroidConfig(priority="high"),
    )
    try:
        respuesta = messaging.send_each_for_multicast(mensaje, app=app)
    except exceptions.FirebaseError:
        logger.exception("Error de FCM al enviar la notificacion push.")
        resultado.fallidos = len(tokens)
        return resultado

    for token, envio in zip(tokens, respuesta.responses):
        if envio.success:
            resultado.enviados += 1
            continue
        resultado.fallidos += 1
        if isinstance(envio.exception, (messaging.UnregisteredError, messaging.SenderIdMismatchError)):
            resultado.tokens_invalidos.append(token)
        else:
            logger.warning("FCM rechazo un envio: %s", envio.exception)
    return resultado

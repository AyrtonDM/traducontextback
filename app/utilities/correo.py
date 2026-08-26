from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import json

from app.core.configuracion import configuracion


RESEND_EMAILS_URL = "https://api.resend.com/emails"


class CorreoNoConfiguradoError(RuntimeError):
    """Error lanzado cuando falta configuracion para enviar correos."""


class EnvioCorreoError(RuntimeError):
    """Error lanzado cuando Resend no acepta el envio del correo."""


def enviar_correo(
    *,
    destinatarios: str | list[str],
    asunto: str,
    html: str | None = None,
    texto: str | None = None,
    cc: str | list[str] | None = None,
    bcc: str | list[str] | None = None,
    responder_a: str | list[str] | None = None,
    encabezados: dict[str, str] | None = None,
    etiquetas: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Envia un correo usando Resend.

    Sirve para correos informativos, codigos de verificacion,
    recuperacion de cuentas y notificaciones futuras.
    """

    if not configuracion.api_key_resend:
        raise CorreoNoConfiguradoError("Falta configurar API_KEY_RESEND.")

    if html is None and texto is None:
        raise ValueError("El correo debe incluir contenido html o texto.")

    payload: dict[str, Any] = {
        "from": configuracion.correo_remitente,
        "to": destinatarios,
        "subject": asunto,
    }

    campos_opcionales = {
        "html": html,
        "text": texto,
        "cc": cc,
        "bcc": bcc,
        "reply_to": responder_a,
        "headers": encabezados,
        "tags": etiquetas,
    }

    payload.update(
        {
            clave: valor
            for clave, valor in campos_opcionales.items()
            if valor is not None
        }
    )

    solicitud = Request(
        RESEND_EMAILS_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {configuracion.api_key_resend}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(solicitud, timeout=15) as respuesta:
            cuerpo = respuesta.read().decode("utf-8")
    except HTTPError as error:
        detalle = error.read().decode("utf-8")
        raise EnvioCorreoError(
            f"Resend rechazo el correo: {error.code} {detalle}"
        ) from error
    except URLError as error:
        raise EnvioCorreoError(
            f"No se pudo conectar con Resend: {error.reason}"
        ) from error

    return json.loads(cuerpo) if cuerpo else {}

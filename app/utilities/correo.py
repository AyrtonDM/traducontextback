from email.message import EmailMessage
from smtplib import SMTP, SMTPException
from typing import Any

from app.core.configuracion import configuracion


class CorreoNoConfiguradoError(RuntimeError):
    """Error lanzado cuando falta configuracion para enviar correos."""


class EnvioCorreoError(RuntimeError):
    """Error lanzado cuando Gmail no permite enviar el correo."""


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
    """Envia un correo usando Gmail SMTP.

    Sirve para correos informativos, codigos de verificacion,
    recuperacion de cuentas y notificaciones futuras.
    """

    validar_configuracion_gmail()

    if html is None and texto is None:
        raise ValueError("El correo debe incluir contenido html o texto.")

    destinatarios_lista = normalizar_destinatarios(destinatarios)
    cc_lista = normalizar_destinatarios(cc)
    bcc_lista = normalizar_destinatarios(bcc)

    mensaje = construir_mensaje(
        destinatarios=destinatarios_lista,
        asunto=asunto,
        html=html,
        texto=texto,
        cc=cc_lista,
        responder_a=responder_a,
        encabezados=encabezados,
    )

    try:
        with SMTP(configuracion.gmail_host, configuracion.gmail_port, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(configuracion.gmail_usuario, configuracion.gmail_password)
            smtp.send_message(
                mensaje,
                to_addrs=destinatarios_lista + cc_lista + bcc_lista,
            )
    except (OSError, SMTPException) as error:
        raise EnvioCorreoError(
            f"No se pudo enviar el correo con Gmail: {error}"
        ) from error

    return {
        "destinatarios": destinatarios_lista,
        "cc": cc_lista,
        "bcc": bcc_lista,
        "etiquetas": etiquetas or [],
    }


def validar_configuracion_gmail() -> None:
    campos_requeridos = {
        "GMAIL_HOST": configuracion.gmail_host,
        "GMAIL_PORT": configuracion.gmail_port,
        "GMAIL_USUARIO": configuracion.gmail_usuario,
        "GMAIL_PASSWORD": configuracion.gmail_password,
        "GMAIL_REMITENTE": configuracion.gmail_remitente,
    }

    faltantes = [
        nombre
        for nombre, valor in campos_requeridos.items()
        if valor is None or str(valor).strip() == ""
    ]

    if faltantes:
        raise CorreoNoConfiguradoError(
            f"Falta configurar: {', '.join(faltantes)}."
        )


def construir_mensaje(
    *,
    destinatarios: list[str],
    asunto: str,
    html: str | None,
    texto: str | None,
    cc: list[str],
    responder_a: str | list[str] | None,
    encabezados: dict[str, str] | None,
) -> EmailMessage:
    mensaje = EmailMessage()
    mensaje["From"] = configuracion.gmail_remitente
    mensaje["To"] = ", ".join(destinatarios)
    mensaje["Subject"] = asunto

    if cc:
        mensaje["Cc"] = ", ".join(cc)

    if responder_a:
        mensaje["Reply-To"] = ", ".join(normalizar_destinatarios(responder_a))

    if encabezados:
        for nombre, valor in encabezados.items():
            mensaje[nombre] = valor

    if texto:
        mensaje.set_content(texto)
    else:
        mensaje.set_content("Este correo contiene contenido HTML.")

    if html:
        mensaje.add_alternative(html, subtype="html")

    return mensaje


def normalizar_destinatarios(
    destinatarios: str | list[str] | None,
) -> list[str]:
    if destinatarios is None:
        return []

    if isinstance(destinatarios, str):
        return [destinatarios]

    return destinatarios

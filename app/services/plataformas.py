"""
Definicion de Google Meet y Zoom: OAuth (HU-35), validacion de enlaces de reunion (HU-36) y consulta
de participantes (HU-40). Toda llamada HTTP pasa por `_peticion` para poder simularla en las pruebas.
"""

import logging
import re
from base64 import b64encode
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx

from app.core.configuracion import configuracion
from app.models.integracion.conexion_plataforma import PLATAFORMA_GOOGLE_MEET, PLATAFORMA_ZOOM

logger = logging.getLogger(__name__)

TIEMPO_MAXIMO_HTTP_SEGUNDOS = 10.0


class PlataformaNoSoportadaError(ValueError):
    """La plataforma indicada no es Google Meet ni Zoom."""


class ErrorPlataformaExterna(RuntimeError):
    """La plataforma externa rechazo la peticion o no respondio."""


@dataclass(frozen=True)
class Permiso:
    alcance: str
    descripcion: str


@dataclass(frozen=True)
class DefinicionPlataforma:
    plataforma: str
    nombre: str
    url_autorizacion: str
    url_token: str
    url_revocacion: str
    permisos: tuple[Permiso, ...]

    @property
    def client_id(self) -> str:
        return getattr(configuracion, f"{self._prefijo}_client_id", "") or ""

    @property
    def client_secret(self) -> str:
        return getattr(configuracion, f"{self._prefijo}_client_secret", "") or ""

    @property
    def redirect_uri(self) -> str:
        return getattr(configuracion, f"{self._prefijo}_redirect_uri", "") or ""

    @property
    def _prefijo(self) -> str:
        return "google" if self.plataforma == PLATAFORMA_GOOGLE_MEET else "zoom"

    @property
    def configurada(self) -> bool:
        return bool(self.client_id and self.client_secret and self.redirect_uri)


# Solo los permisos necesarios (HU-35): identificar la cuenta y leer datos/participantes de reuniones
PLATAFORMAS: dict[str, DefinicionPlataforma] = {
    PLATAFORMA_GOOGLE_MEET: DefinicionPlataforma(
        plataforma=PLATAFORMA_GOOGLE_MEET,
        nombre="Google Meet",
        url_autorizacion="https://accounts.google.com/o/oauth2/v2/auth",
        url_token="https://oauth2.googleapis.com/token",
        url_revocacion="https://oauth2.googleapis.com/revoke",
        permisos=(
            Permiso("openid", "Identificarte con tu cuenta de Google."),
            Permiso("email", "Ver tu correo electrónico para mostrar qué cuenta está vinculada."),
            Permiso(
                "https://www.googleapis.com/auth/meetings.space.readonly",
                "Consultar (solo lectura) los datos y participantes de tus reuniones de Meet.",
            ),
        ),
    ),
    PLATAFORMA_ZOOM: DefinicionPlataforma(
        plataforma=PLATAFORMA_ZOOM,
        nombre="Zoom",
        url_autorizacion="https://zoom.us/oauth/authorize",
        url_token="https://zoom.us/oauth/token",
        url_revocacion="https://zoom.us/oauth/revoke",
        permisos=(
            Permiso("user:read:user", "Ver tu perfil básico (correo) para mostrar qué cuenta está vinculada."),
            Permiso("meeting:read:meeting", "Consultar (solo lectura) los datos de tus reuniones de Zoom."),
            Permiso(
                "meeting:read:list_past_participants",
                "Ver los nombres de los participantes de tus reuniones.",
            ),
        ),
    ),
}


def obtener_plataforma(plataforma: str) -> DefinicionPlataforma:
    definicion = PLATAFORMAS.get(plataforma)
    if not definicion:
        raise PlataformaNoSoportadaError("Plataforma no soportada. Usa 'google_meet' o 'zoom'.")
    return definicion


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------


def _peticion(metodo: str, url: str, **kwargs) -> httpx.Response:
    """Unico punto de salida HTTP (se reemplaza en las pruebas)."""
    with httpx.Client(timeout=TIEMPO_MAXIMO_HTTP_SEGUNDOS) as cliente:
        return cliente.request(metodo, url, **kwargs)


def _basic(definicion: DefinicionPlataforma) -> str:
    credenciales = f"{definicion.client_id}:{definicion.client_secret}".encode()
    return "Basic " + b64encode(credenciales).decode()


def _json_o_error(respuesta: httpx.Response, accion: str) -> dict:
    if respuesta.status_code >= 400:
        logger.warning("%s fallo con HTTP %s: %s", accion, respuesta.status_code, respuesta.text[:300])
        raise ErrorPlataformaExterna(f"La plataforma rechazó la solicitud ({accion}).")
    try:
        return respuesta.json()
    except ValueError as error:
        raise ErrorPlataformaExterna(f"Respuesta inesperada de la plataforma ({accion}).") from error


# ---------------------------------------------------------------------------
# OAuth
# ---------------------------------------------------------------------------


@dataclass
class TokensOAuth:
    access_token: str
    refresh_token: str | None
    fecha_expiracion: datetime | None
    alcances: str | None


def url_autorizacion(definicion: DefinicionPlataforma, estado: str) -> str:
    parametros = {
        "response_type": "code",
        "client_id": definicion.client_id,
        "redirect_uri": definicion.redirect_uri,
        "state": estado,
    }
    if definicion.plataforma == PLATAFORMA_GOOGLE_MEET:
        parametros.update(
            scope=" ".join(p.alcance for p in definicion.permisos),
            access_type="offline",  # para recibir refresh_token
            prompt="consent",
            include_granted_scopes="true",
        )
    # En Zoom los permisos se definen en la app del Marketplace (no se envian en la URL)
    return f"{definicion.url_autorizacion}?{urlencode(parametros)}"


def _tokens_desde(datos: dict, refresh_anterior: str | None = None) -> TokensOAuth:
    access_token = datos.get("access_token")
    if not access_token:
        raise ErrorPlataformaExterna("La plataforma no devolvió un token de acceso.")
    expira_en = datos.get("expires_in")
    fecha_expiracion = (
        datetime.now(timezone.utc) + timedelta(seconds=int(expira_en)) if expira_en else None
    )
    return TokensOAuth(
        access_token=access_token,
        refresh_token=datos.get("refresh_token") or refresh_anterior,
        fecha_expiracion=fecha_expiracion,
        alcances=datos.get("scope"),
    )


def _solicitar_tokens(definicion: DefinicionPlataforma, formulario: dict) -> dict:
    if definicion.plataforma == PLATAFORMA_ZOOM:
        respuesta = _peticion(
            "POST", definicion.url_token, data=formulario, headers={"Authorization": _basic(definicion)}
        )
    else:
        respuesta = _peticion(
            "POST",
            definicion.url_token,
            data={**formulario, "client_id": definicion.client_id, "client_secret": definicion.client_secret},
        )
    return _json_o_error(respuesta, "obtener tokens")


def intercambiar_codigo(definicion: DefinicionPlataforma, codigo: str) -> TokensOAuth:
    datos = _solicitar_tokens(
        definicion,
        {"grant_type": "authorization_code", "code": codigo, "redirect_uri": definicion.redirect_uri},
    )
    return _tokens_desde(datos)


def refrescar_tokens(definicion: DefinicionPlataforma, refresh_token: str) -> TokensOAuth:
    datos = _solicitar_tokens(definicion, {"grant_type": "refresh_token", "refresh_token": refresh_token})
    return _tokens_desde(datos, refresh_anterior=refresh_token)


def revocar_token(definicion: DefinicionPlataforma, token: str) -> bool:
    """Revoca el token en la plataforma. Devuelve False si no se pudo (se elimina igual en local)."""
    try:
        if definicion.plataforma == PLATAFORMA_ZOOM:
            respuesta = _peticion(
                "POST", definicion.url_revocacion, data={"token": token}, headers={"Authorization": _basic(definicion)}
            )
        else:
            respuesta = _peticion("POST", definicion.url_revocacion, data={"token": token})
        return respuesta.status_code < 400
    except httpx.HTTPError:
        logger.warning("No se pudo revocar el token de %s", definicion.plataforma)
        return False


def obtener_cuenta(definicion: DefinicionPlataforma, access_token: str) -> str | None:
    """Correo (o nombre) de la cuenta vinculada; None si no se puede obtener."""
    url = (
        "https://openidconnect.googleapis.com/v1/userinfo"
        if definicion.plataforma == PLATAFORMA_GOOGLE_MEET
        else "https://api.zoom.us/v2/users/me"
    )
    try:
        datos = _json_o_error(
            _peticion("GET", url, headers={"Authorization": f"Bearer {access_token}"}), "consultar la cuenta"
        )
    except (ErrorPlataformaExterna, httpx.HTTPError):
        return None
    return datos.get("email") or datos.get("display_name") or datos.get("name")


# ---------------------------------------------------------------------------
# Enlaces de reunion (HU-36)
# ---------------------------------------------------------------------------

_MEET_CODIGO = r"([a-z]{3})-?([a-z]{4})-?([a-z]{3})"
_RE_MEET_URL = re.compile(rf"^(?:https?://)?meet\.google\.com/{_MEET_CODIGO}(?:[/?#].*)?$", re.IGNORECASE)
_RE_MEET_CODIGO = re.compile(rf"^{_MEET_CODIGO}$", re.IGNORECASE)
_RE_ZOOM_URL = re.compile(
    r"^(?:https?://)?(?:[\w-]+\.)?zoom\.us/(?:j|w|s|wc/join|wc)/(\d{9,11})(?:[/?#].*)?$", re.IGNORECASE
)
_RE_ZOOM_ID = re.compile(r"^\d[\d\s-]{7,14}\d$")


def normalizar_reunion(plataforma: str, enlace: str) -> str:
    """
    Valida que el enlace o identificador corresponda a la plataforma y devuelve la referencia
    normalizada: 'abc-defg-hij' en Meet y el ID numerico en Zoom. Lanza ValueError si no corresponde.
    """
    texto = (enlace or "").strip()
    nombre = obtener_plataforma(plataforma).nombre
    if not texto:
        raise ValueError(f"Indica el enlace o el identificador de la reunión de {nombre}.")

    if plataforma == PLATAFORMA_GOOGLE_MEET:
        coincidencia = _RE_MEET_URL.match(texto) or _RE_MEET_CODIGO.match(texto)
        if coincidencia:
            return "-".join(parte.lower() for parte in coincidencia.groups())
    else:
        coincidencia = _RE_ZOOM_URL.match(texto)
        if coincidencia:
            return coincidencia.group(1)
        if _RE_ZOOM_ID.match(texto):
            digitos = re.sub(r"\D", "", texto)
            if 9 <= len(digitos) <= 11:
                return digitos

    otra = next((d.nombre for p, d in PLATAFORMAS.items() if p != plataforma), "otra plataforma")
    if (plataforma == PLATAFORMA_ZOOM and (_RE_MEET_URL.match(texto) or _RE_MEET_CODIGO.match(texto))) or (
        plataforma == PLATAFORMA_GOOGLE_MEET and (_RE_ZOOM_URL.match(texto) or "zoom.us" in texto.lower())
    ):
        raise ValueError(f"El enlace corresponde a {otra}, no a {nombre}.")
    if plataforma == PLATAFORMA_GOOGLE_MEET:
        raise ValueError("El enlace no es de Google Meet. Ejemplo: https://meet.google.com/abc-defg-hij")
    raise ValueError("El enlace no es de Zoom. Ejemplo: https://zoom.us/j/12345678901 o el ID de 9 a 11 dígitos.")


def enlace_publico(plataforma: str, referencia: str) -> str:
    if plataforma == PLATAFORMA_GOOGLE_MEET:
        return f"https://meet.google.com/{referencia}"
    return f"https://zoom.us/j/{referencia}"


# ---------------------------------------------------------------------------
# Participantes (HU-40)
# ---------------------------------------------------------------------------


@dataclass
class ParticipantePlataforma:
    id_externo: str
    nombre: str


def _participantes_meet(access_token: str, codigo: str) -> list[ParticipantePlataforma]:
    cabeceras = {"Authorization": f"Bearer {access_token}"}
    registros = _json_o_error(
        _peticion(
            "GET",
            "https://meet.googleapis.com/v2/conferenceRecords",
            params={"filter": f'space.meeting_code="{codigo}"'},
            headers=cabeceras,
        ),
        "consultar la reunión",
    ).get("conferenceRecords", [])
    if not registros:
        return []
    # La conferencia en curso (sin hora de fin) o, si no hay, la mas reciente
    actual = next((r for r in registros if not r.get("endTime")), None) or max(
        registros, key=lambda r: r.get("startTime", "")
    )
    datos = _json_o_error(
        _peticion(
            "GET",
            f"https://meet.googleapis.com/v2/{actual['name']}/participants",
            params={"filter": "latest_end_time IS NULL"},
            headers=cabeceras,
        ),
        "consultar participantes",
    )
    participantes = []
    for p in datos.get("participants", []):
        usuario = p.get("signedinUser") or p.get("anonymousUser") or p.get("phoneUser") or {}
        nombre = usuario.get("displayName")
        if nombre:
            participantes.append(ParticipantePlataforma(id_externo=p.get("name", nombre), nombre=nombre))
    return participantes


def _participantes_zoom(access_token: str, id_reunion: str) -> list[ParticipantePlataforma]:
    cabeceras = {"Authorization": f"Bearer {access_token}"}
    respuesta = _peticion(
        "GET",
        f"https://api.zoom.us/v2/metrics/meetings/{id_reunion}/participants",
        params={"type": "live", "page_size": 100},
        headers=cabeceras,
    )
    if respuesta.status_code >= 400:
        # Sin plan con panel de metricas: se intenta con la reunion ya realizada
        respuesta = _peticion(
            "GET",
            f"https://api.zoom.us/v2/past_meetings/{id_reunion}/participants",
            params={"page_size": 100},
            headers=cabeceras,
        )
    datos = _json_o_error(respuesta, "consultar participantes")
    participantes = []
    for p in datos.get("participants", []):
        nombre = p.get("user_name") or p.get("name")
        identificador = p.get("participant_user_id") or p.get("user_id") or p.get("id") or nombre
        if nombre:
            participantes.append(ParticipantePlataforma(id_externo=str(identificador), nombre=nombre))
    return participantes


def consultar_participantes(plataforma: str, access_token: str, referencia: str) -> list[ParticipantePlataforma]:
    """Participantes que informa la plataforma (sin duplicados). Lanza ErrorPlataformaExterna si falla."""
    try:
        if plataforma == PLATAFORMA_GOOGLE_MEET:
            encontrados = _participantes_meet(access_token, referencia)
        else:
            encontrados = _participantes_zoom(access_token, referencia)
    except httpx.HTTPError as error:
        raise ErrorPlataformaExterna("No se pudo conectar con la plataforma.") from error
    unicos: dict[str, ParticipantePlataforma] = {}
    for participante in encontrados:
        unicos.setdefault(participante.id_externo, participante)
    return list(unicos.values())

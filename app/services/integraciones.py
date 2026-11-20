"""
HU-35 Conexion con plataformas: vincular y desvincular Google Meet y Zoom con OAuth. Los tokens se
guardan cifrados, nunca se devuelven al cliente y se revocan al desvincular.
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cifrado import (
    IntegracionNoConfiguradaError,
    cifrado_disponible,
    cifrar,
    descifrar,
    firmar_estado,
    leer_estado,
)
from app.models.integracion.conexion_plataforma import PLATAFORMAS as CODIGOS_PLATAFORMA
from app.models.integracion.conexion_plataforma import ConexionPlataforma
from app.schemas.integracion import PermisoPlataforma, PlataformaDetalle
from app.services import plataformas
from app.services.plataformas import DefinicionPlataforma, ErrorPlataformaExterna, obtener_plataforma

logger = logging.getLogger(__name__)

ESTADO_VINCULADA = "vinculada"
ESTADO_NO_VINCULADA = "no_vinculada"
ESTADO_EXPIRADA = "expirada"

# El usuario tiene 10 minutos para completar la autorizacion
VIGENCIA_ESTADO_OAUTH_SEGUNDOS = 600
# Margen para refrescar el token antes de que caduque
MARGEN_EXPIRACION = timedelta(minutes=2)


class ConexionNoVinculadaError(ValueError):
    """La plataforma no esta vinculada o su autorizacion expiro."""


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _permisos(definicion: DefinicionPlataforma) -> list[PermisoPlataforma]:
    return [PermisoPlataforma(alcance=p.alcance, descripcion=p.descripcion) for p in definicion.permisos]


def _verificar_configurada(definicion: DefinicionPlataforma) -> None:
    if not definicion.configurada or not cifrado_disponible():
        raise IntegracionNoConfiguradaError(
            f"La integración con {definicion.nombre} no está configurada en el servidor."
        )


def obtener_conexion(sesion: Session, id_usuario: int, plataforma: str) -> ConexionPlataforma | None:
    return sesion.scalar(
        select(ConexionPlataforma).where(
            ConexionPlataforma.id_usuario == id_usuario,
            ConexionPlataforma.plataforma == plataforma,
        )
    )


def estado_conexion(conexion: ConexionPlataforma | None) -> str:
    """Expirada: el token de acceso caduco y no hay refresh token para renovarlo."""
    if conexion is None:
        return ESTADO_NO_VINCULADA
    caducado = conexion.fecha_expiracion is not None and conexion.fecha_expiracion <= _ahora()
    if caducado and not conexion.refresh_token_cifrado:
        return ESTADO_EXPIRADA
    return ESTADO_VINCULADA


def armar_detalle(definicion: DefinicionPlataforma, conexion: ConexionPlataforma | None) -> PlataformaDetalle:
    return PlataformaDetalle(
        plataforma=definicion.plataforma,
        nombre=definicion.nombre,
        configurada=definicion.configurada and cifrado_disponible(),
        estado=estado_conexion(conexion),
        cuenta_externa=conexion.cuenta_externa if conexion else None,
        fecha_vinculacion=(conexion.fecha_actualizacion or conexion.fecha_creacion) if conexion else None,
        permisos=_permisos(definicion),
    )


def listar_plataformas(sesion: Session, id_usuario: int) -> list[PlataformaDetalle]:
    return [
        armar_detalle(plataformas.PLATAFORMAS[codigo], obtener_conexion(sesion, id_usuario, codigo))
        for codigo in CODIGOS_PLATAFORMA
    ]


# ---------------------------------------------------------------------------
# Autorizacion OAuth
# ---------------------------------------------------------------------------


def iniciar_autorizacion(id_usuario: int, plataforma: str) -> tuple[str, list[PermisoPlataforma]]:
    """URL de la pantalla oficial de autorizacion, con un 'state' firmado que identifica al usuario."""
    definicion = obtener_plataforma(plataforma)
    _verificar_configurada(definicion)
    estado = firmar_estado({"u": id_usuario, "p": plataforma, "n": secrets.token_urlsafe(12)})
    return plataformas.url_autorizacion(definicion, estado), _permisos(definicion)


def completar_autorizacion(sesion: Session, plataforma: str, codigo: str, estado: str) -> ConexionPlataforma:
    """
    Callback de OAuth: valida el 'state', canjea el codigo por tokens y los guarda cifrados.
    Si la cuenta ya estaba vinculada, se reemplazan los tokens.
    """
    definicion = obtener_plataforma(plataforma)
    _verificar_configurada(definicion)
    datos = leer_estado(estado, VIGENCIA_ESTADO_OAUTH_SEGUNDOS)
    if datos.get("p") != plataforma or not isinstance(datos.get("u"), int):
        raise ValueError("La solicitud de autorización no corresponde a esta plataforma.")
    id_usuario = datos["u"]

    tokens = plataformas.intercambiar_codigo(definicion, codigo)
    cuenta = plataformas.obtener_cuenta(definicion, tokens.access_token)

    conexion = obtener_conexion(sesion, id_usuario, plataforma)
    if conexion is None:
        conexion = ConexionPlataforma(id_usuario=id_usuario, plataforma=plataforma, access_token_cifrado="")
        sesion.add(conexion)
    else:
        conexion.fecha_actualizacion = _ahora()
    conexion.access_token_cifrado = cifrar(tokens.access_token)
    conexion.refresh_token_cifrado = cifrar(tokens.refresh_token) if tokens.refresh_token else None
    conexion.fecha_expiracion = tokens.fecha_expiracion
    conexion.alcances = tokens.alcances
    conexion.cuenta_externa = cuenta
    sesion.commit()
    return conexion


def desvincular(sesion: Session, id_usuario: int, plataforma: str) -> bool:
    """
    Revoca los tokens en la plataforma (si se puede) y los elimina. Devuelve si la revocacion remota
    fue confirmada; los tokens se eliminan siempre.
    """
    definicion = obtener_plataforma(plataforma)
    conexion = obtener_conexion(sesion, id_usuario, plataforma)
    if conexion is None:
        raise ConexionNoVinculadaError(f"{definicion.nombre} no está vinculada.")

    revocado = True
    for cifrado in (conexion.refresh_token_cifrado, conexion.access_token_cifrado):
        if not cifrado:
            continue
        try:
            revocado = plataformas.revocar_token(definicion, descifrar(cifrado)) and revocado
        except IntegracionNoConfiguradaError:
            revocado = False
    sesion.delete(conexion)
    sesion.commit()
    return revocado


def exigir_conexion_vinculada(sesion: Session, id_usuario: int, plataforma: str) -> ConexionPlataforma:
    """HU-36: no se configura ni se inicia una sesion con una plataforma no vinculada o expirada."""
    definicion = obtener_plataforma(plataforma)
    conexion = obtener_conexion(sesion, id_usuario, plataforma)
    estado = estado_conexion(conexion)
    if estado == ESTADO_NO_VINCULADA:
        raise ConexionNoVinculadaError(
            f"Primero vincula tu cuenta de {definicion.nombre} en Integraciones."
        )
    if estado == ESTADO_EXPIRADA:
        raise ConexionNoVinculadaError(
            f"La autorización de {definicion.nombre} expiró. Vuelve a vincular tu cuenta en Integraciones."
        )
    return conexion


def token_vigente(sesion: Session, conexion: ConexionPlataforma) -> str:
    """
    Token de acceso listo para usar; lo renueva con el refresh token si esta por caducar. Si la
    renovacion falla, la conexion queda 'expirada' y se lanza ConexionNoVinculadaError.
    """
    definicion = obtener_plataforma(conexion.plataforma)
    por_caducar = conexion.fecha_expiracion is not None and conexion.fecha_expiracion <= _ahora() + MARGEN_EXPIRACION
    if not por_caducar:
        return descifrar(conexion.access_token_cifrado)
    if not conexion.refresh_token_cifrado:
        raise ConexionNoVinculadaError(f"La autorización de {definicion.nombre} expiró.")
    try:
        tokens = plataformas.refrescar_tokens(definicion, descifrar(conexion.refresh_token_cifrado))
    except ErrorPlataformaExterna as error:
        logger.warning("No se pudo renovar el token de %s: %s", conexion.plataforma, error)
        conexion.refresh_token_cifrado = None
        conexion.fecha_expiracion = _ahora()
        sesion.commit()
        raise ConexionNoVinculadaError(
            f"La autorización de {definicion.nombre} expiró. Vuelve a vincular tu cuenta."
        ) from error
    conexion.access_token_cifrado = cifrar(tokens.access_token)
    conexion.refresh_token_cifrado = cifrar(tokens.refresh_token) if tokens.refresh_token else None
    conexion.fecha_expiracion = tokens.fecha_expiracion
    conexion.fecha_actualizacion = _ahora()
    sesion.commit()
    return tokens.access_token

import logging
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.cifrado import EstadoOAuthInvalidoError, IntegracionNoConfiguradaError
from app.core.configuracion import configuracion
from app.core.seguridad import requiere_token
from app.database.conexion import obtener_sesion
from app.models.usuario.usuario import Usuario
from app.schemas.integracion import (
    AutorizacionRespuesta,
    AutorizacionResultado,
    ListaPlataformasRespuesta,
    Plataforma,
    PlataformaRespuesta,
)
from app.services import plataformas
from app.services.integraciones import (
    ConexionNoVinculadaError,
    armar_detalle,
    completar_autorizacion,
    desvincular,
    iniciar_autorizacion,
    listar_plataformas,
)
from app.services.plataformas import ErrorPlataformaExterna

logger = logging.getLogger(__name__)

enrutador = APIRouter(prefix="/integraciones", tags=["integraciones"])

RESPUESTA_401 = {status.HTTP_401_UNAUTHORIZED: {"description": "El token es invalido, expiro o no fue enviado."}}


@enrutador.get(
    "",
    response_model=ListaPlataformasRespuesta,
    summary="Plataformas compatibles y estado de mis conexiones (requiere token)",
    description=(
        "Google Meet y Zoom con su estado (vinculada, no_vinculada, expirada), la cuenta vinculada y "
        "los permisos que se solicitan. Nunca devuelve tokens (HU-35)."
    ),
    responses=RESPUESTA_401,
)
def consultar_plataformas(
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> ListaPlataformasRespuesta:
    return ListaPlataformasRespuesta(
        mensaje="Plataformas obtenidas correctamente.",
        resultado=listar_plataformas(sesion, usuario.id),
    )


@enrutador.post(
    "/{plataforma}/autorizar",
    response_model=AutorizacionRespuesta,
    summary="Iniciar la vinculacion OAuth (requiere token)",
    description=(
        "Devuelve la URL de la pantalla oficial de autorizacion de la plataforma y los permisos que se "
        "pediran. El navegador debe abrir esa URL; al terminar, la plataforma vuelve al callback."
    ),
    responses={
        **RESPUESTA_401,
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "La plataforma no esta configurada en el servidor."},
    },
)
def autorizar(
    plataforma: Plataforma,
    usuario: Usuario = Depends(requiere_token),
) -> AutorizacionRespuesta:
    try:
        url, permisos = iniciar_autorizacion(usuario.id, plataforma)
    except IntegracionNoConfiguradaError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    return AutorizacionRespuesta(
        mensaje="Abre la pantalla de autorización para vincular tu cuenta.",
        resultado=AutorizacionResultado(plataforma=plataforma, url_autorizacion=url, permisos=permisos),
    )


def _volver_al_frontend(plataforma: str, resultado: str, mensaje: str) -> RedirectResponse:
    parametros = urlencode({"plataforma": plataforma, "resultado": resultado, "mensaje": mensaje})
    destino = f"{configuracion.frontend_url.rstrip('/')}/integraciones?{parametros}"
    return RedirectResponse(destino, status_code=status.HTTP_302_FOUND)


@enrutador.get(
    "/{plataforma}/callback",
    summary="Retorno de la autorizacion OAuth (lo abre la plataforma, no requiere token)",
    description=(
        "Valida el 'state' firmado, canjea el codigo por tokens y los guarda cifrados. Siempre redirige "
        "al frontend (/integraciones) con 'resultado' = vinculada, cancelada o error. Si la autorizacion "
        "falla o se cancela, no se vincula nada."
    ),
    response_class=RedirectResponse,
    status_code=status.HTTP_302_FOUND,
)
def callback(
    plataforma: Plataforma,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    sesion: Session = Depends(obtener_sesion),
) -> RedirectResponse:
    nombre = plataformas.obtener_plataforma(plataforma).nombre
    if error:
        return _volver_al_frontend(plataforma, "cancelada", f"Se canceló la autorización de {nombre}.")
    if not code or not state:
        return _volver_al_frontend(plataforma, "error", f"{nombre} no devolvió la autorización.")
    try:
        completar_autorizacion(sesion, plataforma, code, state)
    except EstadoOAuthInvalidoError as fallo:
        return _volver_al_frontend(plataforma, "error", str(fallo))
    except IntegracionNoConfiguradaError as fallo:
        return _volver_al_frontend(plataforma, "error", str(fallo))
    except (ErrorPlataformaExterna, ValueError) as fallo:
        sesion.rollback()
        logger.warning("No se pudo completar la vinculacion con %s: %s", plataforma, fallo)
        return _volver_al_frontend(plataforma, "error", f"No se pudo vincular {nombre}. Inténtalo de nuevo.")
    return _volver_al_frontend(plataforma, "vinculada", f"{nombre} se vinculó correctamente.")


@enrutador.delete(
    "/{plataforma}",
    response_model=PlataformaRespuesta,
    summary="Desvincular una plataforma (requiere token)",
    description="Revoca los tokens en la plataforma (si responde) y los elimina del sistema.",
    responses={**RESPUESTA_401, status.HTTP_404_NOT_FOUND: {"description": "La plataforma no estaba vinculada."}},
)
def desvincular_plataforma(
    plataforma: Plataforma,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> PlataformaRespuesta:
    definicion = plataformas.obtener_plataforma(plataforma)
    try:
        revocado = desvincular(sesion, usuario.id, plataforma)
    except ConexionNoVinculadaError as fallo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(fallo)) from fallo
    mensaje = f"{definicion.nombre} se desvinculó y sus tokens se eliminaron."
    if not revocado:
        mensaje += f" No se pudo confirmar la revocación en {definicion.nombre}; puedes quitar el acceso desde tu cuenta."
    return PlataformaRespuesta(mensaje=mensaje, resultado=armar_detalle(definicion, None))

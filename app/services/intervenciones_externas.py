"""
HU-37 Captura y HU-38 Traduccion de sesiones externas. Cada fragmento de audio de la reunion se
transcribe con Whisper y se traduce en el momento (sin esperar a que termine la reunion), en ambos
sentidos, con la configuracion de la sesion y las intervenciones anteriores como contexto.
Un fallo de traduccion deja la intervencion en 'error' sin detener el servicio.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.integracion.intervencion_externa import IntervencionExterna
from app.models.integracion.sesion_externa import ESTADO_ACTIVA, SesionExterna
from app.models.traduccion.idioma import Idioma
from app.schemas.sesion_externa import IntervencionExternaDetalle
from app.services.enriquecedor_traduccion import neutralizar_delimitadores
from app.services.sesiones_externas import (
    ParticipanteExternoNoEncontradoError,
    SesionExternaNoEncontradaError,
    obtener_sesion_externa,
)
from app.services.traduccion import detector_idioma
from app.services.traduccion_contextual import traducir_con_configuracion
from app.services.transcripcion import transcribir

logger = logging.getLogger(__name__)

ESTADO_PROCESANDO = "procesando"
ESTADO_TRADUCIDA = "traducida"
ESTADO_ERROR = "error"

TIEMPO_MAXIMO_LLM_SEGUNDOS = 6.0
UMBRAL_CONFIANZA_DETECCION = 0.5
MAX_INTERVENCIONES_HISTORIAL = 5
MAX_CARACTERES_LINEA = 500
MAX_CARACTERES_HISTORIAL = 1500
NOMBRE_SIN_IDENTIFICAR = "Sin identificar"

MENSAJE_IDIOMA_NO_IDENTIFICADO = "No se pudo identificar el idioma de la intervención; no se tradujo."
MENSAJE_ERROR_TRADUCCION = "No se pudo traducir la intervención. Puedes reintentarlo."

# Fragmentos admitidos (MediaRecorder de Chrome y Edge produce audio/webm)
TIPOS_AUDIO = {
    "audio/webm", "audio/ogg", "audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp4", "audio/m4a",
    "audio/x-m4a", "video/webm",
}
TAMANO_MAXIMO_AUDIO = 5 * 1024 * 1024


class IntervencionExternaNoEncontradaError(SesionExternaNoEncontradaError):
    """La intervencion no existe en una sesion externa del usuario."""


class ServicioNoActivoError(ValueError):
    """La sesion no esta activa: en pausa o finalizada no se captura ni se traduce (HU-41)."""


@dataclass
class _Parametros:
    id_usuario: int
    id_intervencion: int
    texto: str
    codigo_origen: str
    codigo_destino: str
    nombre_contexto: str | None
    descripcion_contexto: str | None
    nombre_tono: str | None
    nombre_entorno: str | None
    id_glosario: int | None
    historial: list[str]


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _consulta():
    return select(IntervencionExterna).options(
        selectinload(IntervencionExterna.participante),
        selectinload(IntervencionExterna.idioma_origen),
        selectinload(IntervencionExterna.idioma_destino),
    )


def armar_detalle_intervencion(i: IntervencionExterna) -> IntervencionExternaDetalle:
    return IntervencionExternaDetalle(
        id_intervencion=i.id_intervencion,
        id_sesion_externa=i.id_sesion_externa,
        id_participante=i.id_participante,
        nombre_participante=i.participante.nombre if i.participante else None,
        orden=i.orden,
        texto_original=i.texto_original,
        texto_traducido=i.texto_traducido,
        codigo_idioma_origen=i.idioma_origen.codigo if i.idioma_origen else None,
        codigo_idioma_destino=i.idioma_destino.codigo if i.idioma_destino else None,
        nombre_idioma_origen=i.idioma_origen.nombre if i.idioma_origen else None,
        nombre_idioma_destino=i.idioma_destino.nombre if i.idioma_destino else None,
        estado=i.estado,
        mensaje_error=i.mensaje_error,
        fecha_creacion=i.fecha_creacion,
        fecha_actualizacion=i.fecha_actualizacion,
    )


def _obtener(sesion: Session, id_sesion_externa: int, id_intervencion: int) -> IntervencionExterna:
    intervencion = sesion.scalar(
        _consulta().where(
            IntervencionExterna.id_intervencion == id_intervencion,
            IntervencionExterna.id_sesion_externa == id_sesion_externa,
        )
    )
    if not intervencion:
        raise IntervencionExternaNoEncontradaError("Intervención no encontrada en la sesión indicada.")
    return intervencion


# ---------------------------------------------------------------------------
# Idioma, historial y parametros
# ---------------------------------------------------------------------------


def _idiomas(sesion_externa: SesionExterna, texto: str, idioma_whisper: str | None) -> tuple[Idioma, Idioma] | None:
    """
    Sentido de la traduccion (HU-38): el idioma de la intervencion debe ser uno de los dos de la
    sesion y se traduce al otro. Primero el detector del proyecto; si no decide, el de Whisper.
    """
    par = {sesion_externa.idioma_origen.codigo: sesion_externa.idioma_origen,
           sesion_externa.idioma_destino.codigo: sesion_externa.idioma_destino}
    candidatos = []
    try:
        deteccion = detector_idioma.detectar(texto)
        if deteccion["confianza"] >= UMBRAL_CONFIANZA_DETECCION:
            candidatos.append(deteccion["codigo"])
    except Exception:  # noqa: BLE001
        logger.exception("No se pudo detectar el idioma de una intervención externa")
    if idioma_whisper:
        candidatos.append(idioma_whisper)
    for codigo in candidatos:
        if codigo in par:
            origen = par[codigo]
            destino = next(i for c, i in par.items() if c != codigo)
            return origen, destino
    return None


def _linea(i: IntervencionExterna) -> str:
    nombre = i.participante.nombre if i.participante else NOMBRE_SIN_IDENTIFICAR
    idioma = i.idioma_origen.nombre if i.idioma_origen else "?"
    linea = neutralizar_delimitadores(" ".join(f"{nombre} ({idioma}): {i.texto_original}".split()))
    if len(linea) > MAX_CARACTERES_LINEA:
        linea = linea[: MAX_CARACTERES_LINEA - 3].rstrip() + "..."
    return linea


def _historial(sesion: Session, id_sesion_externa: int, antes_de_orden: int) -> list[str]:
    """HU-38: ultimas intervenciones traducidas de la misma reunion, en orden cronologico."""
    previas = sesion.scalars(
        _consulta()
        .where(
            IntervencionExterna.id_sesion_externa == id_sesion_externa,
            IntervencionExterna.estado == ESTADO_TRADUCIDA,
            IntervencionExterna.orden < antes_de_orden,
        )
        .order_by(IntervencionExterna.orden.desc())
        .limit(MAX_INTERVENCIONES_HISTORIAL)
    ).all()
    lineas = [_linea(i) for i in reversed(previas)]
    while lineas and sum(len(l) for l in lineas) + len(lineas) - 1 > MAX_CARACTERES_HISTORIAL:
        lineas.pop(0)
    return lineas


def _parametros(sesion_externa: SesionExterna, intervencion: IntervencionExterna, origen: Idioma,
                destino: Idioma, historial: list[str]) -> _Parametros:
    contexto = sesion_externa.contexto
    descripciones = [contexto.descripcion if contexto else None, sesion_externa.descripcion_contexto]
    glosario = sesion_externa.glosario
    # El glosario solo se aplica en su sentido (como en las conversaciones, HU-32)
    id_glosario = (
        glosario.id_glosario
        if glosario and glosario.id_idioma_origen == origen.id_idioma and glosario.id_idioma_destino == destino.id_idioma
        else None
    )
    return _Parametros(
        id_usuario=sesion_externa.id_usuario,
        id_intervencion=intervencion.id_intervencion,
        texto=intervencion.texto_original,
        codigo_origen=origen.codigo,
        codigo_destino=destino.codigo,
        nombre_contexto=contexto.nombre if contexto else None,
        descripcion_contexto="\n".join(d for d in descripciones if d) or None,
        nombre_tono=sesion_externa.tono.nombre if sesion_externa.tono else None,
        nombre_entorno=sesion_externa.entorno.nombre if sesion_externa.entorno else None,
        id_glosario=id_glosario,
        historial=historial,
    )


def _traducir_y_guardar(sesion: Session, p: _Parametros) -> IntervencionExterna:
    texto_traducido, mensaje_error = None, None
    try:
        traduccion = traducir_con_configuracion(
            sesion=sesion,
            id_usuario=p.id_usuario,
            texto=p.texto,
            idioma_origen=p.codigo_origen,
            idioma_destino=p.codigo_destino,
            nombre_contexto=p.nombre_contexto,
            descripcion_contexto=p.descripcion_contexto,
            nombre_tono=p.nombre_tono,
            id_glosario=p.id_glosario,
            analizar_contexto=False,
            adaptar_estilo=bool(p.nombre_tono or p.nombre_contexto or p.descripcion_contexto or p.historial),
            tiempo_maximo_llm=TIEMPO_MAXIMO_LLM_SEGUNDOS,
            nombre_entorno=p.nombre_entorno,
            historial_conversacion=p.historial or None,
            aplicar_aprendizaje=True,
        )
        texto_traducido = traduccion.traduccion
    except ValueError as error:
        mensaje_error = str(error)
    except Exception:  # noqa: BLE001
        logger.exception("Error al traducir la intervención externa %s", p.id_intervencion)
        mensaje_error = MENSAJE_ERROR_TRADUCCION

    intervencion = sesion.get(IntervencionExterna, p.id_intervencion, populate_existing=True)
    if intervencion is None:
        sesion.rollback()
        raise IntervencionExternaNoEncontradaError("La intervención ya no existe.")
    intervencion.estado = ESTADO_ERROR if mensaje_error else ESTADO_TRADUCIDA
    intervencion.texto_traducido = texto_traducido
    intervencion.mensaje_error = mensaje_error
    intervencion.fecha_actualizacion = _ahora()
    sesion.commit()
    sesion.expire_all()
    return _obtener(sesion, intervencion.id_sesion_externa, intervencion.id_intervencion)


# ---------------------------------------------------------------------------
# Procesar audio
# ---------------------------------------------------------------------------


def _exigir_activa(sesion_externa: SesionExterna) -> None:
    if sesion_externa.estado != ESTADO_ACTIVA:
        raise ServicioNoActivoError(
            f"El servicio está {sesion_externa.estado}; no se captura ni se traduce contenido."
        )


def _contexto_para_whisper(sesion: Session, id_sesion_externa: int) -> str | None:
    ultimo = sesion.scalar(
        select(IntervencionExterna.texto_original)
        .where(IntervencionExterna.id_sesion_externa == id_sesion_externa)
        .order_by(IntervencionExterna.orden.desc())
        .limit(1)
    )
    return ultimo


def procesar_audio(
    sesion: Session,
    id_usuario: int,
    id_sesion_externa: int,
    contenido: bytes,
    nombre_archivo: str,
    tipo_contenido: str,
    id_participante: int | None = None,
) -> IntervencionExterna | None:
    """
    Transcribe un fragmento y, si tiene voz, lo registra y lo traduce. Devuelve None si no hubo voz.
    Si el servicio se pauso mientras se transcribia, el fragmento se descarta.
    """
    tipo_base = (tipo_contenido or "").split(";")[0].strip().lower()
    if tipo_base not in TIPOS_AUDIO:
        raise ValueError("Formato de audio no admitido. Envía audio webm, ogg, wav, mp3 o m4a.")
    if not contenido:
        raise ValueError("El fragmento de audio está vacío.")
    if len(contenido) > TAMANO_MAXIMO_AUDIO:
        raise ValueError("El fragmento de audio supera los 5 MB; envía fragmentos más cortos.")

    # 1. Validar sin bloquear y transcribir fuera de la transaccion (puede tardar varios segundos)
    sesion_externa = obtener_sesion_externa(sesion, id_usuario, id_sesion_externa)
    _exigir_activa(sesion_externa)
    if id_participante is not None and not any(
        p.id_participante == id_participante for p in sesion_externa.participantes
    ):
        raise ParticipanteExternoNoEncontradoError("Participante no encontrado en la sesión indicada.")
    contexto_previo = _contexto_para_whisper(sesion, id_sesion_externa)
    sesion.commit()

    transcripcion = transcribir(contenido, nombre_archivo or "fragmento.webm", tipo_base, contexto_previo)
    if not transcripcion.texto:
        return None

    # 2. Transaccion corta: bloquear la sesion, volver a exigir 'activa', asignar orden y guardar
    bloqueada = sesion.scalar(
        select(SesionExterna.estado)
        .where(SesionExterna.id_sesion_externa == id_sesion_externa, SesionExterna.id_usuario == id_usuario)
        .with_for_update()
    )
    if bloqueada is None:
        raise SesionExternaNoEncontradaError("Sesión externa no encontrada.")
    sesion_externa = obtener_sesion_externa(sesion, id_usuario, id_sesion_externa)
    _exigir_activa(sesion_externa)

    sentido = _idiomas(sesion_externa, transcripcion.texto, transcripcion.codigo_idioma)
    ultimo_orden = sesion.scalar(
        select(func.max(IntervencionExterna.orden)).where(IntervencionExterna.id_sesion_externa == id_sesion_externa)
    )
    intervencion = IntervencionExterna(
        id_sesion_externa=id_sesion_externa,
        id_participante=id_participante,
        orden=(ultimo_orden or 0) + 1,
        texto_original=transcripcion.texto,
        id_idioma_origen=sentido[0].id_idioma if sentido else None,
        id_idioma_destino=sentido[1].id_idioma if sentido else None,
        estado=ESTADO_PROCESANDO if sentido else ESTADO_ERROR,
        mensaje_error=None if sentido else MENSAJE_IDIOMA_NO_IDENTIFICADO,
    )
    sesion.add(intervencion)
    sesion.flush()

    if not sentido:
        # HU-38: se informa sin detener el servicio
        sesion.commit()
        return _obtener(sesion, id_sesion_externa, intervencion.id_intervencion)

    parametros = _parametros(
        sesion_externa, intervencion, sentido[0], sentido[1],
        _historial(sesion, id_sesion_externa, intervencion.orden),
    )
    sesion.commit()

    # 3. Traducir sin transaccion abierta y guardar el resultado
    return _traducir_y_guardar(sesion, parametros)


# ---------------------------------------------------------------------------
# Consultas y acciones sobre intervenciones
# ---------------------------------------------------------------------------


def listar_intervenciones(
    sesion: Session, id_usuario: int, id_sesion_externa: int, despues_de: int | None = None
) -> list[IntervencionExterna]:
    obtener_sesion_externa(sesion, id_usuario, id_sesion_externa)
    consulta = _consulta().where(IntervencionExterna.id_sesion_externa == id_sesion_externa)
    if despues_de is not None:
        referencia = sesion.scalar(
            select(IntervencionExterna.orden).where(
                IntervencionExterna.id_intervencion == despues_de,
                IntervencionExterna.id_sesion_externa == id_sesion_externa,
            )
        )
        if referencia is None:
            raise IntervencionExternaNoEncontradaError(
                "La intervención indicada en 'despues_de' no pertenece a la sesión."
            )
        consulta = consulta.where(IntervencionExterna.orden > referencia)
    return list(sesion.scalars(consulta.order_by(IntervencionExterna.orden.asc())).all())


def reintentar_intervencion(
    sesion: Session, id_usuario: int, id_sesion_externa: int, id_intervencion: int
) -> IntervencionExterna:
    """Vuelve a traducir una intervencion con error de traduccion (no las de idioma no identificado)."""
    sesion_externa = obtener_sesion_externa(sesion, id_usuario, id_sesion_externa)
    _exigir_activa(sesion_externa)
    intervencion = _obtener(sesion, id_sesion_externa, id_intervencion)
    if intervencion.estado != ESTADO_ERROR:
        raise ValueError(f"Solo se puede reintentar una intervención con error. Estado actual: {intervencion.estado}.")
    if not intervencion.idioma_origen or not intervencion.idioma_destino:
        raise ValueError("No se identificó el idioma de esta intervención; no se puede volver a traducir.")

    intervencion.estado = ESTADO_PROCESANDO
    intervencion.mensaje_error = None
    intervencion.fecha_actualizacion = _ahora()
    parametros = _parametros(
        sesion_externa, intervencion, intervencion.idioma_origen, intervencion.idioma_destino,
        _historial(sesion, id_sesion_externa, intervencion.orden),
    )
    sesion.commit()
    return _traducir_y_guardar(sesion, parametros)


def asignar_participante(
    sesion: Session, id_usuario: int, id_sesion_externa: int, id_intervencion: int, id_participante: int | None
) -> IntervencionExterna:
    """HU-40: el usuario indica quien hablo (o lo deja sin identificar)."""
    sesion_externa = obtener_sesion_externa(sesion, id_usuario, id_sesion_externa)
    if sesion_externa.estado == "finalizada":
        raise ValueError("La sesión está finalizada; no se puede modificar.")
    if id_participante is not None and not any(
        p.id_participante == id_participante for p in sesion_externa.participantes
    ):
        raise ParticipanteExternoNoEncontradoError("Participante no encontrado en la sesión indicada.")
    intervencion = _obtener(sesion, id_sesion_externa, id_intervencion)
    intervencion.id_participante = id_participante
    intervencion.fecha_actualizacion = _ahora()
    sesion.commit()
    sesion.expire_all()
    return _obtener(sesion, id_sesion_externa, id_intervencion)

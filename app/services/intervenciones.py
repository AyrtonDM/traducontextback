import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.conversacion.conversacion import Conversacion
from app.models.traduccion.idioma import Idioma
from app.models.conversacion.intervencion import (
    ESTADO_ERROR,
    ESTADO_PROCESANDO,
    ESTADO_TRADUCIDA,
    Intervencion,
)
from app.schemas.intervencion import CrearIntervencionSolicitud, IntervencionDetalle
from app.services.conversaciones import (
    ConversacionNoEncontradaError,
    ParticipanteNoEncontradoError,
    exigir_conversacion_activa,
    obtener_conversacion_usuario,
)
from app.services.enriquecedor_traduccion import neutralizar_delimitadores
from app.services.traduccion import detector_idioma
from app.services.traduccion_contextual import traducir_con_configuracion

logger = logging.getLogger(__name__)

# Espera maxima del modelo de lenguaje en conversaciones; al superarla se usa la traduccion de NLLB
TIEMPO_MAXIMO_LLM_CONVERSACION_SEGUNDOS = 6.0
# Una intervencion "procesando" sin cambios durante este tiempo se considera interrumpida y puede reintentarse
TIEMPO_PROCESANDO_INTERRUMPIDA = timedelta(minutes=2)

MENSAJE_ERROR_GENERICO = "No se pudo traducir la intervencion. Intenta de nuevo."

# HU-31/HU-26: una intervencion sin hablante solo se acepta si su idioma se detecta con esta confianza
UMBRAL_CONFIANZA_DETECCION = 0.7
MENSAJE_IDIOMA_NO_IDENTIFICADO = (
    "No se pudo identificar el idioma de la intervencion; selecciona quien habla."
)

# HU-29: historial de la conversacion que se envia como contexto al modelo de lenguaje
MAX_INTERVENCIONES_HISTORIAL = 5
# Tope por linea (una sola intervencion larga no puede ocupar todo el historial) y tope total
MAX_CARACTERES_LINEA_HISTORIAL = 500
MAX_CARACTERES_HISTORIAL = 1500
NOMBRE_NO_IDENTIFICADO = "No identificado"


class IntervencionNoEncontradaError(ConversacionNoEncontradaError):
    """La intervencion no existe en una conversacion del usuario autenticado."""


@dataclass
class _ParametrosTraduccion:
    """Datos necesarios para traducir, copiados antes de cerrar la transaccion."""

    id_usuario: int
    id_intervencion: int
    texto: str
    codigo_idioma_origen: str
    codigo_idioma_destino: str
    nombre_contexto: str | None
    descripcion_contexto: str | None
    nombre_tono: str | None
    adaptar_estilo: bool
    nombre_entorno: str | None = None
    # HU-29: None si 'mantener_contexto' esta apagado; lista vacia si no hay intervenciones previas
    historial_conversacion: list[str] | None = None


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _consulta_intervenciones():
    return select(Intervencion).options(
        selectinload(Intervencion.participante),
        selectinload(Intervencion.idioma_origen),
        selectinload(Intervencion.idioma_destino),
    )


def _obtener_intervencion(sesion: Session, id_conversacion: int, id_intervencion: int) -> Intervencion:
    intervencion = sesion.scalar(
        _consulta_intervenciones().where(
            Intervencion.id_intervencion == id_intervencion,
            Intervencion.id_conversacion == id_conversacion,
        )
    )
    if not intervencion:
        raise IntervencionNoEncontradaError(
            "Intervencion no encontrada en la conversacion indicada."
        )
    return intervencion


def _bloquear_conversacion(sesion: Session, id_usuario: int, id_conversacion: int) -> None:
    """Bloquea la fila de la conversacion hasta el commit (orden secuencial sin colisiones)."""
    bloqueada = sesion.scalar(
        select(Conversacion.id_conversacion)
        .where(
            Conversacion.id_conversacion == id_conversacion,
            Conversacion.id_usuario == id_usuario,
        )
        .with_for_update()
    )
    if bloqueada is None:
        raise ConversacionNoEncontradaError(
            "Conversacion no encontrada o no pertenece al usuario autenticado."
        )


def _linea_historial(intervencion: Intervencion) -> str:
    """'<nombre> (<idioma>): <texto original>' en una sola linea, sin delimitadores y truncada."""
    nombre = intervencion.participante.nombre if intervencion.participante else NOMBRE_NO_IDENTIFICADO
    idioma = intervencion.idioma_origen.nombre if intervencion.idioma_origen else "?"
    linea = " ".join(f"{nombre} ({idioma}): {intervencion.texto_original}".split())
    linea = neutralizar_delimitadores(linea)
    if len(linea) > MAX_CARACTERES_LINEA_HISTORIAL:
        linea = linea[: MAX_CARACTERES_LINEA_HISTORIAL - 3].rstrip() + "..."
    return linea


def _leer_historial(
    sesion: Session,
    conversacion: Conversacion,
    orden_actual: int,
) -> list[str] | None:
    """
    HU-29: ultimas intervenciones 'traducidas' de ESTA conversacion anteriores a `orden_actual`, en
    orden ascendente. Recorta las mas antiguas hasta quedar dentro del tope total de caracteres.
    Devuelve None si 'mantener_contexto' esta apagado (no se consulta la base de datos).
    """
    if not conversacion.mantener_contexto:
        return None

    previas = sesion.scalars(
        _consulta_intervenciones()
        .where(
            Intervencion.id_conversacion == conversacion.id_conversacion,
            Intervencion.estado == ESTADO_TRADUCIDA,
            Intervencion.orden < orden_actual,
        )
        .order_by(Intervencion.orden.desc())
        .limit(MAX_INTERVENCIONES_HISTORIAL)
    ).all()
    lineas = [_linea_historial(intervencion) for intervencion in reversed(previas)]

    # Las lineas se unen con salto de linea en el prompt: se cuenta un caracter por separador
    while lineas and _caracteres_historial(lineas) > MAX_CARACTERES_HISTORIAL:
        lineas.pop(0)
    return lineas


def _caracteres_historial(lineas: list[str]) -> int:
    return sum(len(linea) for linea in lineas) + max(len(lineas) - 1, 0)


def _registrar_uso_historial(id_intervencion: int, historial: list[str] | None) -> None:
    if historial is None:
        logger.info("Intervencion %s: historial omitido (interruptor apagado)", id_intervencion)
    elif not historial:
        logger.info("Intervencion %s: historial omitido (sin previas)", id_intervencion)
    else:
        logger.info(
            "Intervencion %s: historial usado (%d, %d caracteres)",
            id_intervencion,
            len(historial),
            _caracteres_historial(historial),
        )


def _parametros_traduccion(
    conversacion: Conversacion,
    intervencion: Intervencion,
    codigo_idioma_origen: str,
    codigo_idioma_destino: str,
    historial: list[str] | None = None,
) -> _ParametrosTraduccion:
    """
    Configuracion de la sesion para la traduccion central. El entorno (HU-24), las descripciones y el
    historial (HU-29) se envian como contexto; el modelo de lenguaje solo se usa si la sesion tiene
    tono, contexto, descripcion personalizada o historial (NLLB no puede usar contexto).
    """
    contexto = conversacion.contexto
    nombre_tono = conversacion.tono.nombre if conversacion.tono else None
    descripciones = [
        contexto.descripcion if contexto else None,
        conversacion.descripcion_contexto,
    ]
    descripcion = "\n".join(d for d in descripciones if d) or None
    adaptar_estilo = bool(
        nombre_tono or contexto or conversacion.descripcion_contexto or historial
    )

    return _ParametrosTraduccion(
        id_usuario=conversacion.id_usuario,
        id_intervencion=intervencion.id_intervencion,
        texto=intervencion.texto_original,
        codigo_idioma_origen=codigo_idioma_origen,
        codigo_idioma_destino=codigo_idioma_destino,
        nombre_contexto=contexto.nombre if contexto else None,
        descripcion_contexto=descripcion,
        nombre_tono=nombre_tono,
        adaptar_estilo=adaptar_estilo,
        nombre_entorno=conversacion.entorno.nombre if conversacion.entorno else None,
        historial_conversacion=historial,
    )


def _idiomas_por_deteccion(conversacion: Conversacion, texto: str) -> tuple[Idioma, Idioma]:
    """
    Intervencion sin hablante (HU-31): detecta el idioma y lo exige igual a uno de los dos de la
    sesion con confianza suficiente. Devuelve (origen, destino); el destino es el otro idioma.
    """
    try:
        deteccion = detector_idioma.detectar(texto)
    except Exception:
        logger.exception("No se pudo detectar el idioma de una intervencion sin hablante")
        raise ValueError(MENSAJE_IDIOMA_NO_IDENTIFICADO)

    codigo = deteccion["codigo"]
    confianza = deteccion["confianza"]
    logger.info(
        "Conversacion %s: idioma detectado '%s' con confianza %.2f",
        conversacion.id_conversacion,
        codigo,
        confianza,
    )
    if confianza < UMBRAL_CONFIANZA_DETECCION:
        raise ValueError(MENSAJE_IDIOMA_NO_IDENTIFICADO)

    idioma_1, idioma_2 = conversacion.idioma_origen, conversacion.idioma_destino
    if idioma_1 and codigo == idioma_1.codigo:
        return idioma_1, idioma_2
    if idioma_2 and codigo == idioma_2.codigo:
        return idioma_2, idioma_1
    raise ValueError(MENSAJE_IDIOMA_NO_IDENTIFICADO)


def _traducir_y_guardar(sesion: Session, parametros: _ParametrosTraduccion) -> Intervencion:
    """
    Traduce fuera de cualquier transaccion (la intervencion ya esta guardada como 'procesando') y
    guarda el resultado en una transaccion corta. Un error de traduccion deja la intervencion en
    'error' sin interrumpir la sesion.
    """
    texto_traducido = None
    mensaje_error = None
    try:
        traduccion = traducir_con_configuracion(
            sesion=sesion,
            id_usuario=parametros.id_usuario,
            texto=parametros.texto,
            idioma_origen=parametros.codigo_idioma_origen,
            idioma_destino=parametros.codigo_idioma_destino,
            nombre_contexto=parametros.nombre_contexto,
            descripcion_contexto=parametros.descripcion_contexto,
            nombre_tono=parametros.nombre_tono,
            analizar_contexto=False,
            adaptar_estilo=parametros.adaptar_estilo,
            tiempo_maximo_llm=TIEMPO_MAXIMO_LLM_CONVERSACION_SEGUNDOS,
            nombre_entorno=parametros.nombre_entorno,
            historial_conversacion=parametros.historial_conversacion,
        )
        texto_traducido = traduccion.traduccion
        if parametros.adaptar_estilo and not traduccion.estilo_aplicado:
            logger.info(
                "Intervencion %s: no se aplico el estilo; se usa la traduccion base (NLLB).",
                parametros.id_intervencion,
            )
    except ValueError as error:
        mensaje_error = str(error)
    except Exception:
        logger.exception("Error al traducir la intervencion %s", parametros.id_intervencion)
        mensaje_error = MENSAJE_ERROR_GENERICO

    # populate_existing: se relee la fila por si la conversacion se elimino mientras se traducia
    intervencion = sesion.get(Intervencion, parametros.id_intervencion, populate_existing=True)
    if intervencion is None:
        sesion.rollback()
        raise IntervencionNoEncontradaError("La intervencion ya no existe.")

    intervencion.estado = ESTADO_ERROR if mensaje_error else ESTADO_TRADUCIDA
    intervencion.texto_traducido = texto_traducido
    intervencion.mensaje_error = mensaje_error
    intervencion.fecha_actualizacion = _ahora()
    sesion.commit()
    sesion.expire_all()
    return _obtener_intervencion(sesion, intervencion.id_conversacion, intervencion.id_intervencion)


def armar_detalle_intervencion(intervencion: Intervencion) -> IntervencionDetalle:
    participante = intervencion.participante
    return IntervencionDetalle(
        id_intervencion=intervencion.id_intervencion,
        id_conversacion=intervencion.id_conversacion,
        id_participante=intervencion.id_participante,
        nombre_participante=participante.nombre if participante else None,
        orden_participante=participante.orden if participante else None,
        orden=intervencion.orden,
        texto_original=intervencion.texto_original,
        texto_traducido=intervencion.texto_traducido,
        id_idioma_origen=intervencion.id_idioma_origen,
        id_idioma_destino=intervencion.id_idioma_destino,
        codigo_idioma_origen=intervencion.idioma_origen.codigo if intervencion.idioma_origen else None,
        codigo_idioma_destino=intervencion.idioma_destino.codigo if intervencion.idioma_destino else None,
        nombre_idioma_origen=intervencion.idioma_origen.nombre if intervencion.idioma_origen else None,
        nombre_idioma_destino=intervencion.idioma_destino.nombre if intervencion.idioma_destino else None,
        estado=intervencion.estado,
        mensaje_error=intervencion.mensaje_error,
        fecha_creacion=intervencion.fecha_creacion,
        fecha_actualizacion=intervencion.fecha_actualizacion,
    )


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------


def listar_intervenciones(
    sesion: Session,
    id_usuario: int,
    id_conversacion: int,
    despues_de: int | None = None,
) -> list[Intervencion]:
    """
    Intervenciones de una conversacion del usuario en orden ascendente (cualquier estado de la sesion).
    Con `despues_de` (id de una intervencion de la misma conversacion) solo devuelve las posteriores.
    """
    obtener_conversacion_usuario(sesion, id_usuario, id_conversacion)

    consulta = _consulta_intervenciones().where(Intervencion.id_conversacion == id_conversacion)
    if despues_de is not None:
        orden_referencia = sesion.scalar(
            select(Intervencion.orden).where(
                Intervencion.id_intervencion == despues_de,
                Intervencion.id_conversacion == id_conversacion,
            )
        )
        if orden_referencia is None:
            raise IntervencionNoEncontradaError(
                "La intervencion indicada en 'despues_de' no pertenece a la conversacion."
            )
        consulta = consulta.where(Intervencion.orden > orden_referencia)

    return list(sesion.scalars(consulta.order_by(Intervencion.orden.asc())).all())


# ---------------------------------------------------------------------------
# Crear y reintentar
# ---------------------------------------------------------------------------


def crear_intervencion(
    sesion: Session,
    id_usuario: int,
    id_conversacion: int,
    datos: CrearIntervencionSolicitud,
) -> Intervencion:
    """
    Registra la intervencion del participante que habla y la traduce al idioma del otro participante.
    Origen = idioma del participante que habla; destino = idioma del otro participante.
    """
    # 1. Transaccion corta: validar, bloquear la conversacion, asignar orden y guardar "procesando"
    _bloquear_conversacion(sesion, id_usuario, id_conversacion)
    conversacion = exigir_conversacion_activa(sesion, id_usuario, id_conversacion)

    if datos.id_participante is not None:
        # Hablante elegido: se usa su idioma y no se detecta
        hablante = next(
            (p for p in conversacion.participantes if p.id_participante == datos.id_participante),
            None,
        )
        if not hablante:
            raise ParticipanteNoEncontradoError(
                "Participante no encontrado en la conversacion indicada."
            )
        oyente = next(
            (p for p in conversacion.participantes if p.id_participante != hablante.id_participante),
            None,
        )
        if not oyente:
            raise ValueError("La conversacion no tiene otro participante al que traducir.")
        id_participante = hablante.id_participante
        idioma_origen, idioma_destino = hablante.idioma, oyente.idioma
    else:
        # "No identificado": el sentido de la traduccion sale del idioma detectado
        id_participante = None
        idioma_origen, idioma_destino = _idiomas_por_deteccion(conversacion, datos.texto)

    ultimo_orden = sesion.scalar(
        select(func.max(Intervencion.orden)).where(Intervencion.id_conversacion == id_conversacion)
    )
    intervencion = Intervencion(
        id_conversacion=id_conversacion,
        id_participante=id_participante,
        orden=(ultimo_orden or 0) + 1,
        texto_original=datos.texto,
        id_idioma_origen=idioma_origen.id_idioma,
        id_idioma_destino=idioma_destino.id_idioma,
        estado=ESTADO_PROCESANDO,
    )
    sesion.add(intervencion)
    sesion.flush()

    # HU-29: el historial se lee dentro de esta transaccion corta, antes del commit
    historial = _leer_historial(sesion, conversacion, intervencion.orden)
    _registrar_uso_historial(intervencion.id_intervencion, historial)
    parametros = _parametros_traduccion(
        conversacion,
        intervencion,
        codigo_idioma_origen=idioma_origen.codigo,
        codigo_idioma_destino=idioma_destino.codigo,
        historial=historial,
    )
    # El commit libera el bloqueo antes de traducir
    sesion.commit()

    # 2. Traduccion sin transaccion abierta y 3. guardado del resultado
    return _traducir_y_guardar(sesion, parametros)


def reintentar_intervencion(
    sesion: Session,
    id_usuario: int,
    id_conversacion: int,
    id_intervencion: int,
) -> Intervencion:
    """
    Vuelve a traducir una intervencion en 'error', o en 'procesando' si quedo interrumpida.
    Usa la configuracion actual de la sesion, que debe estar activa.
    """
    conversacion = exigir_conversacion_activa(sesion, id_usuario, id_conversacion)

    intervencion = sesion.scalar(
        select(Intervencion)
        .where(
            Intervencion.id_intervencion == id_intervencion,
            Intervencion.id_conversacion == id_conversacion,
        )
        .with_for_update()
    )
    if not intervencion:
        raise IntervencionNoEncontradaError(
            "Intervencion no encontrada en la conversacion indicada."
        )

    ultima_modificacion = intervencion.fecha_actualizacion or intervencion.fecha_creacion
    interrumpida = (
        intervencion.estado == ESTADO_PROCESANDO
        and ultima_modificacion < _ahora() - TIEMPO_PROCESANDO_INTERRUMPIDA
    )
    if intervencion.estado != ESTADO_ERROR and not interrumpida:
        raise ValueError(
            f"Solo se puede reintentar una intervencion con error. Estado actual: {intervencion.estado}."
        )

    intervencion.estado = ESTADO_PROCESANDO
    intervencion.texto_traducido = None
    intervencion.mensaje_error = None
    intervencion.fecha_actualizacion = _ahora()

    # HU-29: solo intervenciones anteriores a la que se reintenta, leidas antes del commit
    historial = _leer_historial(sesion, conversacion, intervencion.orden)
    _registrar_uso_historial(intervencion.id_intervencion, historial)
    parametros = _parametros_traduccion(
        conversacion,
        intervencion,
        codigo_idioma_origen=intervencion.idioma_origen.codigo,
        codigo_idioma_destino=intervencion.idioma_destino.codigo,
        historial=historial,
    )
    sesion.commit()

    return _traducir_y_guardar(sesion, parametros)

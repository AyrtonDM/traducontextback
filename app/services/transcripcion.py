"""
HU-37: transcripcion con Whisper (OpenAI) de los fragmentos de audio capturados de una reunion.
Reutiliza el cliente de OpenAI del enriquecedor (misma OPENAI_API_KEY).
"""

import logging
import re
from dataclasses import dataclass

from app.services.traduccion_contextual import enriquecedor_traduccion

logger = logging.getLogger(__name__)

MODELO_TRANSCRIPCION = "whisper-1"
TIEMPO_MAXIMO_TRANSCRIPCION_SEGUNDOS = 30.0
# Un segmento con esta probabilidad de "no hay voz" o mas se descarta
UMBRAL_SIN_VOZ = 0.6
# Ultimos caracteres de la reunion que se pasan a Whisper para dar continuidad (nombres, terminos)
MAX_CARACTERES_PROMPT = 200

# Whisper devuelve el idioma por nombre en ingles
IDIOMAS_WHISPER = {
    "english": "en", "spanish": "es", "french": "fr", "portuguese": "pt", "german": "de",
    "italian": "it", "japanese": "ja", "chinese": "zh", "korean": "ko", "russian": "ru",
    "arabic": "ar", "dutch": "nl", "catalan": "ca", "hindi": "hi", "turkish": "tr", "polish": "pl",
}

# Frases que Whisper suele "inventar" ante silencio o musica
_ALUCINACIONES = re.compile(
    r"^\W*(gracias por ver( el v[ií]deo)?|subt[ií]tulos (realizados )?por la comunidad de amara\.org|"
    r"thanks? (you )?for watching|thank you\.?|suscr[ií]bete.*|\.+|…+)\W*$",
    re.IGNORECASE,
)


class TranscripcionError(RuntimeError):
    """Whisper no respondio o fallo."""


@dataclass
class Transcripcion:
    texto: str
    # Codigo ISO del idioma detectado por Whisper, si se pudo mapear
    codigo_idioma: str | None


def _campo(objeto, nombre: str):
    return objeto.get(nombre) if isinstance(objeto, dict) else getattr(objeto, nombre, None)


def transcribir(contenido: bytes, nombre_archivo: str, tipo_contenido: str, contexto_previo: str | None = None) -> Transcripcion:
    """Devuelve el texto transcrito ('' si no hay voz). Lanza TranscripcionError si Whisper falla."""
    parametros = {
        "model": MODELO_TRANSCRIPCION,
        "file": (nombre_archivo, contenido, tipo_contenido),
        "response_format": "verbose_json",
    }
    if contexto_previo:
        parametros["prompt"] = contexto_previo[-MAX_CARACTERES_PROMPT:]
    try:
        cliente = enriquecedor_traduccion.cliente.with_options(timeout=TIEMPO_MAXIMO_TRANSCRIPCION_SEGUNDOS)
        respuesta = cliente.audio.transcriptions.create(**parametros)
    except Exception as error:  # noqa: BLE001
        logger.warning("Fallo la transcripcion con Whisper: %s", error)
        raise TranscripcionError("No se pudo transcribir el audio de la reunión.") from error

    segmentos = _campo(respuesta, "segments") or []
    if segmentos:
        con_voz = [s for s in segmentos if (_campo(s, "no_speech_prob") or 0) < UMBRAL_SIN_VOZ]
        texto = " ".join((_campo(s, "text") or "").strip() for s in con_voz)
    else:
        texto = _campo(respuesta, "text") or ""
    texto = " ".join(texto.split())
    if not texto or _ALUCINACIONES.match(texto):
        texto = ""

    idioma = (_campo(respuesta, "language") or "").strip().lower()
    return Transcripcion(texto=texto, codigo_idioma=IDIOMAS_WHISPER.get(idioma, idioma if len(idioma) == 2 else None))

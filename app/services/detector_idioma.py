import os
import logging
from app.constants.idiomas import IDIOMAS

logger = logging.getLogger(__name__)

try:
    import fasttext
except ImportError:
    fasttext = None

try:
    from langdetect import detect_langs
except ImportError:
    detect_langs = None

# Palabras cortas muy comunes cuyo idioma se conoce con certeza
PALABRAS_CONOCIDAS: dict[str, str] = {
    # Inglés
    "hello": "en", "hi": "en", "hey": "en", "yes": "en", "no": "en",
    "ok": "en", "okay": "en", "bye": "en", "good": "en", "bad": "en",
    "the": "en", "and": "en", "for": "en", "are": "en", "you": "en",
    "this": "en", "that": "en", "with": "en", "have": "en", "from": "en",
    # Español
    "hola": "es", "si": "es", "sí": "es", "no": "es", "bien": "es",
    "mal": "es", "adiós": "es", "adios": "es", "gracias": "es",
    "por favor": "es", "buenos días": "es", "buenas": "es",
    # Portugués
    "olá": "pt", "ola": "pt", "sim": "pt", "obrigado": "pt", "tchau": "pt",
    # Francés
    "bonjour": "fr", "merci": "fr", "oui": "fr", "non": "fr", "salut": "fr",
    # Alemán
    "hallo": "de", "ja": "de", "nein": "de", "danke": "de", "bitte": "de",
    # Italiano
    "ciao": "it", "grazie": "it", "prego": "it", "buongiorno": "it",
}

# Umbral mínimo de confianza para aceptar detección
CONFIANZA_MINIMA = 0.55
# Mínimo de caracteres para activar detector de modelo
MIN_CARACTERES = 8


class DetectorIdioma:

    def __init__(self, ruta_modelo: str = "app/models_ia/detector_idioma/lid.176.ftz"):
        self.ruta_modelo = ruta_modelo
        self.modelo = None
        if fasttext and os.path.exists(ruta_modelo):
            try:
                self.modelo = fasttext.load_model(ruta_modelo)
            except Exception as e:
                logger.warning(f"No se pudo cargar fasttext: {e}")
                self.modelo = None

    def detectar(self, texto: str) -> dict:
        texto = texto.strip()

        if not texto:
            raise ValueError("El texto no puede estar vacio.")

        # 1. Revisar si el texto (o alguna frase inicial) está en el diccionario de palabras conocidas
        texto_lower = texto.lower()
        for frase, codigo in PALABRAS_CONOCIDAS.items():
            if texto_lower == frase or texto_lower.startswith(frase + " "):
                return {
                    "codigo": codigo,
                    "nombre": IDIOMAS.get(codigo, "Idioma desconocido"),
                    "confianza": 0.99
                }

        # 2. Para textos muy cortos, aumentar el umbral de confianza requerido
        confianza_requerida = CONFIANZA_MINIMA
        if len(texto) < MIN_CARACTERES:
            confianza_requerida = 0.85  # Más estricto con textos cortos

        if self.modelo and len(texto) >= 3:
            try:
                idiomas, probabilidades = self.modelo.predict(texto, k=3)
                codigo = idiomas[0].replace("__label__", "")
                confianza = float(probabilidades[0])

                if confianza >= confianza_requerida:
                    return {
                        "codigo": codigo,
                        "nombre": IDIOMAS.get(codigo, "Idioma desconocido"),
                        "confianza": confianza
                    }
                else:
                    logger.debug(f"Confianza insuficiente ({confianza:.2f}) para '{texto}', se omite")
            except Exception as e:
                logger.warning(f"Error en prediccion fasttext: {e}")

        if detect_langs and len(texto) >= 5:
            try:
                resultados = detect_langs(texto)
                if resultados:
                    mejor = resultados[0]
                    codigo = str(mejor.lang)
                    confianza = float(mejor.prob)
                    if confianza >= confianza_requerida:
                        return {
                            "codigo": codigo,
                            "nombre": IDIOMAS.get(codigo, "Idioma desconocido"),
                            "confianza": confianza
                        }
            except Exception as e:
                logger.warning(f"Error en deteccion con langdetect: {e}")

        # 3. Fallback: no se pudo detectar con suficiente confianza
        return {
            "codigo": "desconocido",
            "nombre": "No detectado",
            "confianza": 0.0
        }


detector_idioma = DetectorIdioma()
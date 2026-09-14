import logging
from openai import OpenAI
from pydantic import BaseModel, Field

from app.constants.idiomas import IDIOMAS
from app.core.configuracion import configuracion

logger = logging.getLogger(__name__)


class DeteccionIAResultado(BaseModel):
    codigo: str = Field(..., description="Codigo ISO 639-1 del idioma detectado (ej: es, en, ja, zh, fr, de, it, pt)")
    confianza: float = Field(..., description="Nivel de confianza de la deteccion entre 0.0 y 1.0")


class DetectorIdioma:

    def __init__(self):
        self.cliente = OpenAI(api_key=configuracion.openai_api_key)

    def detectar(self, texto: str) -> dict:
        texto = texto.strip()

        if not texto:
            raise ValueError("El texto no puede estar vacio.")

        idiomas_soportados = ", ".join(
            f"{codigo} ({nombre})" for codigo, nombre in IDIOMAS.items()
        )

        prompt_sistema = (
            "Eres un detector de idiomas experto. "
            "Tu única tarea es identificar el idioma del texto que te envíen y devolver su código ISO 639-1.\n\n"
            f"Los idiomas que soporta el sistema son: {idiomas_soportados}.\n\n"
            "REGLAS:\n"
            "1. Si el texto está en uno de los idiomas soportados, devuelve su código (ej: 'ja', 'en', 'es').\n"
            "2. Si el texto está en un idioma NO soportado, devuelve el código 'desconocido'.\n"
            "3. Debes reconocer tanto texto nativo (japonés en kanji/hiragana) como texto romanizado "
            "(ej: 'Konbanwa', 'Oyasumi', 'Arigatou' son japonés).\n"
            "4. La confianza debe ser entre 0.0 y 1.0. Si estás seguro, usa 0.99. Si hay duda, usa un valor menor.\n"
            "5. Devuelve SOLO el JSON estructurado, sin explicaciones adicionales."
        )

        prompt_usuario = f"Detecta el idioma de este texto:\n\n{texto}"

        try:
            respuesta = self.cliente.responses.parse(
                model="gpt-5.6-luna",
                input=[
                    {"role": "system", "content": prompt_sistema},
                    {"role": "user", "content": prompt_usuario},
                ],
                text_format=DeteccionIAResultado,
            )
            resultado = respuesta.output_parsed
            codigo = resultado.codigo.strip().lower()

            # Validar que el código retornado esté en los idiomas soportados
            if codigo not in IDIOMAS:
                return {
                    "codigo": "desconocido",
                    "nombre": "No detectado",
                    "confianza": 0.0,
                }

            return {
                "codigo": codigo,
                "nombre": IDIOMAS.get(codigo, "Idioma desconocido"),
                "confianza": resultado.confianza,
            }

        except Exception as error:
            logger.warning(f"Error al detectar idioma con IA: {error}")
            return {
                "codigo": "desconocido",
                "nombre": "No detectado",
                "confianza": 0.0,
            }


detector_idioma = DetectorIdioma()
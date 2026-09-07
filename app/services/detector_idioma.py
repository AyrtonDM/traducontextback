import os
import fasttext

from app.constants.idiomas import IDIOMAS


class DetectorIdioma:

    def __init__(self, ruta_modelo: str):
        if not os.path.exists(ruta_modelo):
            raise FileNotFoundError(
                f"No se encontro el modelo de deteccion de idioma: {ruta_modelo}"
            )

        self.modelo = fasttext.load_model(ruta_modelo)

    def detectar(self, texto: str) -> dict:
        texto = texto.strip()

        if not texto:
            raise ValueError("El texto no puede estar vacio.")

        idiomas, probabilidades = self.modelo.predict(
            texto,
            k=1
        )

        codigo = idiomas[0].replace("__label__", "")
        confianza = float(probabilidades[0])

        return {
            "codigo": codigo,
            "nombre": IDIOMAS.get(codigo, "Idioma desconocido"),
            "confianza": confianza
        }
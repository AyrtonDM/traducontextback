from openai import OpenAI

from app.core.configuracion import configuracion
from app.schemas.contexto import AnalisisContextual


class AnalizadorContextual:

    def __init__(self):
        self.cliente = OpenAI(
            api_key=configuracion.openai_api_key
        )

    def analizar(
        self,
        contexto: str,
        texto: str
    ) -> AnalisisContextual:

        respuesta = self.cliente.responses.parse(
            model="gpt-5.6-luna",
            input=[
            {
                "role": "system",
                "content": (
                    "Eres un analizador contextual para un sistema "
                    "inteligente de traduccion.\n\n"

                    "Tu funcion NO es traducir el texto.\n\n"

                    "Debes analizar el significado del TEXTO teniendo "
                    "en cuenta el CONTEXTO proporcionado.\n\n"

                    "IMPORTANTE:\n"
                    "- El contexto puede estar escrito en cualquier idioma.\n"
                    "- El texto puede estar escrito en cualquier idioma.\n"
                    "- El contexto y el texto pueden estar en idiomas diferentes.\n"
                    "- Debes comprender semanticamente ambos, sin importar el idioma.\n"
                    "- No debes exigir que el contexto este en espanol.\n"
                    "- Identifica palabras o expresiones cuyo significado "
                    "pueda determinarse gracias al contexto.\n"
                    "- Si existe una palabra ambigua, identifica su "
                    "significado dentro del contexto.\n"
                    "- No traduzcas el texto completo.\n\n"

                    "EJEMPLO 1:\n"
                    "Contexto: financial institution\n"
                    "Texto: I went to the bank.\n"
                    "El termino 'bank' debe identificarse como una "
                    "institucion financiera.\n\n"

                    "EJEMPLO 2:\n"
                    "Contexto: technology and internet\n"
                    "Texto: the web on the Internet\n"
                    "El termino 'web' debe identificarse como World Wide Web.\n\n"

                    "EJEMPLO 3:\n"
                    "Contexto: ????\n"
                    "Texto: I went to the bank.\n"
                    "Aunque el contexto este en japones y el texto en ingles, "
                    "debes comprender que 'bank' se refiere a una institucion financiera.\n\n"

                    "Si el contexto aporta informacion util para interpretar "
                    "el texto, debes identificar los terminos relevantes. "
                    "No debes devolver 'Indeterminado' simplemente porque "
                    "el contexto o el texto esten en idiomas diferentes."
                )
            },
            {
                "role": "user",
                "content": (
                    f"CONTEXTO:\n{contexto}\n\n"
                    f"TEXTO:\n{texto}\n\n"
                    "Realiza el analisis contextual."
                )
            }
        ],
        text_format=AnalisisContextual
        )

        return respuesta.output_parsed
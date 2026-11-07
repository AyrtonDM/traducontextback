import logging
from openai import OpenAI

from app.core.configuracion import configuracion
from app.schemas.traduccion import (
    AlternativaTraduccion,
    ExplicacionExpresion,
    ResultadoEnriquecimiento,
)

logger = logging.getLogger(__name__)


class EnriquecedorTraduccion:
    """
    Servicio encargado de generar alternativas de traduccion y explicar modismos/expresiones
    utilizando el modelo de lenguaje de acuerdo a la configuracion activa del usuario.
    """

    def __init__(self):
        self.cliente = OpenAI(
            api_key=configuracion.openai_api_key
        )

    def enriquecer(
        self,
        texto_origen: str,
        idioma_origen: str,
        idioma_destino: str,
        traduccion_base: str,
        nombre_contexto: str | None = None,
        descripcion_contexto: str | None = None,
        nombre_tono: str | None = None,
        nombre_variante: str | None = None,
        generar_alternativas: bool = False,
        explicar_expresiones: bool = False,
    ) -> ResultadoEnriquecimiento:
        if not generar_alternativas and not explicar_expresiones:
            return ResultadoEnriquecimiento(
                alternativas=[],
                explicacion_expresiones=[],
            )

        detalles_contexto = []
        if nombre_contexto:
            detalles_contexto.append(f"Contexto: {nombre_contexto}")
        if descripcion_contexto:
            detalles_contexto.append(f"Descripcion del contexto: {descripcion_contexto}")
        if nombre_tono:
            detalles_contexto.append(f"Tono deseado: {nombre_tono}")
        if nombre_variante:
            detalles_contexto.append(f"Variante regional: {nombre_variante}")

        contexto_str = "\n".join(detalles_contexto) if detalles_contexto else "Ninguno especificado"

        instrucciones = []
        if generar_alternativas:
            instrucciones.append(
                "- generar_alternativas=True: Proporciona entre 2 y 3 alternativas de traduccion al idioma de destino "
                "que ofrezcan opciones validas, matices o sinonimos acordes al contexto, tono y variante. "
                "Incluye una breve explicacion del matiz en el campo 'explicacion'."
            )
        else:
            instrucciones.append(
                "- generar_alternativas=False: Deja la lista 'alternativas' estrictamente vacia ([])."
            )

        if explicar_expresiones:
            instrucciones.append(
                "- explicar_expresiones=True: Identifica modismos, expresiones coloquiales, frases hechas o terminos "
                "idiomaticos presentes en el texto original. Para cada uno, incluye la expresion original ('expresion'), "
                "su significado ('significado'), y su equivalente o forma traducida ('equivalente'). "
                "Si el texto no contiene expresiones idiomaticas o modismos, devuelve la lista vacia ([])."
            )
        else:
            instrucciones.append(
                "- explicar_expresiones=False: Deja la lista 'explicacion_expresiones' estrictamente vacia ([])."
            )

        instrucciones_str = "\n".join(instrucciones)

        prompt_usuario = (
            f"INFORMACION DE TRADUCCION:\n"
            f"- Idioma de origen: {idioma_origen}\n"
            f"- Idioma de destino: {idioma_destino}\n"
            f"- Texto de origen: {texto_origen}\n"
            f"- Traduccion base obtenida: {traduccion_base}\n\n"
            f"CONFIGURACION ADICIONAL:\n"
            f"{contexto_str}\n\n"
            f"INSTRUCCIONES A CUMPLIR:\n"
            f"{instrucciones_str}\n"
        )

        try:
            respuesta = self.cliente.responses.parse(
                model="gpt-5.6-luna",
                input=[
                    {
                        "role": "system",
                        "content": (
                            "Eres un asistente linguistico especializado en traduccion, analisis semantico, "
                            "modismos y adaptacion contextual de textos. Responde siempre respetando estrictamente "
                            "el esquema de salida solicitado."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt_usuario,
                    },
                ],
                text_format=ResultadoEnriquecimiento,
            )
            return respuesta.output_parsed
        except Exception as error:
            logger.warning(
                "No se pudo enriquecer la traduccion con alternativas o modismos: %s",
                error,
            )
            return ResultadoEnriquecimiento(
                alternativas=[],
                explicacion_expresiones=[],
            )

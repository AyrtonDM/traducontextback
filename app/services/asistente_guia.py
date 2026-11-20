import logging

from openai import OpenAI

from app.core.configuracion import configuracion
from app.schemas.asistente_guia import (
    BienvenidaGuiaDetalle,
    ResultadoPreguntaGuia,
    SolicitudPreguntaGuia,
)

logger = logging.getLogger(__name__)

CONOCIMIENTO_SISTEMA_TRADUCONTEXT = """
MANUAL OFICIAL DE LA PLATAFORMA TRADUCONTEXT:

1. QUe ES TRADUCONTEXT?
TraduContext es un Asistente Inteligente de Traduccion Contextual que adapta las traducciones segun la situacion comunicativa, dominio tecnico, tono, variante regional y glosarios del usuario. Cuenta con 6 modulos principales:

2. MoDULO 1: TRADUCCIoN CONTEXTUAL DE TEXTO
- Permite traducir textos entre multiples idiomas (Espanol, Ingles, Frances, Portugues, Aleman, Italiano, etc.) o detectar automaticamente el idioma de origen.
- Contexto / Dominio: Permite elegir el ambito del texto (General, Tecnico, Medico, Legal, Academico, Negocios) o crear contextos personalizados para que los terminos se traduzcan con el sentido correcto.
- Tono: Ajusta el estilo de la traduccion (Neutral, Formal, Informal, Profesional).
- Variante Regional: Adapta el vocabulario al pais o region del idioma destino (ej. Espanol de Espana, Mexico, Latinoamerica; Ingles de EE. UU. o Reino Unido).
- Explicar expresiones / modismos: Identifica frases hechas o modismos en el texto original, explica su significado y muestra su equivalente natural.
- Generar alternativas: Muestra de 2 a 3 variantes adicionales de traduccion explicando el matiz de cada una.
- Glosario opcional: Permite aplicar un glosario personalizado del usuario durante la traduccion.

3. MoDULO 2: TRADUCCIoN DE DOCUMENTOS (.DOCX, .XLSX, .PDF)
- Permite subir documentos en formato Word (.docx), Excel (.xlsx) y PDF (.pdf).
- Al subir un archivo, el sistema detecta automaticamente el idioma en el que esta escrito.
- Conserva el formato original, tablas, diseno e imagenes del documento al generar el archivo traducido.
- Permite aplicar un glosario personalizado al traducir el documento.
- Cuenta con dos listados: Documentos Originales subidos y Documentos Traducidos (del mas reciente al mas antiguo), con descarga directa y eliminacion independiente (si eliminas el documento original, tus documentos traducidos se conservan).

4. MoDULO 3: CONVERSACIoN EN TIEMPO REAL
- Permite mantener conversaciones bilingües fluidas en tiempo real entre 2 o mas participantes.
- Configuracion de la conversacion (panel izquierdo):
  * Idiomas de la conversacion (ej. Espanol <-> Ingles).
  * Entorno de conversacion: Reunion, Conferencias, Clases, Entrevistas o Conversacion informal.
  * Contexto / Dominio y Tono.
  * Otras opciones: 'Mantener contexto de la conversacion' (recuerda los turnos anteriores para mantener coherencia) y 'Asistencia conversacional'.
- Controles de sesion:
  * Boton 'Iniciar conversacion': Crea la sesion activa con los participantes configurados.
  * Boton Microfono: Permite hablar o ingresar una intervencion; transcribe la voz y traduce bidireccionalmente de forma automatica hacia el idioma del otro participante.
  * Botones Pausar, Reanudar y Finalizar: Controlan el estado de la sesion (ACTIVA, PAUSADA, FINALIZADA).
  * Boton 'Asistente': Genera explicaciones contextuales del turno seleccionado, sugerencias de respuestas rapidas listas para usar y recomendaciones sobre como expresar una idea segun el entorno.
  * Boton 'Reproduccion por voz': Reproduce con voz sintetizada (TTS) el audio de la traduccion de cada intervencion.
  * Panel 'Participantes': Permite ver y editar los nombres o idiomas de Participante 1, Participante 2, o agregar mas participantes.

5. MoDULO 4: GLOSARIOS PERSONALIZADOS
- Permite crear diccionarios propios para un par de idiomas (ej. Ingles -> Espanol).
- Cada termino del glosario puede tener una de dos reglas:
  * Traduccion preferida: Define exactamente como debe traducirse una palabra o frase tecnica.
  * Conservar original: Impide que se traduzcan nombres de marcas, empresas, siglas o terminos que deben mantenerse en su idioma original.
- Tambien permite indicar si el termino debe distinguir entre mayusculas y minusculas.

6. MoDULO 5: HISTORIAL DE TRADUCCIONES
- Almacena automaticamente las traducciones de texto realizadas por el usuario.
- Permite buscar y filtrar por: texto (original o traducido), idioma de origen, idioma de destino, rango de fechas (fecha desde / fecha hasta) y filtro de 'Solo favoritos'.
- Permite marcar o desmarcar traducciones como Favoritas (icono de estrella) y eliminar registros del historial.

7. MoDULO 6: PERFIL Y CONFIGURACIoN DE USUARIO
- Permite actualizar el nombre del usuario, subir o cambiar su foto de perfil (JPG, PNG o WEBP de hasta 5 MB) y guardar su configuracion de traduccion predeterminada.

8. MoDULO 7: CHATS MULTILINGÜES ENTRE USUARIOS
- Permite buscar a otros usuarios activos de TraduContext e iniciar un chat directo uno a uno.
- Cada participante elige su propio 'idioma de lectura': los mensajes que envia la otra persona se traducen automaticamente en segundo plano al idioma de lectura de quien los recibe.
- Permite configurar un contexto compartido para el chat y recibir notificaciones en bandeja y push cuando llegan nuevos mensajes.

9. MoDULO 8: INTEGRACIONES Y SESIONES EXTERNAS
- Permite vincular plataformas externas de reuniones/llamadas y gestionar sesiones externas de traduccion contextual bidireccional con identificacion de participantes y control de estado (iniciar, pausar, reanudar, finalizar).

10. MoDULO 9: APRENDIZAJE DE PREFERENCIAS, DASHBOARD Y REPORTES (ADMINISTRACIoN)
- Aprendizaje: Registra correcciones y elecciones del usuario para sugerir y adaptar futuras traducciones.
- Dashboard y Reportes (para Administradores): Visualizacion de metricas e indicadores de uso de la plataforma y exportacion de reportes filtrados.
"""

SUGERENCIAS_POR_VISTA: dict[str, list[str]] = {
    "conversaciones": [
        "Como inicio una conversacion en tiempo real?",
        "Para que sirve el boton Asistente en la conversacion?",
        "Como funciona la traduccion por microfono y reproduccion por voz?",
    ],
    "documentos": [
        "Que formatos de documento puedo subir y traducir?",
        "Se conserva el diseno e imagenes de mi PDF o Word al traducir?",
        "Que pasa con mis traducciones si elimino el documento original?",
    ],
    "glosarios": [
        "Como creo un glosario personalizado?",
        "Como evito que se traduzca una marca o sigla con un glosario?",
        "Como aplico mi glosario al traducir un texto o documento?",
    ],
    "historial": [
        "Como busco o filtro mis traducciones anteriores?",
        "Como marco una traduccion como favorita?",
        "Como elimino un registro de mi historial?",
    ],
    "perfil": [
        "Como cambio mi foto de perfil?",
        "Como guardo mi configuracion de traduccion predeterminada?",
        "Que formatos de imagen acepta la foto de perfil?",
    ],
    "traduccion": [
        "Como funcionan el Contexto, Tono y Variante Regional?",
        "Que hacen las opciones Explicar expresiones y Generar alternativas?",
        "Como uso un glosario personalizado al traducir un texto?",
    ],
    "chats": [
        "Como inicio un chat multilingüe con otro usuario?",
        "Como cambio mi idioma de lectura en un chat?",
        "Como configuro el contexto compartido de un chat?",
    ],
    "integraciones": [
        "Como vinculo una plataforma externa como Zoom o Meet?",
        "Como inicio una sesion externa de traduccion?",
        "Como controlo la traduccion durante una reunion externa?",
    ],
    "dashboard": [
        "Que indicadores muestra el dashboard administrativo?",
        "Como genero y filtro un reporte administrativo?",
        "En que formatos puedo exportar los reportes?",
    ],
    "general": [
        "Que modulos tiene la plataforma TraduContext?",
        "Como funciona la Conversacion en tiempo real?",
        "Como traduzco un documento PDF, Word o Excel?",
    ],
}


def obtener_bienvenida_guia(vista_actual: str | None = None) -> BienvenidaGuiaDetalle:
    clave_vista = (vista_actual or "general").strip().lower()
    if clave_vista not in SUGERENCIAS_POR_VISTA:
        for k in SUGERENCIAS_POR_VISTA:
            if k in clave_vista:
                clave_vista = k
                break
        else:
            clave_vista = "general"

    saludos_por_vista = {
        "conversaciones": (
            "¡Hola! Soy el Asistente Guia de TraduContext. Veo que estas en el modulo de "
            "**Conversacion en tiempo real**. En que puedo ayudarte?"
        ),
        "documentos": (
            "¡Hola! Soy el Asistente Guia de TraduContext. Estoy aqui para ayudarte con la "
            "**Traduccion de Documentos** (.docx, .xlsx y .pdf). Que deseas saber?"
        ),
        "glosarios": (
            "¡Hola! Soy el Asistente Guia de TraduContext. Puedo explicarte como crear y usar "
            "**Glosarios Personalizados**. Que duda tienes?"
        ),
        "historial": (
            "¡Hola! Soy el Asistente Guia de TraduContext. Puedo ayudarte a filtrar tu "
            "**Historial de Traducciones** y gestionar tus favoritos."
        ),
        "perfil": (
            "¡Hola! Soy el Asistente Guia de TraduContext. Necesitas ayuda para configurar "
            "tu **Perfil** o tus preferencias de traduccion?"
        ),
        "traduccion": (
            "¡Hola! Soy el Asistente Guia de TraduContext. Puedo guiarte para aprovechar al maximo "
            "la **Traduccion Contextual**, tonos, modismos y alternativas."
        ),
        "chats": (
            "¡Hola! Soy el Asistente Guia de TraduContext. Puedo explicarte como usar los "
            "**Chats Multilingües** con traduccion automatica en tu idioma de lectura."
        ),
        "integraciones": (
            "¡Hola! Soy el Asistente Guia de TraduContext. Necesitas ayuda con las "
            "**Integraciones y Sesiones Externas**?"
        ),
        "dashboard": (
            "¡Hola! Soy el Asistente Guia de TraduContext. Puedo orientarte en el uso del "
            "**Dashboard Administrativo y Reportes**."
        ),
        "general": (
            "¡Hola! Soy el Asistente Guia de **TraduContext**. Puedo ayudarte con cualquier consulta "
            "sobre como usar los modulos de la plataforma. Que te gustaria aprender a usar?"
        ),
    }

    return BienvenidaGuiaDetalle(
        saludo=saludos_por_vista[clave_vista],
        vista_actual=clave_vista,
        sugerencias_iniciales=SUGERENCIAS_POR_VISTA[clave_vista],
    )


class AsistenteGuiaServicio:
    """
    Chatbot guia del sistema acotado estrictamente a responder consultas sobre
    el funcionamiento y uso de la plataforma TraduContext.
    """

    def __init__(self) -> None:
        self._cliente: OpenAI | None = None

    def _obtener_cliente(self) -> OpenAI | None:
        if self._cliente is None and configuracion.openai_api_key:
            try:
                self._cliente = OpenAI(api_key=configuracion.openai_api_key)
            except Exception as exc:
                logger.warning("No se pudo inicializar cliente OpenAI en AsistenteGuia: %s", exc)
        return self._cliente

    def responder(self, solicitud: SolicitudPreguntaGuia) -> ResultadoPreguntaGuia:
        pregunta = solicitud.pregunta.strip()
        bienvenida = obtener_bienvenida_guia(solicitud.vista_actual)
        cliente = self._obtener_cliente()

        if cliente:
            system_prompt = (
                "Eres el Asistente Guia Oficial integrado en la plataforma TraduContext.\n"
                "Tu uNICA mision es orientar al usuario sobre como utilizar las funciones, pantallas, "
                "botones y modulos del sistema TraduContext.\n\n"
                f"{CONOCIMIENTO_SISTEMA_TRADUCONTEXT}\n\n"
                "REGLAS ESTRICTAS DE DOMINIO (GUARDRAILS):\n"
                "1. SOLO debes responder consultas sobre el sistema TraduContext, sus modulos, como realizar "
                "acciones dentro de la plataforma o que significa cada opcion de la interfaz.\n"
                "2. Si el usuario hace una pregunta que NO tiene relacion con TraduContext (por ejemplo: "
                "matematicas, recetas de cocina, historia general, programar codigo externo, politica, chistes "
                "o tareas escolares ajenas a la plataforma), pon `es_tema_sistema=False` y responde amablemente: "
                "'Soy el asistente guia exclusivo de **TraduContext**. Solo estoy habilitado para responder "
                "consultas sobre el funcionamiento y uso de los modulos de nuestra plataforma (Traduccion Contextual, "
                "Documentos, Conversacion en Tiempo Real, Glosarios, Historial y Perfil). En cual de estos modulos "
                "te gustaria que te guie?'\n"
                "3. Se claro, amable, conciso y utiliza vinetas o pasos numerados cortos.\n"
                "4. Devuelve siempre 3 preguntas cortas en `sugerencias` sobre funcionalidades de TraduContext "
                "para que el usuario pueda seguir explorando el sistema."
            )

            mensajes_input: list[dict[str, str]] = [
                {"role": "system", "content": system_prompt},
            ]

            for msg in solicitud.historial[-6:]:
                rol = "assistant" if msg.rol.lower().strip() == "assistant" else "user"
                mensajes_input.append({"role": rol, "content": msg.contenido.strip()})

            contexto_vista = (
                f"[El usuario se encuentra actualmente en la vista/modulo: '{bienvenida.vista_actual}']\n"
                if solicitud.vista_actual
                else ""
            )
            mensajes_input.append(
                {"role": "user", "content": f"{contexto_vista}Consulta del usuario: {pregunta}"}
            )

            try:
                respuesta_ia = cliente.responses.parse(
                    model="gpt-5.6-luna",
                    input=mensajes_input,
                    text_format=ResultadoPreguntaGuia,
                )
                parsed = respuesta_ia.output_parsed
                if parsed and parsed.respuesta.strip():
                    if not parsed.sugerencias:
                        parsed.sugerencias = bienvenida.sugerencias_iniciales
                    return parsed
            except Exception as exc:
                logger.warning("AsistenteGuia OpenAI fallo, usando motor local de conocimiento: %s", exc)

        return self._responder_con_motor_local(pregunta, bienvenida.vista_actual)

    def _responder_con_motor_local(
        self,
        pregunta: str,
        vista_actual: str,
    ) -> ResultadoPreguntaGuia:
        p = pregunta.lower()

        # Verificar si es consulta sobre conversacion en tiempo real
        if any(
            kw in p
            for kw in (
                "conversac",
                "tiempo real",
                "microfono",
                "microfono",
                "participante",
                "pausar",
                "reanudar",
                "finalizar",
                "entorno",
                "reunion",
                "reunion",
                "voz",
                "audio",
                "asistente",
                "turno",
            )
        ):
            return ResultadoPreguntaGuia(
                respuesta=(
                    "En el modulo de **Conversacion en tiempo real** puedes comunicarte en dos idiomas simultaneamente:\n"
                    "1. **Configura la sesion (panel izquierdo):** Elige los dos idiomas (ej. Espanol ? Ingles), el **Entorno** (*Reunion, Conferencias, Clases, Entrevistas, Conversacion informal*), el **Contexto** y el **Tono**.\n"
                    "2. **Inicia la conversacion:** Pulsa **Iniciar conversacion** para activar la sala con los participantes.\n"
                    "3. **Habla o escribe:** Usa el boton del **Microfono** para registrar cada intervencion; el sistema traducira automaticamente al idioma del otro participante y generara el audio para escucharlo con **Reproduccion por voz**.\n"
                    "4. **Usa el boton `? Asistente`:** Obten explicaciones del contexto, sugerencias de respuestas rapidas y recomendaciones de como expresar tus ideas."
                ),
                sugerencias=SUGERENCIAS_POR_VISTA["conversaciones"],
                es_tema_sistema=True,
            )

        # Verificar si es consulta sobre documentos
        if any(
            kw in p
            for kw in (
                "documento",
                "pdf",
                "word",
                "docx",
                "excel",
                "xlsx",
                "archivo",
                "subir",
                "descargar",
                "formato",
            )
        ):
            return ResultadoPreguntaGuia(
                respuesta=(
                    "El modulo de **Traduccion de Documentos** funciona en 3 pasos:\n"
                    "1. **Subir archivo:** Puedes subir documentos **Word (`.docx`)**, **Excel (`.xlsx`)** o **PDF (`.pdf`)**. El sistema detectara automaticamente el idioma original del documento.\n"
                    "2. **Traducir conservando formato:** Selecciona el idioma de destino (y opcionalmente un glosario) y pulsa traducir. Se mantendran las imagenes, tablas y diseno original.\n"
                    "3. **Descargar o gestionar:** Puedes descargar tanto el archivo original como el traducido. Si eliminas el documento original, tus documentos traducidos se conservan intactos."
                ),
                sugerencias=SUGERENCIAS_POR_VISTA["documentos"],
                es_tema_sistema=True,
            )

        # Verificar si es consulta sobre glosarios
        if any(
            kw in p
            for kw in (
                "glosario",
                "termino",
                "termino",
                "marca",
                "conservar",
                "preferida",
                "diccionario",
            )
        ):
            return ResultadoPreguntaGuia(
                respuesta=(
                    "Con los **Glosarios Personalizados** puedes controlar como se traducen palabras especificas:\n"
                    "1. Ve a **Glosarios** y crea uno eligiendo el idioma de origen y de destino.\n"
                    "2. Agrega tus terminos eligiendo una de dos reglas:\n"
                    "   - **Traduccion preferida:** Fuerza una traduccion exacta para un termino tecnico.\n"
                    "   - **Conservar original:** Evita que nombres de marcas, empresas o siglas sean traducidos.\n"
                    "3. Selecciona tu glosario al traducir un texto, documento o conversacion."
                ),
                sugerencias=SUGERENCIAS_POR_VISTA["glosarios"],
                es_tema_sistema=True,
            )

        # Verificar si es consulta sobre historial o favoritos
        if any(kw in p for kw in ("historial", "favorito", "estrella", "buscar", "filtrar", "fecha")):
            return ResultadoPreguntaGuia(
                respuesta=(
                    "En el **Historial de Traducciones** puedes consultar todas tus traducciones previas:\n"
                    "- **Filtros combinados:** Filtra por palabra clave, idioma de origen, idioma de destino, rango de fechas (`desde` / `hasta`) o activa **Solo favoritos**.\n"
                    "- **Favoritos:** Pulsa la estrella en cualquier traduccion para destacarla.\n"
                    "- **Eliminar:** Puedes borrar cualquier registro del historial cuando ya no lo necesites."
                ),
                sugerencias=SUGERENCIAS_POR_VISTA["historial"],
                es_tema_sistema=True,
            )

        # Verificar si es consulta sobre perfil
        if any(kw in p for kw in ("perfil", "foto", "cuenta", "nombre", "configuracion", "configuracion")):
            return ResultadoPreguntaGuia(
                respuesta=(
                    "En la seccion **Mi Perfil** puedes:\n"
                    "- Actualizar tu **nombre completo**.\n"
                    "- Subir o cambiar tu **foto de perfil** (formatos JPG, PNG o WEBP de hasta 5 MB).\n"
                    "- Configurar tus preferencias predeterminadas de traduccion (Contexto, Tono, Variante Regional, Entorno de conversacion, Explicacion de modismos y Alternativas)."
                ),
                sugerencias=SUGERENCIAS_POR_VISTA["perfil"],
                es_tema_sistema=True,
            )

        # Verificar si es consulta sobre traduccion contextual / general del sistema
        if any(
            kw in p
            for kw in (
                "traducontext",
                "sistema",
                "plataforma",
                "como funciona",
                "como funciona",
                "ayuda",
                "hola",
                "modulo",
                "modulo",
                "tono",
                "contexto",
                "variante",
                "modismo",
                "expresion",
                "alternativa",
                "traducir",
            )
        ):
            return ResultadoPreguntaGuia(
                respuesta=(
                    "**TraduContext** cuenta con los siguientes modulos para ayudarte:\n"
                    "1. **Traduccion Contextual de Texto:** Traduce adaptando el *Contexto/Dominio*, *Tono*, *Variante Regional*, *Glosario*, *Explicacion de modismos* y *Alternativas*.\n"
                    "2. **Traduccion de Documentos:** Traduce archivos `.docx`, `.xlsx` y `.pdf` conservando su diseno e imagenes.\n"
                    "3. **Conversacion en Tiempo Real:** Traduccion bidireccional por turnos con microfono, sintesis de voz, memoria de contexto y asistente de respuestas.\n"
                    "4. **Glosarios e Historial:** Diccionarios propios por par de idiomas y registro filtrable con favoritos."
                ),
                sugerencias=SUGERENCIAS_POR_VISTA.get(vista_actual, SUGERENCIAS_POR_VISTA["general"]),
                es_tema_sistema=True,
            )

        # Fuera de dominio (Guardrail)
        return ResultadoPreguntaGuia(
            respuesta=(
                "Soy el asistente guia exclusivo de **TraduContext**. Solo estoy habilitado para responder "
                "consultas sobre el funcionamiento y uso de los modulos de nuestra plataforma "
                "(**Traduccion Contextual**, **Documentos**, **Conversacion en Tiempo Real**, **Glosarios**, "
                "**Historial** y **Perfil**). Sobre cual de estos modulos te gustaria recibir ayuda?"
            ),
            sugerencias=SUGERENCIAS_POR_VISTA.get(vista_actual, SUGERENCIAS_POR_VISTA["general"]),
            es_tema_sistema=False,
        )


asistente_guia_servicio = AsistenteGuiaServicio()

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.glosario.glosario import Glosario
from app.models.traduccion.idioma import Idioma
from app.models.traduccion.variante_regional import VarianteRegional
from app.schemas.glosario import TerminoAplicado
from app.services.aplicador_glosario import construir_reglas, describir_reglas
from app.services.enriquecedor_traduccion import (
    EnriquecedorTraduccion,
    EnriquecimientoProcesado,
)
from app.services.glosarios import obtener_glosario_para_traduccion
from app.services.motor_contextual import MotorContextual
from app.services.traduccion import traducir_texto


enriquecedor_traduccion = EnriquecedorTraduccion()

ESTADO_REGION_SIN_REGION = "sin_region"
ESTADO_REGION_APLICADA = "aplicada"
ESTADO_REGION_INCOMPATIBLE = "incompatible"
ESTADO_REGION_ERROR_ADAPTACION = "error_adaptacion"


@dataclass
class TraduccionContextual:
    """Resultado de la traduccion central: base (NLLB + glosario) mas enriquecimiento segun configuracion."""

    texto_origen: str
    idioma_origen: str
    idioma_destino: str
    # Traduccion final: la adaptada a la region si se aplico correctamente; si no, la base
    traduccion: str
    # Traduccion de NLLB con el glosario aplicado
    traduccion_base: str
    confianza_deteccion: float | None
    estado_region: str
    enriquecimiento: EnriquecimientoProcesado
    glosario_usado: Glosario | None = None
    terminos_glosario_aplicados: list[TerminoAplicado] = field(default_factory=list)
    analisis_contextual: dict | None = None
    # Ids de los idiomas resueltos; None si el codigo no existe en la base de datos
    id_idioma_origen: int | None = None
    id_idioma_destino: int | None = None
    # True si la traduccion final es la reescrita segun tono y contexto (adaptar_estilo)
    estilo_aplicado: bool = False

    @property
    def region_aplicada(self) -> bool:
        return self.estado_region == ESTADO_REGION_APLICADA


def traducir_con_configuracion(
    sesion: Session,
    id_usuario: int,
    texto: str,
    idioma_origen: str | None,
    idioma_destino: str,
    *,
    nombre_contexto: str | None = None,
    descripcion_contexto: str | None = None,
    nombre_tono: str | None = None,
    variante: VarianteRegional | None = None,
    id_glosario: int | None = None,
    generar_alternativas: bool = False,
    explicar_expresiones: bool = False,
    analizar_contexto: bool = False,
    adaptar_estilo: bool = False,
    tiempo_maximo_llm: float | None = None,
    nombre_entorno: str | None = None,
) -> TraduccionContextual:
    """
    Funcion central de traduccion contextual (HU-15 a HU-18 y glosarios), reutilizable por
    /traducciones y por las conversaciones.

    1. Analisis contextual opcional (no altera la traduccion; si falla se omite).
    2. Traduccion base con NLLB aplicando el glosario indicado (detecta el idioma si no se indica).
    3. La variante regional solo se aplica si corresponde al idioma de destino.
    4. Enriquecimiento con el modelo de lenguaje (region, alternativas, modismos y, si se pide
       `adaptar_estilo`, tono y contexto); si falla, expira (`tiempo_maximo_llm`) o no respeta el
       glosario, se conserva la traduccion base.

    Las consultas a la base de datos se hacen solo cuando hacen falta (glosario, o idioma de destino
    si hay variante) y el resto al final, para no dejar una transaccion abierta mientras se traduce.

    Lanza GlosarioNoEncontradoError si el glosario no es del usuario o no coincide con el par de
    idiomas, y ValueError ante datos invalidos. No guarda nada en la base de datos.
    """

    # 1. Analisis contextual
    analisis_contextual = None
    contexto_analisis = descripcion_contexto or nombre_contexto
    if analizar_contexto and contexto_analisis:
        try:
            analisis = MotorContextual().analizar(contexto=contexto_analisis, texto=texto)
            if hasattr(analisis, "model_dump"):
                analisis_contextual = analisis.model_dump()
        except Exception:
            pass

    # 2. Traduccion base (aplicando el glosario seleccionado, si lo hay)
    glosario_usado = None

    def obtener_reglas_glosario(codigo_origen: str, codigo_destino: str):
        nonlocal glosario_usado
        if id_glosario is None:
            return []
        glosario_usado = obtener_glosario_para_traduccion(
            sesion=sesion,
            id_usuario=id_usuario,
            id_glosario=id_glosario,
            codigo_idioma_origen=codigo_origen,
            codigo_idioma_destino=codigo_destino,
        )
        return construir_reglas(glosario_usado)

    resultado = traducir_texto(
        texto_origen=texto,
        idioma_origen=idioma_origen,
        idioma_destino=idioma_destino,
        obtener_reglas_glosario=obtener_reglas_glosario,
    )

    reglas_glosario = construir_reglas(glosario_usado)
    terminos_aplicados = resultado.get("terminos_glosario_aplicados", [])

    def buscar_idioma(codigo: str) -> Idioma | None:
        return sesion.scalar(select(Idioma).where(Idioma.codigo == codigo))

    # El idioma de destino solo se consulta antes del modelo si hay que validar la variante
    idioma_dest_db = buscar_idioma(resultado["idioma_destino"]) if variante else None

    # 3. Localizacion cultural: la variante solo se aplica si corresponde al idioma de destino
    if not variante:
        estado_region = ESTADO_REGION_SIN_REGION
    elif idioma_dest_db and variante.id_idioma == idioma_dest_db.id_idioma:
        estado_region = ESTADO_REGION_APLICADA
    else:
        estado_region = ESTADO_REGION_INCOMPATIBLE
    region_valida = estado_region == ESTADO_REGION_APLICADA

    # 4. Enriquecer: adaptacion regional, alternativas y explicacion de modismos segun configuracion
    enriquecimiento = enriquecedor_traduccion.enriquecer(
        texto_origen=resultado["texto_origen"],
        idioma_origen=resultado["idioma_origen"],
        idioma_destino=resultado["idioma_destino"],
        traduccion_base=resultado["traduccion"],
        nombre_contexto=nombre_contexto,
        descripcion_contexto=descripcion_contexto,
        nombre_tono=nombre_tono,
        nombre_variante=variante.nombre if variante and region_valida else None,
        generar_alternativas=generar_alternativas,
        explicar_expresiones=explicar_expresiones,
        reglas_glosario=describir_reglas(reglas_glosario),
        adaptar_region=region_valida,
        terminos_glosario_aplicados=terminos_aplicados,
        adaptar_estilo=adaptar_estilo,
        tiempo_maximo=tiempo_maximo_llm,
        nombre_entorno=nombre_entorno,
    )

    traduccion_final = resultado["traduccion"]
    adaptacion_valida = bool(
        enriquecimiento.resultado.traduccion_adaptada and not enriquecimiento.adaptacion_fallida
    )
    estilo_aplicado = False
    if region_valida:
        if adaptacion_valida:
            traduccion_final = enriquecimiento.resultado.traduccion_adaptada
        else:
            # Si el modelo fallo, expiro o no respeto el glosario, se conserva la traduccion base (NLLB)
            estado_region = ESTADO_REGION_ERROR_ADAPTACION
    elif adaptar_estilo and adaptacion_valida:
        traduccion_final = enriquecimiento.resultado.traduccion_adaptada
        estilo_aplicado = True

    idioma_orig_db = buscar_idioma(resultado["idioma_origen"])
    if idioma_dest_db is None:
        idioma_dest_db = buscar_idioma(resultado["idioma_destino"])

    return TraduccionContextual(
        texto_origen=resultado["texto_origen"],
        idioma_origen=resultado["idioma_origen"],
        idioma_destino=resultado["idioma_destino"],
        traduccion=traduccion_final,
        traduccion_base=resultado["traduccion"],
        confianza_deteccion=resultado.get("confianza_deteccion"),
        estado_region=estado_region,
        enriquecimiento=enriquecimiento,
        glosario_usado=glosario_usado,
        terminos_glosario_aplicados=terminos_aplicados,
        analisis_contextual=analisis_contextual,
        id_idioma_origen=idioma_orig_db.id_idioma if idioma_orig_db else None,
        id_idioma_destino=idioma_dest_db.id_idioma if idioma_dest_db else None,
        estilo_aplicado=estilo_aplicado,
    )

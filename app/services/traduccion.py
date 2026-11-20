from collections.abc import Callable

from app.core.configuracion import RUTA_BASE
from app.services.aplicador_glosario import ReglaGlosario, traducir_con_glosario
from app.services.detector_idioma import DetectorIdioma
from app.services.motor_nllb import MotorNLLB


detector_idioma = DetectorIdioma(
    str(RUTA_BASE / "app" / "models_ia" / "detector_idioma" / "lid.176.ftz")
)
motor_nllb = MotorNLLB()


def traducir_texto(
    texto_origen: str,
    idioma_origen: str | None,
    idioma_destino: str,
    obtener_reglas_glosario: Callable[[str, str], list[ReglaGlosario]] | None = None,
) -> dict:
    """
    Traduce un texto. Si se indica `obtener_reglas_glosario`, se invoca con el par
    de idiomas ya resuelto (origen detectado o indicado, destino) y las reglas
    retornadas se aplican durante la traduccion.
    """

    texto_origen = texto_origen.strip()

    if not texto_origen:
        raise ValueError(
            "El texto de origen no puede estar vacio."
        )

    if not idioma_destino:
        raise ValueError(
            "El idioma de destino es obligatorio."
        )

    idioma_destino = idioma_destino.strip().lower()

    confianza_deteccion = None

    if not idioma_origen or not str(idioma_origen).strip():
        resultado_deteccion = detector_idioma.detectar(
            texto_origen
        )
        idioma_origen = resultado_deteccion["codigo"]
        confianza_deteccion = resultado_deteccion["confianza"]
    else:
        idioma_origen = str(idioma_origen).strip().lower()

    reglas = (
        obtener_reglas_glosario(idioma_origen, idioma_destino)
        if obtener_reglas_glosario
        else []
    )

    traduccion, terminos_aplicados = traducir_con_glosario(
        texto=texto_origen,
        idioma_origen=idioma_origen,
        idioma_destino=idioma_destino,
        reglas=reglas,
        traducir=motor_nllb.traducir,
    )

    return {
        "texto_origen": texto_origen,
        "idioma_origen": idioma_origen,
        "idioma_destino": idioma_destino,
        "traduccion": traduccion,
        "confianza_deteccion": confianza_deteccion,
        "terminos_glosario_aplicados": terminos_aplicados,
    }

from app.services.detector_idioma import DetectorIdioma
from app.services.motor_nllb import MotorNLLB


detector_idioma = DetectorIdioma(
    "app/models_ia/detector_idioma/lid.176.ftz"
)
motor_nllb = MotorNLLB()


def traducir_texto(
    texto_origen: str,
    idioma_origen: str | None,
    idioma_destino: str,
) -> dict:

    texto_origen = texto_origen.strip()

    if not texto_origen:
        raise ValueError(
            "El texto de origen no puede estar vacio."
        )

    if not idioma_destino:
        raise ValueError(
            "El idioma de destino es obligatorio."
        )

    confianza_deteccion = None

    if not idioma_origen:
        resultado_deteccion = detector_idioma.detectar(
            texto_origen
        )
        idioma_origen = resultado_deteccion["codigo"]
        confianza_deteccion = resultado_deteccion["confianza"]

    traduccion = motor_nllb.traducir(
        texto=texto_origen,
        idioma_origen=idioma_origen,
        idioma_destino=idioma_destino,
    )

    return {
        "texto_origen": texto_origen,
        "idioma_origen": idioma_origen,
        "idioma_destino": idioma_destino,
        "traduccion": traduccion,
        "confianza_deteccion": confianza_deteccion,
    }
from app.services.detector_idioma import DetectorIdioma


RUTA_MODELO = "app/models_ia/detector_idioma/lid.176.ftz"


detector = DetectorIdioma(RUTA_MODELO)


textos = [
    "Hola, como estas?",
    "Hello, how are you?",
    "Bonjour, comment allez-vous?",
    "Hallo, wie geht es dir?",
    "Hola, necesito ir al banco."
]


for texto in textos:
    resultado = detector.detectar(texto)

    print(f"Texto: {texto}")
    print(f"Idioma: {resultado['codigo']}")
    print(f"NombreIdioma: {resultado['nombre']}")
    print(f"Confianza: {resultado['confianza']:.4f}")
    print("-" * 40)
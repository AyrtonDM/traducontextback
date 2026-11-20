from app.services.traduccion import traducir_texto


def test_traducir_texto_devuelve_resultado_esperado():
    resultado = traducir_texto(
        texto_origen="Hola, como estas?",
        idioma_origen="es",
        idioma_destino="en",
    )

    assert isinstance(resultado, dict)
    assert resultado["texto_origen"] == "Hola, como estas?"
    assert resultado["idioma_origen"] == "es"
    assert resultado["idioma_destino"] == "en"
    assert isinstance(resultado["traduccion"], str)
    assert len(resultado["traduccion"]) > 0

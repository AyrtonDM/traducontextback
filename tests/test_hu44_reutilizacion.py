"""HU-44 Reutilizacion de traducciones: sugerencias del historial en POST /traducciones."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select

from app.core.configuracion import configuracion
from app.models.traduccion.configuracion_traduccion import ConfiguracionTraduccion
from app.models.traduccion.contexto import Contexto
from app.models.traduccion.idioma import Idioma
from app.models.traduccion.traduccion import Traduccion
from tests.conftest import crear_usuario

PREFIJO = configuracion.api_v1_prefix
URL_TRADUCIR = f"{PREFIJO}/traducciones"


@pytest.fixture()
def idiomas(sesion):
    encontrados = {
        i.codigo: i for i in sesion.scalars(select(Idioma).where(Idioma.codigo.in_(["es", "en", "fr"])))
    }
    if len(encontrados) < 3:
        pytest.skip("Se necesitan los idiomas es, en y fr (seeds).")
    return encontrados


def configurar(sesion, usuario) -> ConfiguracionTraduccion:
    contexto = sesion.scalar(select(Contexto).where(Contexto.id_usuario.is_(None)).order_by(Contexto.id_contexto))
    config = ConfiguracionTraduccion(id_usuario=usuario.id, id_contexto=contexto.id_contexto)
    sesion.add(config)
    sesion.commit()
    return config


@pytest.fixture()
def config(sesion, usuario):
    return configurar(sesion, usuario)


def agregar_historial(sesion, usuario, config, original, traducido, origen, destino, dias_atras=1):
    registro = Traduccion(
        texto_original=original,
        texto_traducido=traducido,
        fecha_creacion=datetime.now(timezone.utc) - timedelta(days=dias_atras),
        id_configuracion_traduccion=config.id_configuracion_traduccion,
        id_idioma_origen=origen.id_idioma,
        id_idioma_destino=destino.id_idioma,
        id_usuario=usuario.id,
    )
    sesion.add(registro)
    sesion.commit()
    return registro


@pytest.fixture()
def traduccion_simulada(monkeypatch, idiomas):
    """Motor de traduccion falso: es→en con ids reales, para que se busquen sugerencias y se guarde."""

    def falso_traducir(**kwargs):
        return SimpleNamespace(
            texto_origen=kwargs["texto"],
            idioma_origen="es",
            idioma_destino=kwargs["idioma_destino"],
            traduccion="NEW TRANSLATION",
            confianza_deteccion=None,
            region_aplicada=False,
            estado_region="sin_region",
            enriquecimiento=SimpleNamespace(
                procesado=False,
                resultado=SimpleNamespace(alternativas=[], explicacion_expresiones=[]),
            ),
            glosario_usado=None,
            terminos_glosario_aplicados=[],
            analisis_contextual=None,
            id_idioma_origen=idiomas["es"].id_idioma,
            id_idioma_destino=idiomas[kwargs["idioma_destino"]].id_idioma,
            correcciones_aplicadas=0,
        )

    monkeypatch.setattr("app.api.routes.traducciones.traducir_con_configuracion", falso_traducir)


def traducir(cliente, texto, destino="en"):
    respuesta = cliente.post(URL_TRADUCIR, json={"texto": texto, "idioma_origen": "es", "idioma_destino": destino})
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["resultado"]


# ---------------------------------------------------------------------------


def test_sugiere_traducciones_similares_con_texto_traduccion_y_fecha(
    cliente, sesion, usuario, config, idiomas, traduccion_simulada
):
    previa = agregar_historial(
        sesion, usuario, config, "El contrato vence el lunes.", "The contract expires on Monday.",
        idiomas["es"], idiomas["en"],
    )

    sugerencias = traducir(cliente, "el contrato vence el martes")["sugerencias"]
    assert len(sugerencias) == 1
    s = sugerencias[0]
    assert s["id_traduccion"] == previa.id_traduccion
    assert s["texto_original"] == "El contrato vence el lunes."
    assert s["texto_traducido"] == "The contract expires on Monday."
    assert s["fecha_creacion"]
    assert 0.6 <= s["similitud"] < 1


def test_maximo_tres_ordenadas_por_similitud(cliente, sesion, usuario, config, idiomas, traduccion_simulada):
    es, en = idiomas["es"], idiomas["en"]
    textos = [
        "buenos dias a todos los asistentes",       # identico (1.0)
        "buenos dias a todos los presentes",
        "buenas tardes a todos los asistentes",
        "buenos dias a todos",
        "buenos dias",
    ]
    for indice, texto in enumerate(textos):
        agregar_historial(sesion, usuario, config, texto, f"traduccion {indice}", es, en, dias_atras=indice + 1)

    sugerencias = traducir(cliente, "Buenos días a todos los asistentes")["sugerencias"]
    assert len(sugerencias) == 3
    similitudes = [s["similitud"] for s in sugerencias]
    assert similitudes == sorted(similitudes, reverse=True)
    assert sugerencias[0]["texto_original"] == "buenos dias a todos los asistentes"
    assert sugerencias[0]["similitud"] == 1.0


def test_solo_mismo_par_de_idiomas(cliente, sesion, usuario, config, idiomas, traduccion_simulada):
    agregar_historial(sesion, usuario, config, "el contrato vence el lunes", "le contrat expire lundi",
                      idiomas["es"], idiomas["fr"])
    agregar_historial(sesion, usuario, config, "el contrato vence el lunes", "the contract expires",
                      idiomas["en"], idiomas["es"])

    assert traducir(cliente, "el contrato vence el lunes", destino="en")["sugerencias"] == []
    sugerencias_fr = traducir(cliente, "el contrato vence el lunes", destino="fr")["sugerencias"]
    assert [s["texto_traducido"] for s in sugerencias_fr] == ["le contrat expire lundi"]


def test_solo_traducciones_del_usuario_autenticado(cliente, sesion, idiomas, traduccion_simulada, usuario, config):
    otro = crear_usuario(sesion, "USUARIO")
    config_otro = configurar(sesion, otro)
    agregar_historial(sesion, otro, config_otro, "el contrato vence el lunes", "ajena",
                      idiomas["es"], idiomas["en"])

    assert traducir(cliente, "el contrato vence el lunes")["sugerencias"] == []


def test_sin_coincidencias_traduce_normalmente(cliente, sesion, usuario, config, idiomas, traduccion_simulada):
    agregar_historial(sesion, usuario, config, "el clima esta soleado", "the weather is sunny",
                      idiomas["es"], idiomas["en"])

    resultado = traducir(cliente, "la reunion empieza a las diez")
    assert resultado["sugerencias"] == []
    assert resultado["traduccion"] == "NEW TRANSLATION"


def test_traduccion_eliminada_no_se_sugiere(cliente, sesion, usuario, config, idiomas, traduccion_simulada):
    previa = agregar_historial(sesion, usuario, config, "el contrato vence el lunes", "the contract",
                               idiomas["es"], idiomas["en"])
    respuesta = cliente.delete(f"{URL_TRADUCIR}/{previa.id_traduccion}")
    assert respuesta.status_code in (200, 204), respuesta.text

    assert traducir(cliente, "el contrato vence el lunes")["sugerencias"] == []


def test_no_se_sugiere_a_si_misma_ni_repetidas(cliente, sesion, usuario, config, idiomas, traduccion_simulada):
    for _ in range(3):
        agregar_historial(sesion, usuario, config, "hola equipo", "hello team", idiomas["es"], idiomas["en"])

    primera = traducir(cliente, "hola equipo")["sugerencias"]
    assert len(primera) == 1  # las 3 repeticiones se agrupan

    # La traduccion recien hecha ("NEW TRANSLATION") se guardo pero no se sugiere como identica
    segunda = traducir(cliente, "hola equipo")["sugerencias"]
    assert [s["texto_traducido"] for s in segunda] == ["hello team"]
    total = sesion.scalar(select(func.count()).select_from(Traduccion).where(Traduccion.id_usuario == usuario.id))
    assert total == 5


def test_error_en_sugerencias_no_impide_traducir(cliente, config, traduccion_simulada, monkeypatch):
    def fallar(**_kwargs):
        raise RuntimeError("fallo inesperado")

    monkeypatch.setattr("app.api.routes.traducciones.buscar_traducciones_similares", fallar)
    resultado = traducir(cliente, "hola equipo")
    assert resultado["traduccion"] == "NEW TRANSLATION"
    assert resultado["sugerencias"] == []

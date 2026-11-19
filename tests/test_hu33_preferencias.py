"""HU-33 Preferencias de traduccion: endpoints /configuracion-traduccion y valores puntuales en /traducciones."""

from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.models.glosario.glosario import Glosario
from app.models.traduccion.configuracion_traduccion import ConfiguracionTraduccion
from app.models.traduccion.contexto import Contexto
from app.models.traduccion.idioma import Idioma
from app.models.traduccion.tono import Tono
from app.models.traduccion.variante_regional import VarianteRegional
from app.core.configuracion import configuracion
from tests.conftest import crear_usuario

PREFIJO = configuracion.api_v1_prefix
URL = f"{PREFIJO}/configuracion-traduccion"
URL_TRADUCIR = f"{PREFIJO}/traducciones"


# ---------------------------------------------------------------------------
# Datos de catalogo existentes (seeds)
# ---------------------------------------------------------------------------


@pytest.fixture()
def catalogo(sesion):
    contextos = sesion.scalars(
        select(Contexto)
        .where(Contexto.activo.is_(True), Contexto.id_usuario.is_(None))
        .order_by(Contexto.id_contexto)
    ).all()
    tonos = sesion.scalars(
        select(Tono).where(Tono.activo.is_(True)).order_by(Tono.id_tono)
    ).all()
    variante = sesion.scalar(
        select(VarianteRegional)
        .where(VarianteRegional.activo.is_(True))
        .order_by(VarianteRegional.id_variante_regional)
    )
    if len(contextos) < 2 or len(tonos) < 2 or variante is None:
        pytest.skip("Se necesitan seeds de contextos, tonos y variantes regionales.")

    idioma_variante = sesion.get(Idioma, variante.id_idioma)
    otro_idioma = sesion.scalar(
        select(Idioma).where(Idioma.id_idioma != variante.id_idioma).order_by(Idioma.id_idioma)
    )
    return SimpleNamespace(
        contextos=contextos,
        tonos=tonos,
        variante=variante,
        idioma_variante=idioma_variante,
        otro_idioma=otro_idioma,
    )


def crear_glosario(sesion, id_usuario, id_origen, id_destino) -> Glosario:
    glosario = Glosario(
        nombre="Glosario prueba",
        id_usuario=id_usuario,
        id_idioma_origen=id_origen,
        id_idioma_destino=id_destino,
    )
    sesion.add(glosario)
    sesion.commit()
    sesion.refresh(glosario)
    return glosario


def payload_completo(catalogo, **cambios) -> dict:
    datos = {
        "id_contexto": catalogo.contextos[1].id_contexto,
        "id_tono": catalogo.tonos[1].id_tono,
        "id_variante_regional": catalogo.variante.id_variante_regional,
        "idioma_destino": catalogo.idioma_variante.codigo,
        "explicar_expresiones": True,
        "generar_alternativas": True,
    }
    datos.update(cambios)
    return datos


# ---------------------------------------------------------------------------
# Guardar y consultar preferencias
# ---------------------------------------------------------------------------


def test_sin_preferencias_responde_404(cliente):
    respuesta = cliente.get(URL)
    assert respuesta.status_code == 404


def test_guardar_y_consultar_todas_las_preferencias(cliente, sesion, usuario, catalogo):
    glosario = crear_glosario(
        sesion, usuario.id, catalogo.otro_idioma.id_idioma, catalogo.idioma_variante.id_idioma
    )

    respuesta = cliente.post(URL, json=payload_completo(catalogo, id_glosario=glosario.id_glosario))
    assert respuesta.status_code == 200, respuesta.text

    resultado = cliente.get(URL).json()["resultado"]
    assert resultado["id_contexto"] == catalogo.contextos[1].id_contexto
    assert resultado["id_tono"] == catalogo.tonos[1].id_tono
    assert resultado["id_variante_regional"] == catalogo.variante.id_variante_regional
    assert resultado["id_idioma_destino"] == catalogo.idioma_variante.id_idioma
    assert resultado["codigo_idioma_destino"] == catalogo.idioma_variante.codigo
    assert resultado["id_glosario"] == glosario.id_glosario
    assert resultado["nombre_glosario"] == glosario.nombre
    assert resultado["explicar_expresiones"] is True
    assert resultado["generar_alternativas"] is True


def test_actualizar_no_duplica_la_configuracion(cliente, sesion, usuario, catalogo):
    cliente.post(URL, json=payload_completo(catalogo))
    cliente.post(URL, json=payload_completo(catalogo, id_tono=catalogo.tonos[0].id_tono))

    filas = sesion.scalars(
        select(ConfiguracionTraduccion).where(ConfiguracionTraduccion.id_usuario == usuario.id)
    ).all()
    assert len(filas) == 1
    assert filas[0].id_tono == catalogo.tonos[0].id_tono


def test_rechaza_variante_incompatible_con_idioma_destino(cliente, catalogo):
    respuesta = cliente.post(
        URL, json=payload_completo(catalogo, idioma_destino=catalogo.otro_idioma.codigo)
    )
    assert respuesta.status_code == 400
    assert "no corresponde al idioma de destino" in respuesta.json()["mensaje"]


def test_rechaza_glosario_de_otro_idioma_destino(cliente, sesion, usuario, catalogo):
    glosario = crear_glosario(
        sesion, usuario.id, catalogo.idioma_variante.id_idioma, catalogo.otro_idioma.id_idioma
    )
    respuesta = cliente.post(URL, json=payload_completo(catalogo, id_glosario=glosario.id_glosario))
    assert respuesta.status_code == 400
    assert "glosario" in respuesta.json()["mensaje"].lower()


def test_rechaza_glosario_de_otro_usuario(cliente, sesion, catalogo):
    otro = crear_usuario(sesion)
    glosario = crear_glosario(
        sesion, otro.id, catalogo.otro_idioma.id_idioma, catalogo.idioma_variante.id_idioma
    )
    respuesta = cliente.post(URL, json=payload_completo(catalogo, id_glosario=glosario.id_glosario))
    assert respuesta.status_code == 400


def test_rechaza_contexto_personalizado_de_otro_usuario(cliente, sesion, catalogo):
    otro = crear_usuario(sesion)
    contexto_ajeno = Contexto(nombre="Ajeno", personalizado=True, activo=True, id_usuario=otro.id)
    sesion.add(contexto_ajeno)
    sesion.commit()

    respuesta = cliente.post(
        URL, json=payload_completo(catalogo, id_contexto=contexto_ajeno.id_contexto)
    )
    assert respuesta.status_code == 400


def test_preferencias_son_por_usuario(cliente, sesion, catalogo):
    cliente.post(URL, json=payload_completo(catalogo))
    otro = crear_usuario(sesion)
    config_otro = sesion.scalar(
        select(ConfiguracionTraduccion).where(ConfiguracionTraduccion.id_usuario == otro.id)
    )
    assert config_otro is None


# ---------------------------------------------------------------------------
# Restablecer valores por defecto
# ---------------------------------------------------------------------------


def test_restablecer_valores_por_defecto(cliente, catalogo):
    cliente.post(URL, json=payload_completo(catalogo))

    respuesta = cliente.delete(URL)
    assert respuesta.status_code == 200, respuesta.text
    resultado = respuesta.json()["resultado"]
    assert resultado["id_contexto"] == catalogo.contextos[0].id_contexto
    assert resultado["id_tono"] == catalogo.tonos[0].id_tono
    assert resultado["id_variante_regional"] is None
    assert resultado["id_idioma_destino"] is None
    assert resultado["id_glosario"] is None
    assert resultado["explicar_expresiones"] is False
    assert resultado["generar_alternativas"] is False

    # Se mantiene entre peticiones (persistido)
    assert cliente.get(URL).json()["resultado"]["id_tono"] == catalogo.tonos[0].id_tono


def test_restablecer_sin_preferencias_previas_las_crea(cliente, catalogo):
    respuesta = cliente.delete(URL)
    assert respuesta.status_code == 200
    assert cliente.get(URL).status_code == 200


# ---------------------------------------------------------------------------
# Traduccion puntual: usa valores enviados sin modificar los guardados
# ---------------------------------------------------------------------------


@pytest.fixture()
def traduccion_simulada(monkeypatch):
    """Reemplaza el motor de traduccion (NLLB + LLM) y registra con que valores fue llamado."""
    llamadas: list[dict] = []

    def falso_traducir(**kwargs):
        llamadas.append(kwargs)
        return SimpleNamespace(
            texto_origen=kwargs["texto"],
            idioma_origen=kwargs["idioma_origen"] or "es",
            idioma_destino=kwargs["idioma_destino"],
            traduccion="hello",
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
            # Sin ids de idioma no se guarda en el historial
            id_idioma_origen=None,
            id_idioma_destino=None,
        )

    monkeypatch.setattr("app.api.routes.traducciones.traducir_con_configuracion", falso_traducir)
    return llamadas


def test_traduccion_usa_preferencias_guardadas(cliente, catalogo, traduccion_simulada):
    cliente.post(URL, json=payload_completo(catalogo))

    respuesta = cliente.post(
        URL_TRADUCIR, json={"texto": "hola", "idioma_origen": "es", "idioma_destino": "en"}
    )
    assert respuesta.status_code == 200, respuesta.text
    llamada = traduccion_simulada[0]
    assert llamada["nombre_contexto"] == catalogo.contextos[1].nombre
    assert llamada["nombre_tono"] == catalogo.tonos[1].nombre
    assert llamada["variante"].id_variante_regional == catalogo.variante.id_variante_regional
    assert llamada["generar_alternativas"] is True


def test_valor_puntual_no_modifica_preferencias(cliente, catalogo, traduccion_simulada):
    cliente.post(URL, json=payload_completo(catalogo))

    respuesta = cliente.post(
        URL_TRADUCIR,
        json={
            "texto": "hola",
            "idioma_origen": "es",
            "idioma_destino": "en",
            "id_contexto": catalogo.contextos[0].id_contexto,
            "id_tono": catalogo.tonos[0].id_tono,
            "id_variante_regional": None,
            "generar_alternativas": False,
        },
    )
    assert respuesta.status_code == 200, respuesta.text
    llamada = traduccion_simulada[0]
    assert llamada["nombre_contexto"] == catalogo.contextos[0].nombre
    assert llamada["nombre_tono"] == catalogo.tonos[0].nombre
    assert llamada["variante"] is None
    assert llamada["generar_alternativas"] is False
    assert llamada["explicar_expresiones"] is True  # no enviado: se usa el guardado

    resultado = respuesta.json()["resultado"]
    assert resultado["id_tono"] == catalogo.tonos[0].id_tono
    assert resultado["id_variante_regional"] is None

    guardada = cliente.get(URL).json()["resultado"]
    assert guardada["id_contexto"] == catalogo.contextos[1].id_contexto
    assert guardada["id_tono"] == catalogo.tonos[1].id_tono
    assert guardada["id_variante_regional"] == catalogo.variante.id_variante_regional
    assert guardada["generar_alternativas"] is True


def test_valor_puntual_invalido_responde_400(cliente, catalogo, traduccion_simulada):
    cliente.post(URL, json=payload_completo(catalogo))
    respuesta = cliente.post(
        URL_TRADUCIR,
        json={"texto": "hola", "idioma_destino": "en", "id_tono": 999999},
    )
    assert respuesta.status_code == 400
    assert traduccion_simulada == []

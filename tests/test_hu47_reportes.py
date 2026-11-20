"""
HU-47 Reportes administrativos: GET /reportes/actividad.

Usa los datos de prueba de marzo de 2001 (fixture `datos` de conftest): 3 traducciones de
texto es→en (contexto 0), 2 documentos es→fr (1 completado y 1 con error) y 1 conversacion
en→es (contexto 1).
"""

import pytest

from app.core.configuracion import configuracion
from tests.conftest import crear_usuario

URL = f"{configuracion.api_v1_prefix}/reportes/actividad"
MARZO = {"fecha_desde": "2001-03-01", "fecha_hasta": "2001-03-31", "zona_horaria": "America/La_Paz"}


def generar(cliente, **filtros):
    return cliente.get(URL, params={**MARZO, **filtros})


# ---------------------------------------------------------------------------
# Acceso
# ---------------------------------------------------------------------------


def test_usuario_sin_rol_admin_recibe_403(cliente_como, sesion, admin):
    normal = crear_usuario(sesion, "USUARIO")
    assert cliente_como(normal).get(URL).status_code == 403


def test_sin_token_responde_401(cliente_como):
    assert cliente_como(None).get(URL).status_code == 401


# ---------------------------------------------------------------------------
# Detalle y totales
# ---------------------------------------------------------------------------


def test_reporte_sin_filtros_muestra_detalle_y_totales(cliente_admin, datos):
    respuesta = generar(cliente_admin)
    assert respuesta.status_code == 200, respuesta.text
    r = respuesta.json()["resultado"]

    assert r["totales"] == {
        "total": 6,
        "texto": 3,
        "documento": 2,
        "conversacion": 1,
        "sesion_externa": 0,
        "sesion_externa_disponible": True,
    }
    assert len(r["actividades"]) == 6
    # Ordenado de lo mas reciente a lo mas antiguo
    fechas = [a["fecha"] for a in r["actividades"]]
    assert fechas == sorted(fechas, reverse=True)

    conversacion = r["actividades"][0]
    assert conversacion["tipo_servicio"] == "conversacion"
    assert conversacion["idioma_origen"] == datos["idiomas"]["en"].nombre
    assert conversacion["contexto"] == datos["contextos"][1].nombre
    assert conversacion["correo_usuario"] == datos["usuarios"][1].correo
    assert conversacion["detalle"]  # nombre del entorno


def test_el_detalle_no_incluye_el_texto_de_los_usuarios(cliente_admin, datos):
    actividades = generar(cliente_admin).json()["resultado"]["actividades"]
    for actividad in actividades:
        assert "hola" not in str(actividad.values())
        assert "hello" not in str(actividad.values())


@pytest.mark.parametrize(
    ("tipo", "total"),
    [("texto", 3), ("documento", 2), ("conversacion", 1), ("sesion_externa", 0)],
)
def test_filtro_por_tipo_de_servicio(cliente_admin, datos, tipo, total):
    r = generar(cliente_admin, tipo_servicio=tipo).json()["resultado"]
    assert r["totales"]["total"] == total
    assert {a["tipo_servicio"] for a in r["actividades"]} <= {tipo}
    assert r["filtros"]["tipo_servicio"] == tipo


def test_filtro_por_idiomas(cliente_admin, datos):
    idiomas = datos["idiomas"]
    r = generar(cliente_admin, id_idioma_origen=idiomas["es"].id_idioma).json()["resultado"]
    assert r["totales"]["total"] == 5  # 3 textos + 2 documentos

    r = generar(cliente_admin, id_idioma_destino=idiomas["fr"].id_idioma).json()["resultado"]
    assert r["totales"]["total"] == 2
    assert r["filtros"]["nombre_idioma_destino"] == idiomas["fr"].nombre


def test_filtro_por_contexto(cliente_admin, datos):
    contextos = datos["contextos"]
    r = generar(cliente_admin, id_contexto=contextos[0].id_contexto).json()["resultado"]
    assert r["totales"] == {**r["totales"], "total": 3, "texto": 3}
    assert r["filtros"]["nombre_contexto"] == contextos[0].nombre


def test_los_filtros_se_combinan(cliente_admin, datos):
    idiomas = datos["idiomas"]
    r = generar(
        cliente_admin,
        tipo_servicio="documento",
        id_idioma_origen=idiomas["es"].id_idioma,
        id_idioma_destino=idiomas["fr"].id_idioma,
        fecha_desde="2001-03-06",
        fecha_hasta="2001-03-06",
    ).json()["resultado"]
    assert r["totales"]["total"] == 2

    r = generar(
        cliente_admin, tipo_servicio="documento", id_idioma_destino=idiomas["en"].id_idioma
    ).json()["resultado"]
    assert r["totales"]["total"] == 0


def test_sin_resultados_informa(cliente_admin, datos):
    respuesta = generar(cliente_admin, fecha_desde="2001-04-01", fecha_hasta="2001-04-30")
    assert respuesta.status_code == 200
    assert respuesta.json()["resultado"]["totales"]["total"] == 0
    assert respuesta.json()["resultado"]["actividades"] == []
    assert "No se encontraron" in respuesta.json()["mensaje"]


def test_paginacion(cliente_admin, datos):
    pagina_1 = generar(cliente_admin, tamano_pagina=4, pagina=1).json()["resultado"]
    pagina_2 = generar(cliente_admin, tamano_pagina=4, pagina=2).json()["resultado"]

    assert pagina_1["total_paginas"] == 2
    assert len(pagina_1["actividades"]) == 4
    assert len(pagina_2["actividades"]) == 2
    # Los totales son del reporte completo, no de la pagina
    assert pagina_2["totales"]["total"] == 6
    ids_1 = {(a["tipo_servicio"], a["id_registro"]) for a in pagina_1["actividades"]}
    ids_2 = {(a["tipo_servicio"], a["id_registro"]) for a in pagina_2["actividades"]}
    assert not ids_1 & ids_2


# ---------------------------------------------------------------------------
# Validaciones
# ---------------------------------------------------------------------------


def test_fecha_inicial_posterior_a_final_responde_400(cliente_admin):
    respuesta = generar(cliente_admin, fecha_desde="2001-03-10", fecha_hasta="2001-03-01")
    assert respuesta.status_code == 400
    assert "posterior" in respuesta.json()["mensaje"]


def test_tipo_de_servicio_invalido_responde_422(cliente_admin):
    assert generar(cliente_admin, tipo_servicio="otro").status_code == 422


@pytest.mark.parametrize("filtro", ["id_idioma_origen", "id_idioma_destino", "id_contexto"])
def test_filtro_inexistente_responde_400(cliente_admin, filtro):
    assert generar(cliente_admin, **{filtro: 999999}).status_code == 400

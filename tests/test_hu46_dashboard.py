"""
HU-46 Dashboard administrativo: GET /dashboard.

Usa los datos de prueba de marzo de 2001 (fixture `datos` de conftest) para que el periodo
consultado no incluya datos reales de la base local y los totales sean exactos.
"""

from datetime import date

from sqlalchemy import select

from app.core.configuracion import configuracion
from app.models.traduccion.configuracion_traduccion import ConfiguracionTraduccion
from app.models.traduccion.traduccion import Traduccion
from app.models.usuario.sesion import Sesion
from tests.conftest import crear_usuario, momento

URL = f"{configuracion.api_v1_prefix}/dashboard"
ZONA = "America/La_Paz"  # UTC-4


def consultar(cliente, desde: str, hasta: str, zona: str = ZONA):
    return cliente.get(URL, params={"fecha_desde": desde, "fecha_hasta": hasta, "zona_horaria": zona})


# ---------------------------------------------------------------------------
# Acceso
# ---------------------------------------------------------------------------


def test_usuario_sin_rol_admin_recibe_403(cliente_como, sesion, admin):
    normal = crear_usuario(sesion, "USUARIO")
    assert cliente_como(normal).get(URL).status_code == 403


def test_sin_token_responde_401(cliente_como):
    assert cliente_como(None).get(URL).status_code == 401


# ---------------------------------------------------------------------------
# Indicadores
# ---------------------------------------------------------------------------


def test_indicadores_con_datos_reales(cliente_admin, datos):
    respuesta = consultar(cliente_admin, "2001-03-01", "2001-03-31")
    assert respuesta.status_code == 200, respuesta.text
    r = respuesta.json()["resultado"]

    assert r["usuarios"] == {"total": 2, "activos_periodo": 2, "nuevos_periodo": 2}
    assert r["actividad"] == {
        "traducciones_texto": 3,
        "documentos_traducidos": 1,  # el documento con error no cuenta
        "conversaciones": 1,
        "sesiones_externas": 0,
        "sesiones_externas_disponible": True,
    }


def test_idiomas_y_contextos_mas_utilizados(cliente_admin, datos):
    r = consultar(cliente_admin, "2001-03-01", "2001-03-31").json()["resultado"]

    # es: 3 (texto) + 2 (documentos) + 1 (conversacion); en: 3 + 1; fr: 2
    assert [(i["codigo"], i["total"]) for i in r["idiomas_mas_utilizados"]] == [
        ("es", 6), ("en", 4), ("fr", 2),
    ]
    contextos = datos["contextos"]
    assert [(c["id_contexto"], c["total"]) for c in r["contextos_mas_utilizados"]] == [
        (contextos[0].id_contexto, 3), (contextos[1].id_contexto, 1),
    ]


def test_evolucion_diaria_incluye_dias_sin_actividad(cliente_admin, datos):
    r = consultar(cliente_admin, "2001-03-04", "2001-03-08").json()["resultado"]

    assert r["periodo"]["agrupacion"] == "dia"
    puntos = {p["fecha"]: p for p in r["evolucion"]}
    assert list(puntos) == ["2001-03-04", "2001-03-05", "2001-03-06", "2001-03-07", "2001-03-08"]
    assert puntos["2001-03-04"]["traducciones_texto"] == 0
    assert puntos["2001-03-05"]["traducciones_texto"] == 2
    assert puntos["2001-03-06"]["traducciones_texto"] == 1
    assert puntos["2001-03-06"]["documentos"] == 1
    assert puntos["2001-03-07"]["conversaciones"] == 1


def test_evolucion_mensual_en_periodos_largos(cliente_admin, datos):
    r = consultar(cliente_admin, "2001-01-01", "2001-12-31").json()["resultado"]

    assert r["periodo"]["agrupacion"] == "mes"
    assert len(r["evolucion"]) == 12
    marzo = next(p for p in r["evolucion"] if p["fecha"] == "2001-03-01")
    assert marzo["traducciones_texto"] == 3


def test_el_periodo_filtra_la_actividad(cliente_admin, datos):
    r = consultar(cliente_admin, "2001-03-06", "2001-03-06").json()["resultado"]
    assert r["actividad"]["traducciones_texto"] == 1
    assert r["actividad"]["conversaciones"] == 0
    assert r["usuarios"]["nuevos_periodo"] == 0
    assert r["usuarios"]["total"] == 2


def test_usuario_activo_por_inicio_de_sesion(cliente_admin, sesion, datos):
    usuario_a, _ = datos["usuarios"]
    sesion.add(Sesion(
        token="tok-dashboard-prueba", fecha_inicio=momento(20), fecha_expiracion=momento(21),
        estado="CERRADA", id_usuario=usuario_a.id,
    ))
    sesion.commit()

    r = consultar(cliente_admin, "2001-03-20", "2001-03-20").json()["resultado"]
    assert r["usuarios"]["activos_periodo"] == 1


def test_fechas_se_interpretan_en_la_zona_horaria(cliente_admin, sesion, datos):
    usuario_a, _ = datos["usuarios"]
    config = sesion.scalar(
        select(ConfiguracionTraduccion).where(ConfiguracionTraduccion.id_usuario == usuario_a.id)
    )
    idiomas = datos["idiomas"]
    # 10/03 02:00 UTC = 09/03 22:00 en La Paz
    sesion.add(Traduccion(
        texto_original="x", texto_traducido="y", fecha_creacion=momento(10, hora=2),
        id_configuracion_traduccion=config.id_configuracion_traduccion,
        id_idioma_origen=idiomas["es"].id_idioma, id_idioma_destino=idiomas["en"].id_idioma,
        id_usuario=usuario_a.id,
    ))
    sesion.commit()

    en_la_paz = consultar(cliente_admin, "2001-03-09", "2001-03-09").json()["resultado"]
    en_utc = consultar(cliente_admin, "2001-03-09", "2001-03-09", zona="UTC").json()["resultado"]
    assert en_la_paz["actividad"]["traducciones_texto"] == 1
    assert en_utc["actividad"]["traducciones_texto"] == 0


# ---------------------------------------------------------------------------
# Validaciones del periodo
# ---------------------------------------------------------------------------


def test_periodo_por_defecto_ultimos_30_dias(cliente_admin):
    r = cliente_admin.get(URL, params={"zona_horaria": ZONA}).json()["resultado"]
    desde = date.fromisoformat(r["periodo"]["fecha_desde"])
    hasta = date.fromisoformat(r["periodo"]["fecha_hasta"])
    assert (hasta - desde).days == 29
    assert len(r["evolucion"]) == 30


def test_fecha_inicial_posterior_a_final_responde_400(cliente_admin):
    respuesta = consultar(cliente_admin, "2001-03-10", "2001-03-01")
    assert respuesta.status_code == 400
    assert "posterior" in respuesta.json()["mensaje"]


def test_periodo_mayor_a_dos_anos_responde_400(cliente_admin):
    assert consultar(cliente_admin, "2001-01-01", "2004-01-01").status_code == 400


def test_zona_horaria_invalida_responde_400(cliente_admin):
    assert consultar(cliente_admin, "2001-03-01", "2001-03-31", zona="Marte/Base").status_code == 400

"""HU-32 Glosarios personalizados, criterio 4: aplicar el glosario en conversaciones."""

from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.core.configuracion import configuracion
from app.models.conversacion.entorno import Entorno
from app.models.glosario.glosario import Glosario
from app.models.traduccion.idioma import Idioma
from app.services import intervenciones as servicio_intervenciones
from tests.conftest import crear_usuario

URL = f"{configuracion.api_v1_prefix}/conversaciones"


@pytest.fixture()
def catalogo(sesion):
    idiomas = {
        i.codigo: i for i in sesion.scalars(select(Idioma).where(Idioma.codigo.in_(["es", "en", "fr"])))
    }
    entorno = sesion.scalar(select(Entorno).where(Entorno.activo.is_(True)).order_by(Entorno.id_entorno))
    if len(idiomas) < 3 or entorno is None:
        pytest.skip("Se necesitan seeds de idiomas (es, en, fr) y entornos.")
    return SimpleNamespace(idiomas=idiomas, entorno=entorno)


def crear_glosario(sesion, id_usuario, origen: Idioma, destino: Idioma, nombre="Glosario prueba") -> Glosario:
    glosario = Glosario(
        nombre=nombre,
        id_usuario=id_usuario,
        id_idioma_origen=origen.id_idioma,
        id_idioma_destino=destino.id_idioma,
    )
    sesion.add(glosario)
    sesion.commit()
    sesion.refresh(glosario)
    return glosario


def iniciar(cliente, catalogo, **extra):
    datos = {
        "id_idioma_origen": catalogo.idiomas["es"].id_idioma,
        "id_idioma_destino": catalogo.idiomas["en"].id_idioma,
        "id_entorno": catalogo.entorno.id_entorno,
        "mantener_contexto": False,
    }
    datos.update(extra)
    return cliente.post(URL, json=datos)


@pytest.fixture()
def traduccion_simulada(monkeypatch):
    """Sustituye la traduccion central y registra los argumentos con que se llamo."""
    llamadas = []

    def falsa(**kwargs):
        llamadas.append(kwargs)
        return SimpleNamespace(traduccion="traducido", estilo_aplicado=False)

    monkeypatch.setattr(servicio_intervenciones, "traducir_con_configuracion", falsa)
    return llamadas


def test_iniciar_con_glosario_del_par(cliente, sesion, usuario, catalogo):
    glosario = crear_glosario(sesion, usuario.id, catalogo.idiomas["es"], catalogo.idiomas["en"])
    respuesta = iniciar(cliente, catalogo, id_glosario=glosario.id_glosario)
    assert respuesta.status_code == 201
    resultado = respuesta.json()["resultado"]
    assert resultado["id_glosario"] == glosario.id_glosario
    assert resultado["nombre_glosario"] == "Glosario prueba"
    assert resultado["par_idiomas_glosario"] == "ES → EN"


def test_iniciar_acepta_glosario_en_sentido_inverso(cliente, sesion, usuario, catalogo):
    glosario = crear_glosario(sesion, usuario.id, catalogo.idiomas["en"], catalogo.idiomas["es"])
    respuesta = iniciar(cliente, catalogo, id_glosario=glosario.id_glosario)
    assert respuesta.status_code == 201
    assert respuesta.json()["resultado"]["par_idiomas_glosario"] == "EN → ES"


def test_rechaza_glosario_de_otro_par(cliente, sesion, usuario, catalogo):
    glosario = crear_glosario(sesion, usuario.id, catalogo.idiomas["es"], catalogo.idiomas["fr"])
    respuesta = iniciar(cliente, catalogo, id_glosario=glosario.id_glosario)
    assert respuesta.status_code == 400
    assert "no corresponde" in respuesta.json()["mensaje"]


def test_rechaza_glosario_de_otro_usuario(cliente, sesion, catalogo):
    otro = crear_usuario(sesion)
    glosario = crear_glosario(sesion, otro.id, catalogo.idiomas["es"], catalogo.idiomas["en"])
    respuesta = iniciar(cliente, catalogo, id_glosario=glosario.id_glosario)
    assert respuesta.status_code == 400


def test_patch_cambia_y_quita_glosario(cliente, sesion, usuario, catalogo):
    glosario = crear_glosario(sesion, usuario.id, catalogo.idiomas["es"], catalogo.idiomas["en"])
    id_conversacion = iniciar(cliente, catalogo).json()["resultado"]["id_conversacion"]

    respuesta = cliente.patch(f"{URL}/{id_conversacion}", json={"id_glosario": glosario.id_glosario})
    assert respuesta.status_code == 200
    assert respuesta.json()["resultado"]["id_glosario"] == glosario.id_glosario

    respuesta = cliente.patch(f"{URL}/{id_conversacion}", json={"id_glosario": None})
    assert respuesta.status_code == 200
    assert respuesta.json()["resultado"]["id_glosario"] is None


def test_glosario_solo_se_aplica_en_su_sentido(cliente, sesion, usuario, catalogo, traduccion_simulada):
    glosario = crear_glosario(sesion, usuario.id, catalogo.idiomas["es"], catalogo.idiomas["en"])
    conversacion = iniciar(cliente, catalogo, id_glosario=glosario.id_glosario).json()["resultado"]
    p1, p2 = sorted(conversacion["participantes"], key=lambda p: p["orden"])
    url = f"{URL}/{conversacion['id_conversacion']}/intervenciones"

    # Participante 1 habla espanol: ES -> EN, mismo sentido que el glosario
    respuesta = cliente.post(url, json={"id_participante": p1["id_participante"], "texto": "Hola"})
    assert respuesta.status_code == 201
    assert traduccion_simulada[-1]["id_glosario"] == glosario.id_glosario

    # Participante 2 habla ingles: EN -> ES, sentido contrario, se traduce sin glosario
    respuesta = cliente.post(url, json={"id_participante": p2["id_participante"], "texto": "Hello"})
    assert respuesta.status_code == 201
    assert traduccion_simulada[-1]["id_glosario"] is None


def test_sin_glosario_no_se_envia(cliente, catalogo, traduccion_simulada):
    conversacion = iniciar(cliente, catalogo).json()["resultado"]
    p1 = min(conversacion["participantes"], key=lambda p: p["orden"])
    url = f"{URL}/{conversacion['id_conversacion']}/intervenciones"
    cliente.post(url, json={"id_participante": p1["id_participante"], "texto": "Hola"})
    assert traduccion_simulada[-1]["id_glosario"] is None


def test_eliminar_glosario_deja_la_conversacion_sin_glosario(cliente, sesion, usuario, catalogo):
    glosario = crear_glosario(sesion, usuario.id, catalogo.idiomas["es"], catalogo.idiomas["en"])
    id_conversacion = iniciar(cliente, catalogo, id_glosario=glosario.id_glosario).json()["resultado"][
        "id_conversacion"
    ]
    respuesta = cliente.delete(f"{configuracion.api_v1_prefix}/glosarios/{glosario.id_glosario}")
    assert respuesta.status_code == 200
    sesion.expire_all()

    respuesta = cliente.get(f"{URL}/{id_conversacion}")
    assert respuesta.status_code == 200
    assert respuesta.json()["resultado"]["id_glosario"] is None

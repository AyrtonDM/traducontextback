"""
Historial (HU-42): la traduccion automatica mientras se escribe no se guarda
(`guardar_en_historial: false`) y el cliente registra la traduccion terminada con
POST /traducciones/historial, sin volver a traducir.
"""

from sqlalchemy import func, select

from app.models.glosario.glosario import Glosario
from app.models.traduccion.traduccion import Traduccion
from tests.conftest import crear_usuario
from tests.test_hu44_reutilizacion import (  # noqa: F401 - fixtures reutilizadas
    URL_TRADUCIR,
    config,
    configurar,
    idiomas,
    traduccion_simulada,
)

URL_HISTORIAL = f"{URL_TRADUCIR}/historial"


def contar(sesion, usuario) -> int:
    return sesion.scalar(select(func.count()).select_from(Traduccion).where(Traduccion.id_usuario == usuario.id))


def test_traduccion_automatica_no_se_guarda(cliente, sesion, usuario, config, traduccion_simulada):
    respuesta = cliente.post(
        URL_TRADUCIR,
        json={"texto": "hola eq", "idioma_origen": "es", "idioma_destino": "en", "guardar_en_historial": False},
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["resultado"]["id_traduccion"] is None
    assert contar(sesion, usuario) == 0


def test_por_defecto_se_sigue_guardando(cliente, sesion, usuario, config, traduccion_simulada):
    """Compatibilidad con otros clientes (p. ej. movil) que no envian el campo."""
    respuesta = cliente.post(URL_TRADUCIR, json={"texto": "hola", "idioma_origen": "es", "idioma_destino": "en"})
    assert respuesta.json()["resultado"]["id_traduccion"] is not None
    assert contar(sesion, usuario) == 1


def test_registrar_traduccion_terminada(cliente, sesion, usuario, config, idiomas):
    respuesta = cliente.post(
        URL_HISTORIAL,
        json={
            "texto_original": "  hola equipo ",
            "texto_traducido": "hi team",  # p. ej. una alternativa elegida por el usuario
            "idioma_origen": "ES",
            "idioma_destino": "en",
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    id_traduccion = respuesta.json()["resultado"]["id_traduccion"]

    registro = sesion.get(Traduccion, id_traduccion)
    assert registro.id_usuario == usuario.id
    assert registro.texto_original == "hola equipo"
    assert registro.texto_traducido == "hi team"
    assert registro.id_idioma_origen == idiomas["es"].id_idioma
    assert registro.id_idioma_destino == idiomas["en"].id_idioma

    # Aparece en el historial del usuario
    historial = cliente.get(URL_HISTORIAL).json()["resultado"]
    assert [h["id_traduccion"] for h in historial] == [id_traduccion]


def test_registrar_con_glosario_del_mismo_par(cliente, sesion, usuario, config, idiomas):
    glosario = Glosario(nombre="G", id_usuario=usuario.id,
                        id_idioma_origen=idiomas["es"].id_idioma, id_idioma_destino=idiomas["en"].id_idioma)
    sesion.add(glosario)
    sesion.commit()

    datos = {"texto_original": "hola", "texto_traducido": "hi", "idioma_origen": "es",
             "idioma_destino": "en", "id_glosario": glosario.id_glosario}
    assert cliente.post(URL_HISTORIAL, json=datos).status_code == 201
    # Glosario de otro par de idiomas
    assert cliente.post(URL_HISTORIAL, json={**datos, "idioma_destino": "fr"}).status_code == 400


def test_registrar_valida_datos(cliente, sesion, usuario, config):
    base = {"texto_original": "hola", "texto_traducido": "hi", "idioma_origen": "es", "idioma_destino": "en"}
    assert cliente.post(URL_HISTORIAL, json={**base, "texto_original": "   "}).status_code == 422
    assert cliente.post(URL_HISTORIAL, json={**base, "idioma_destino": "xx"}).status_code == 400
    assert cliente.post(URL_HISTORIAL, json={**base, "id_glosario": 999999}).status_code == 404


def test_registrar_sin_configuracion_responde_400(cliente_como, sesion):
    sin_config = crear_usuario(sesion, "USUARIO")
    respuesta = cliente_como(sin_config).post(
        URL_HISTORIAL,
        json={"texto_original": "hola", "texto_traducido": "hi", "idioma_origen": "es", "idioma_destino": "en"},
    )
    assert respuesta.status_code == 400

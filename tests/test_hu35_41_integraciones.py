"""
HU-35 a HU-41: integracion con Google Meet y Zoom.

Todas las llamadas externas estan simuladas: OAuth y APIs de las plataformas (`plataformas._peticion`),
Whisper (`intervenciones_externas.transcribir`) y la traduccion (`traducir_con_configuracion`).
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select

from app.core import cifrado
from app.core.configuracion import configuracion
from app.models.conversacion.entorno import Entorno
from app.models.glosario.glosario import Glosario
from app.models.integracion.conexion_plataforma import ConexionPlataforma
from app.models.integracion.intervencion_externa import IntervencionExterna
from app.models.integracion.sesion_externa import SesionExterna
from app.models.traduccion.idioma import Idioma
from app.services import integraciones, intervenciones_externas, plataformas
from app.services.transcripcion import Transcripcion, TranscripcionError
from tests.conftest import crear_usuario, momento

PREFIJO = configuracion.api_v1_prefix
URL_INTEGRACIONES = f"{PREFIJO}/integraciones"
URL_SESIONES = f"{PREFIJO}/sesiones-externas"
ENLACE_MEET = "https://meet.google.com/abc-defg-hij?authuser=0"


# ---------------------------------------------------------------------------
# Infraestructura
# ---------------------------------------------------------------------------


@pytest.fixture()
def credenciales(monkeypatch):
    """Credenciales OAuth y clave de cifrado de prueba."""
    valores = {
        "clave_cifrado_tokens": Fernet.generate_key().decode(),
        "google_client_id": "google-id",
        "google_client_secret": "google-secreto",
        "google_redirect_uri": "http://api/integraciones/google_meet/callback",
        "zoom_client_id": "zoom-id",
        "zoom_client_secret": "zoom-secreto",
        "zoom_redirect_uri": "http://api/integraciones/zoom/callback",
        "frontend_url": "http://front",
    }
    for nombre, valor in valores.items():
        monkeypatch.setattr(configuracion, nombre, valor)
    return valores


class PlataformaSimulada:
    """Respuestas HTTP de Google y Zoom; registra cada peticion."""

    def __init__(self):
        self.peticiones = []
        self.fallar_token = False
        self.participantes_meet = [
            {"name": "conferenceRecords/c1/participants/p1", "signedinUser": {"displayName": "Ana Pérez"}},
            {"name": "conferenceRecords/c1/participants/p2", "anonymousUser": {"displayName": "John"}},
        ]
        self.fallar_participantes = False
        self.contador_tokens = 0

    def __call__(self, metodo, url, **kwargs):
        self.peticiones.append((metodo, url, kwargs))
        peticion = httpx.Request(metodo, url)
        if url.endswith("/token"):
            if self.fallar_token:
                return httpx.Response(400, json={"error": "invalid_grant"}, request=peticion)
            self.contador_tokens += 1
            return httpx.Response(200, json={
                "access_token": f"acceso-{self.contador_tokens}",
                "refresh_token": "renovar-1",
                "expires_in": 3600,
                "scope": "openid email",
            }, request=peticion)
        if "revoke" in url:
            return httpx.Response(200, json={}, request=peticion)
        if "userinfo" in url or url.endswith("/users/me"):
            return httpx.Response(200, json={"email": "persona@ejemplo.com"}, request=peticion)
        if url.endswith("/conferenceRecords"):
            if self.fallar_participantes:
                return httpx.Response(403, json={}, request=peticion)
            return httpx.Response(200, json={"conferenceRecords": [{"name": "conferenceRecords/c1"}]}, request=peticion)
        if url.endswith("/participants"):
            return httpx.Response(200, json={"participants": self.participantes_meet}, request=peticion)
        return httpx.Response(404, json={}, request=peticion)


@pytest.fixture()
def plataforma(monkeypatch, credenciales):
    simulada = PlataformaSimulada()
    monkeypatch.setattr(plataformas, "_peticion", simulada)
    return simulada


def autorizar_y_volver(cliente, plataforma_codigo="google_meet", codigo="codigo-ok"):
    url = cliente.post(f"{URL_INTEGRACIONES}/{plataforma_codigo}/autorizar").json()["resultado"]["url_autorizacion"]
    estado = parse_qs(urlparse(url).query)["state"][0]
    return cliente.get(
        f"{URL_INTEGRACIONES}/{plataforma_codigo}/callback",
        params={"code": codigo, "state": estado},
        follow_redirects=False,
    )


def resultado_redireccion(respuesta) -> dict:
    assert respuesta.status_code == 302
    destino = urlparse(respuesta.headers["location"])
    assert destino.path == "/integraciones"
    return {k: v[0] for k, v in parse_qs(destino.query).items()}


@pytest.fixture()
def vinculado(cliente, plataforma):
    assert resultado_redireccion(autorizar_y_volver(cliente))["resultado"] == "vinculada"
    return plataforma


@pytest.fixture()
def catalogo(sesion):
    idiomas = {i.codigo: i for i in sesion.scalars(select(Idioma).where(Idioma.codigo.in_(["es", "en", "fr"])))}
    entorno = sesion.scalar(select(Entorno).where(Entorno.activo.is_(True)).order_by(Entorno.id_entorno))
    if len(idiomas) < 3 or entorno is None:
        pytest.skip("Se necesitan seeds de idiomas (es, en, fr) y entornos.")
    return SimpleNamespace(idiomas=idiomas, entorno=entorno)


def crear_sesion(cliente, catalogo, **extra):
    datos = {
        "plataforma": "google_meet",
        "enlace_reunion": ENLACE_MEET,
        "id_idioma_origen": catalogo.idiomas["es"].id_idioma,
        "id_idioma_destino": catalogo.idiomas["en"].id_idioma,
        "id_entorno": catalogo.entorno.id_entorno,
    }
    datos.update(extra)
    return cliente.post(URL_SESIONES, json=datos)


@pytest.fixture()
def sesion_activa(cliente, catalogo, vinculado):
    creada = crear_sesion(cliente, catalogo).json()["resultado"]
    assert cliente.post(f"{URL_SESIONES}/{creada['id_sesion_externa']}/iniciar").status_code == 200
    return creada


@pytest.fixture()
def motor(monkeypatch):
    """Whisper y traduccion simulados. `motor.textos` es la cola de transcripciones a devolver."""
    estado = SimpleNamespace(textos=[], traducciones=[], fallar_traduccion=False, al_transcribir=None)

    def falso_transcribir(contenido, nombre, tipo, contexto_previo=None):
        if estado.al_transcribir:
            estado.al_transcribir()
        texto, idioma = estado.textos.pop(0)
        return Transcripcion(texto=texto, codigo_idioma=idioma)

    def falso_traducir(**kwargs):
        estado.traducciones.append(kwargs)
        if estado.fallar_traduccion:
            raise RuntimeError("LLM caido")
        return SimpleNamespace(traduccion=f"[{kwargs['idioma_destino']}] {kwargs['texto']}")

    monkeypatch.setattr(intervenciones_externas, "transcribir", falso_transcribir)
    monkeypatch.setattr(intervenciones_externas, "traducir_con_configuracion", falso_traducir)
    return estado


def enviar_audio(cliente, id_sesion, **form):
    return cliente.post(
        f"{URL_SESIONES}/{id_sesion}/audio",
        files={"audio": ("fragmento.webm", b"\x1a\x45\xdf\xa3audio", "audio/webm;codecs=opus")},
        data={k: str(v) for k, v in form.items()},
    )


# ---------------------------------------------------------------------------
# HU-35 Conexion con plataformas
# ---------------------------------------------------------------------------


def test_lista_las_dos_plataformas_con_permisos(cliente, credenciales):
    resultado = cliente.get(URL_INTEGRACIONES).json()["resultado"]
    assert [p["plataforma"] for p in resultado] == ["google_meet", "zoom"]
    for p in resultado:
        assert p["estado"] == "no_vinculada"
        assert p["configurada"] is True
        assert p["permisos"] and all(permiso["descripcion"] for permiso in p["permisos"])


def test_sin_credenciales_no_se_puede_vincular(cliente, monkeypatch):
    monkeypatch.setattr(configuracion, "google_client_id", "")
    assert cliente.get(URL_INTEGRACIONES).json()["resultado"][0]["configurada"] is False
    assert cliente.post(f"{URL_INTEGRACIONES}/google_meet/autorizar").status_code == 503


def test_url_de_autorizacion_oficial_con_permisos_minimos(cliente, credenciales):
    resultado = cliente.post(f"{URL_INTEGRACIONES}/google_meet/autorizar").json()["resultado"]
    url = urlparse(resultado["url_autorizacion"])
    parametros = parse_qs(url.query)
    assert url.netloc == "accounts.google.com"
    assert parametros["client_id"] == ["google-id"]
    assert set(parametros["scope"][0].split()) == {p["alcance"] for p in resultado["permisos"]}
    assert parametros["access_type"] == ["offline"]

    zoom = cliente.post(f"{URL_INTEGRACIONES}/zoom/autorizar").json()["resultado"]
    assert urlparse(zoom["url_autorizacion"]).netloc == "zoom.us"


def test_vincular_guarda_tokens_cifrados(cliente, sesion, usuario, plataforma):
    datos = resultado_redireccion(autorizar_y_volver(cliente))
    assert datos["resultado"] == "vinculada"

    conexion = sesion.scalar(select(ConexionPlataforma).where(ConexionPlataforma.id_usuario == usuario.id))
    assert conexion.access_token_cifrado != "acceso-1"
    assert cifrado.descifrar(conexion.access_token_cifrado) == "acceso-1"
    assert cifrado.descifrar(conexion.refresh_token_cifrado) == "renovar-1"

    google = cliente.get(URL_INTEGRACIONES).json()["resultado"][0]
    assert google["estado"] == "vinculada"
    assert google["cuenta_externa"] == "persona@ejemplo.com"
    assert "token" not in str(google).lower().replace("tokens", "")


def test_autorizacion_cancelada_no_vincula(cliente, sesion, usuario, plataforma):
    respuesta = cliente.get(
        f"{URL_INTEGRACIONES}/google_meet/callback", params={"error": "access_denied"}, follow_redirects=False
    )
    assert resultado_redireccion(respuesta)["resultado"] == "cancelada"
    assert sesion.scalar(select(ConexionPlataforma).where(ConexionPlataforma.id_usuario == usuario.id)) is None


def test_state_alterado_o_de_otra_plataforma_no_vincula(cliente, sesion, usuario, plataforma):
    respuesta = cliente.get(
        f"{URL_INTEGRACIONES}/google_meet/callback", params={"code": "x", "state": "falso"}, follow_redirects=False
    )
    assert resultado_redireccion(respuesta)["resultado"] == "error"

    url = cliente.post(f"{URL_INTEGRACIONES}/google_meet/autorizar").json()["resultado"]["url_autorizacion"]
    estado_google = parse_qs(urlparse(url).query)["state"][0]
    respuesta = cliente.get(
        f"{URL_INTEGRACIONES}/zoom/callback", params={"code": "x", "state": estado_google}, follow_redirects=False
    )
    assert resultado_redireccion(respuesta)["resultado"] == "error"
    assert sesion.scalar(select(ConexionPlataforma).where(ConexionPlataforma.id_usuario == usuario.id)) is None


def test_fallo_al_canjear_el_codigo_no_vincula(cliente, sesion, usuario, plataforma):
    plataforma.fallar_token = True
    assert resultado_redireccion(autorizar_y_volver(cliente))["resultado"] == "error"
    assert sesion.scalar(select(ConexionPlataforma).where(ConexionPlataforma.id_usuario == usuario.id)) is None


def test_estado_expirada(cliente, sesion, usuario, vinculado):
    conexion = sesion.scalar(select(ConexionPlataforma).where(ConexionPlataforma.id_usuario == usuario.id))
    conexion.fecha_expiracion = datetime.now(timezone.utc) - timedelta(hours=1)
    conexion.refresh_token_cifrado = None
    sesion.commit()
    assert cliente.get(URL_INTEGRACIONES).json()["resultado"][0]["estado"] == "expirada"


def test_token_caducado_se_renueva(cliente, sesion, usuario, vinculado):
    conexion = sesion.scalar(select(ConexionPlataforma).where(ConexionPlataforma.id_usuario == usuario.id))
    conexion.fecha_expiracion = datetime.now(timezone.utc) - timedelta(minutes=1)
    sesion.commit()
    assert integraciones.token_vigente(sesion, conexion) == "acceso-2"
    assert cifrado.descifrar(conexion.access_token_cifrado) == "acceso-2"


def test_desvincular_revoca_y_elimina(cliente, sesion, usuario, vinculado):
    respuesta = cliente.delete(f"{URL_INTEGRACIONES}/google_meet")
    assert respuesta.status_code == 200
    assert respuesta.json()["resultado"]["estado"] == "no_vinculada"
    assert any("revoke" in url for _, url, _ in vinculado.peticiones)
    assert sesion.scalar(select(ConexionPlataforma).where(ConexionPlataforma.id_usuario == usuario.id)) is None
    assert cliente.delete(f"{URL_INTEGRACIONES}/google_meet").status_code == 404


# ---------------------------------------------------------------------------
# HU-36 Configuracion de sesion externa
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("plataforma_codigo", "enlace", "esperado"),
    [
        ("google_meet", "https://meet.google.com/abc-defg-hij?authuser=0", "abc-defg-hij"),
        ("google_meet", "ABCDEFGHIJ", "abc-defg-hij"),
        ("zoom", "https://us02web.zoom.us/j/12345678901?pwd=xyz", "12345678901"),
        ("zoom", "123 456 7890", "1234567890"),
    ],
)
def test_normaliza_enlaces(plataforma_codigo, enlace, esperado):
    assert plataformas.normalizar_reunion(plataforma_codigo, enlace) == esperado


@pytest.mark.parametrize(
    ("plataforma_codigo", "enlace", "mensaje"),
    [
        ("google_meet", "https://zoom.us/j/12345678901", "corresponde a Zoom"),
        ("zoom", "https://meet.google.com/abc-defg-hij", "corresponde a Google Meet"),
        ("google_meet", "https://ejemplo.com/reunion", "no es de Google Meet"),
    ],
)
def test_rechaza_enlaces_de_otra_plataforma(plataforma_codigo, enlace, mensaje):
    with pytest.raises(ValueError, match=mensaje):
        plataformas.normalizar_reunion(plataforma_codigo, enlace)


def test_no_se_configura_sin_plataforma_vinculada(cliente, catalogo, credenciales):
    respuesta = crear_sesion(cliente, catalogo)
    assert respuesta.status_code == 409
    assert "vincula" in respuesta.json()["mensaje"]


def test_configurar_sesion(cliente, catalogo, vinculado):
    respuesta = crear_sesion(cliente, catalogo, descripcion_contexto="Revisión del proyecto")
    assert respuesta.status_code == 201
    r = respuesta.json()["resultado"]
    assert r["estado"] == "configurada"
    assert r["referencia_reunion"] == "abc-defg-hij"
    assert r["url_reunion"] == "https://meet.google.com/abc-defg-hij"
    assert [p["nombre"] for p in r["participantes"]] == ["Participante 1", "Participante 2"]


def test_enlace_de_otra_plataforma_al_configurar(cliente, catalogo, vinculado):
    respuesta = crear_sesion(cliente, catalogo, enlace_reunion="https://zoom.us/j/12345678901")
    assert respuesta.status_code == 400


def test_modificar_durante_la_reunion(cliente, sesion_activa, catalogo):
    url = f"{URL_SESIONES}/{sesion_activa['id_sesion_externa']}"
    assert cliente.patch(url, json={"descripcion_contexto": "Ahora hablamos de precios"}).status_code == 200
    # Idiomas y enlace solo antes de iniciar
    respuesta = cliente.patch(url, json={"id_idioma_destino": catalogo.idiomas["fr"].id_idioma})
    assert respuesta.status_code == 400


def test_cambiar_idiomas_antes_de_iniciar(cliente, catalogo, vinculado):
    creada = crear_sesion(cliente, catalogo).json()["resultado"]
    respuesta = cliente.patch(
        f"{URL_SESIONES}/{creada['id_sesion_externa']}", json={"id_idioma_destino": catalogo.idiomas["fr"].id_idioma}
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["resultado"]["codigo_idioma_destino"] == "fr"


def test_sesion_de_otro_usuario(cliente_como, sesion, sesion_activa):
    intruso = cliente_como(crear_usuario(sesion))
    assert intruso.get(f"{URL_SESIONES}/{sesion_activa['id_sesion_externa']}").status_code == 404


# ---------------------------------------------------------------------------
# HU-41 Control del servicio
# ---------------------------------------------------------------------------


def test_ciclo_de_vida_del_servicio(cliente, catalogo, vinculado):
    creada = crear_sesion(cliente, catalogo).json()["resultado"]
    url = f"{URL_SESIONES}/{creada['id_sesion_externa']}"
    assert cliente.post(f"{url}/pausar").status_code == 400  # aun no inicia

    iniciada = cliente.post(f"{url}/iniciar").json()["resultado"]
    assert iniciada["estado"] == "activa" and iniciada["fecha_inicio"]
    assert cliente.post(f"{url}/pausar").json()["resultado"]["estado"] == "pausada"
    assert cliente.post(f"{url}/reanudar").json()["resultado"]["estado"] == "activa"
    finalizada = cliente.post(f"{url}/finalizar").json()["resultado"]
    assert finalizada["estado"] == "finalizada" and finalizada["fecha_fin"]
    assert cliente.post(f"{url}/reanudar").status_code == 400

    # Queda en el historial
    historial = cliente.get(URL_SESIONES, params={"estado": "finalizada"}).json()["resultado"]
    assert [s["id_sesion_externa"] for s in historial] == [creada["id_sesion_externa"]]


def test_no_inicia_si_se_desvinculo(cliente, catalogo, vinculado):
    creada = crear_sesion(cliente, catalogo).json()["resultado"]
    cliente.delete(f"{URL_INTEGRACIONES}/google_meet")
    assert cliente.post(f"{URL_SESIONES}/{creada['id_sesion_externa']}/iniciar").status_code == 409


# ---------------------------------------------------------------------------
# HU-37 Captura y HU-38 Traduccion
# ---------------------------------------------------------------------------


def test_no_captura_si_el_servicio_no_esta_activo(cliente, catalogo, vinculado, motor):
    creada = crear_sesion(cliente, catalogo).json()["resultado"]
    respuesta = enviar_audio(cliente, creada["id_sesion_externa"])
    assert respuesta.status_code == 409


def test_traduce_en_ambos_sentidos_con_contexto(cliente, sesion_activa, motor):
    id_sesion = sesion_activa["id_sesion_externa"]
    motor.textos = [("Buenos días a todos", "es"), ("Good morning, shall we start?", "en")]

    primera = enviar_audio(cliente, id_sesion).json()["resultado"]
    assert primera["estado"] == "traducida"
    assert (primera["codigo_idioma_origen"], primera["codigo_idioma_destino"]) == ("es", "en")
    assert primera["texto_traducido"] == "[en] Buenos días a todos"
    assert primera["nombre_participante"] is None  # no se inventa el hablante

    segunda = enviar_audio(cliente, id_sesion).json()["resultado"]
    assert (segunda["codigo_idioma_origen"], segunda["codigo_idioma_destino"]) == ("en", "es")
    # La segunda considera la primera como contexto de la reunion
    assert "Buenos días a todos" in motor.traducciones[-1]["historial_conversacion"][0]
    assert motor.traducciones[-1]["aplicar_aprendizaje"] is True

    lista = cliente.get(f"{URL_SESIONES}/{id_sesion}/intervenciones").json()["resultado"]
    assert [i["orden"] for i in lista] == [1, 2]
    posteriores = cliente.get(
        f"{URL_SESIONES}/{id_sesion}/intervenciones", params={"despues_de": lista[0]["id_intervencion"]}
    ).json()["resultado"]
    assert len(posteriores) == 1


def test_fragmento_sin_voz(cliente, sesion, sesion_activa, motor):
    motor.textos = [("", None)]
    respuesta = enviar_audio(cliente, sesion_activa["id_sesion_externa"])
    assert respuesta.status_code == 200
    assert respuesta.json()["resultado"] is None
    assert sesion.scalar(select(IntervencionExterna)) is None or not sesion.scalars(
        select(IntervencionExterna).where(IntervencionExterna.id_sesion_externa == sesion_activa["id_sesion_externa"])
    ).all()


def test_idioma_fuera_del_par_se_informa_sin_detener(cliente, sesion_activa, motor):
    id_sesion = sesion_activa["id_sesion_externa"]
    motor.textos = [("Guten Morgen zusammen, wie geht es euch heute?", "de"), ("Hola", "es")]
    fallida = enviar_audio(cliente, id_sesion).json()["resultado"]
    assert fallida["estado"] == "error"
    assert "idioma" in fallida["mensaje_error"]
    # El servicio sigue funcionando
    assert enviar_audio(cliente, id_sesion).json()["resultado"]["estado"] == "traducida"


def test_error_de_traduccion_y_reintento(cliente, sesion_activa, motor):
    id_sesion = sesion_activa["id_sesion_externa"]
    motor.textos = [("Necesitamos revisar el presupuesto", "es")]
    motor.fallar_traduccion = True
    fallida = enviar_audio(cliente, id_sesion).json()["resultado"]
    assert fallida["estado"] == "error"

    motor.fallar_traduccion = False
    reintento = cliente.post(f"{URL_SESIONES}/{id_sesion}/intervenciones/{fallida['id_intervencion']}/reintentar")
    assert reintento.status_code == 200
    assert reintento.json()["resultado"]["estado"] == "traducida"


def test_pausa_durante_la_transcripcion_descarta_el_fragmento(cliente, sesion, sesion_activa, motor):
    id_sesion = sesion_activa["id_sesion_externa"]
    motor.textos = [("Esto no debe guardarse", "es")]
    motor.al_transcribir = lambda: cliente.post(f"{URL_SESIONES}/{id_sesion}/pausar")
    respuesta = enviar_audio(cliente, id_sesion)
    assert respuesta.status_code == 409
    assert cliente.get(f"{URL_SESIONES}/{id_sesion}/intervenciones").json()["resultado"] == []


def test_formato_de_audio_no_admitido(cliente, sesion_activa, motor):
    respuesta = cliente.post(
        f"{URL_SESIONES}/{sesion_activa['id_sesion_externa']}/audio",
        files={"audio": ("nota.txt", b"hola", "text/plain")},
    )
    assert respuesta.status_code == 400


def test_whisper_caido_responde_502(cliente, sesion_activa, monkeypatch):
    def falla(*args, **kwargs):
        raise TranscripcionError("sin servicio")

    monkeypatch.setattr(intervenciones_externas, "transcribir", falla)
    assert enviar_audio(cliente, sesion_activa["id_sesion_externa"]).status_code == 502


def test_glosario_solo_en_su_sentido(cliente, sesion, usuario, catalogo, vinculado, motor):
    glosario = Glosario(
        nombre="Términos", id_usuario=usuario.id,
        id_idioma_origen=catalogo.idiomas["es"].id_idioma, id_idioma_destino=catalogo.idiomas["en"].id_idioma,
    )
    sesion.add(glosario)
    sesion.commit()
    creada = crear_sesion(cliente, catalogo, id_glosario=glosario.id_glosario).json()["resultado"]
    cliente.post(f"{URL_SESIONES}/{creada['id_sesion_externa']}/iniciar")

    motor.textos = [("Revisemos el tablero", "es"), ("Let's check the dashboard", "en")]
    enviar_audio(cliente, creada["id_sesion_externa"])
    assert motor.traducciones[-1]["id_glosario"] == glosario.id_glosario
    enviar_audio(cliente, creada["id_sesion_externa"])
    assert motor.traducciones[-1]["id_glosario"] is None


# ---------------------------------------------------------------------------
# HU-40 Participantes
# ---------------------------------------------------------------------------


def test_etiquetas_genericas_y_renombrar(cliente, sesion_activa):
    url = f"{URL_SESIONES}/{sesion_activa['id_sesion_externa']}/participantes"
    nueva = cliente.post(url, json={}).json()["resultado"]
    assert nueva["nombre"] == "Participante 3" and nueva["generico"] is True

    renombrada = cliente.patch(f"{url}/{nueva['id_participante']}", json={"nombre": "Cliente"})
    assert renombrada.json()["resultado"]["nombre"] == "Cliente"


def test_sincronizar_participantes_de_la_plataforma(cliente, sesion_activa, vinculado):
    url = f"{URL_SESIONES}/{sesion_activa['id_sesion_externa']}/participantes"
    r = cliente.post(f"{url}/sincronizar").json()["resultado"]
    assert r["disponible"] is True and r["agregados"] == 2
    nombres = [p["nombre"] for p in r["participantes"]]
    assert "Ana Pérez" in nombres and "John" in nombres

    # Sin duplicados al volver a sincronizar
    assert cliente.post(f"{url}/sincronizar").json()["resultado"]["agregados"] == 0

    # Los nombres de la plataforma no se renombran
    de_plataforma = next(p for p in r["participantes"] if p["desde_plataforma"])
    assert cliente.patch(f"{url}/{de_plataforma['id_participante']}", json={"nombre": "Otro"}).status_code == 400


def test_plataforma_sin_participantes_usa_genericos(cliente, sesion_activa, vinculado):
    vinculado.fallar_participantes = True
    respuesta = cliente.post(f"{URL_SESIONES}/{sesion_activa['id_sesion_externa']}/participantes/sincronizar")
    assert respuesta.status_code == 200
    r = respuesta.json()["resultado"]
    assert r["disponible"] is False and r["aviso"]
    assert len(r["participantes"]) == 2


def test_intervencion_con_hablante_y_asignacion_posterior(cliente, sesion_activa, motor):
    id_sesion = sesion_activa["id_sesion_externa"]
    p1, p2 = sesion_activa["participantes"]
    motor.textos = [("Hola equipo", "es"), ("Hi there", "en")]

    con_hablante = enviar_audio(cliente, id_sesion, id_participante=p1["id_participante"]).json()["resultado"]
    assert con_hablante["nombre_participante"] == "Participante 1"

    sin_hablante = enviar_audio(cliente, id_sesion).json()["resultado"]
    asignada = cliente.patch(
        f"{URL_SESIONES}/{id_sesion}/intervenciones/{sin_hablante['id_intervencion']}",
        json={"id_participante": p2["id_participante"]},
    )
    assert asignada.json()["resultado"]["nombre_participante"] == "Participante 2"
    assert enviar_audio(cliente, id_sesion, id_participante=999999).status_code == 404


# ---------------------------------------------------------------------------
# Administracion: las sesiones externas cuentan en reportes y dashboard
# ---------------------------------------------------------------------------


def test_reporte_cuenta_sesiones_externas(cliente_admin, sesion, datos):
    idiomas, (usuario_a, _) = datos["idiomas"], datos["usuarios"]
    entorno = sesion.scalar(select(Entorno).order_by(Entorno.id_entorno))
    sesion.add(SesionExterna(
        id_usuario=usuario_a.id, plataforma="zoom", enlace_reunion="123456789", referencia_reunion="123456789",
        id_idioma_origen=idiomas["es"].id_idioma, id_idioma_destino=idiomas["en"].id_idioma,
        id_entorno=entorno.id_entorno, fecha_creacion=momento(9),
    ))
    sesion.commit()
    marzo = {"fecha_desde": "2001-03-01", "fecha_hasta": "2001-03-31", "zona_horaria": "America/La_Paz"}

    reporte = cliente_admin.get(f"{PREFIJO}/reportes/actividad", params={**marzo, "tipo_servicio": "sesion_externa"})
    r = reporte.json()["resultado"]
    assert r["totales"]["sesion_externa"] == 1
    assert r["actividades"][0]["detalle"] == "Zoom · 123456789"

    dashboard = cliente_admin.get(f"{PREFIJO}/dashboard", params=marzo).json()["resultado"]
    assert dashboard["actividad"]["sesiones_externas"] == 1

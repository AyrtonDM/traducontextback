"""Chats entre usuarios (Etapa 1: REST + traduccion en segundo plano)."""

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.configuracion import configuracion
from app.models.chat.chat import Chat
from app.models.chat.mensaje_chat import MensajeChat
from app.models.chat.participante_chat import ParticipanteChat
from app.models.chat.traduccion_mensaje_chat import TraduccionMensajeChat
from app.models.traduccion.configuracion_traduccion import ConfiguracionTraduccion
from app.models.traduccion.contexto import Contexto
from app.models.traduccion.idioma import Idioma
from app.services import chats as servicio
from tests.conftest import crear_usuario

URL = f"{configuracion.api_v1_prefix}/chats"

# Traducciones de prueba (el resto se simula como "[destino] texto")
FRASES = {
    ("How are you?", "en", "es"): "¿Cómo estás?",
    ("Estoy muy bien, gracias por preguntar", "es", "en"): "I am very well, thanks for asking",
}
# Detecciones de prueba (texto -> (codigo, confianza)); por defecto espanol con confianza alta
DETECCIONES = {
    "Estoy muy bien, gracias por preguntar": ("es", 0.98),
    "This sentence is clearly written in English": ("en", 0.97),
    "Texto ambiguo con pocas pistas claras": ("fr", 0.40),
}


@pytest.fixture(autouse=True)
def tablas_chats(sesion):
    """Crea las tablas dentro de la transaccion de la prueba si la migracion aun no se aplico."""
    conexion = sesion.connection()
    for modelo in (Chat, ParticipanteChat, MensajeChat, TraduccionMensajeChat):
        modelo.__table__.create(bind=conexion, checkfirst=True)


@pytest.fixture()
def idiomas(sesion):
    encontrados = {i.codigo: i for i in sesion.scalars(select(Idioma).where(Idioma.codigo.in_(["es", "en", "fr"])))}
    if len(encontrados) < 3:
        pytest.skip("Se necesitan los idiomas es, en y fr (seed de idiomas).")
    return encontrados


@pytest.fixture()
def motor_simulado(sesion, monkeypatch):
    """
    Las tareas en segundo plano usan la sesion de la prueba (asi se revierten) y un detector y un
    traductor simulados. Devuelve el registro de llamadas al traductor.
    """
    llamadas = []

    @contextmanager
    def abrir_sesion():
        yield sesion

    def detectar(texto):
        codigo, confianza = DETECCIONES.get(texto, ("es", 0.95))
        return {"codigo": codigo, "nombre": codigo, "confianza": confianza}

    def traducir(_sesion, _id_usuario, texto, origen, destino):
        llamadas.append((texto, origen, destino))
        return FRASES.get((texto, origen, destino), f"[{destino}] {texto}")

    monkeypatch.setattr(servicio, "_abrir_sesion", abrir_sesion)
    monkeypatch.setattr(servicio, "_detectar", detectar)
    monkeypatch.setattr(servicio, "_traducir", traducir)
    return llamadas


@pytest.fixture()
def juan(sesion):
    return crear_usuario(sesion, nombre="Juan Chats Prueba")


@pytest.fixture()
def pedro(sesion):
    return crear_usuario(sesion, nombre="Pedro Chats Prueba")


@pytest.fixture()
def chat_juan_pedro(cliente_como, juan, pedro, idiomas, motor_simulado):
    """Juan lee en ingles y Pedro en espanol."""
    respuesta = cliente_como(juan).post(URL, json={"id_usuario": pedro.id, "codigo_idioma_lectura": "en"})
    assert respuesta.status_code == 201
    id_chat = respuesta.json()["resultado"]["id_chat"]
    assert cliente_como(pedro).patch(f"{URL}/{id_chat}/idioma-lectura", json={"codigo_idioma": "es"}).status_code == 200
    return id_chat


def enviar(cliente, id_chat, texto):
    return cliente.post(f"{URL}/{id_chat}/mensajes", json={"texto": texto})


def mensajes(cliente, id_chat, **params):
    respuesta = cliente.get(f"{URL}/{id_chat}/mensajes", params=params)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["resultado"]


# ---------------------------------------------------------------------------
# Autenticacion y busqueda
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "metodo,ruta",
    [
        ("get", "/usuarios?q=ju"),
        ("post", ""),
        ("get", ""),
        ("get", "/1"),
        ("patch", "/1/idioma-lectura"),
        ("post", "/1/mensajes"),
        ("get", "/1/mensajes"),
        ("post", "/1/leido"),
    ],
)
def test_sin_token_responde_401(cliente_como, metodo, ruta):
    respuesta = getattr(cliente_como(None), metodo)(f"{URL}{ruta}")
    assert respuesta.status_code == 401


def test_buscar_usuarios_solo_activos_sin_mi_usuario_ni_correo(cliente_como, sesion, juan):
    activo = crear_usuario(sesion, nombre="Zorobabel Activo")
    crear_usuario(sesion, nombre="Zorobabel Suspendido", estado="SUSPENDIDO")
    crear_usuario(sesion, nombre="Zorobabel Inactivo", estado="INACTIVO")
    yo = crear_usuario(sesion, nombre="Zorobabel Yo")

    respuesta = cliente_como(yo).get(f"{URL}/usuarios", params={"q": "zorobabel"})
    assert respuesta.status_code == 200
    resultado = respuesta.json()["resultado"]
    assert resultado == [{"id_usuario": activo.id, "nombre": "Zorobabel Activo"}]


def test_buscar_usuarios_valida_longitud_limite_y_comodines(cliente_como, sesion, juan):
    for numero in range(3):
        crear_usuario(sesion, nombre=f"Quetzal Limite {numero}")
    cliente = cliente_como(juan)

    assert cliente.get(f"{URL}/usuarios", params={"q": "q"}).status_code == 422
    assert cliente.get(f"{URL}/usuarios", params={"q": "  q  "}).status_code == 400
    assert cliente.get(f"{URL}/usuarios", params={"q": "quetzal", "limite": 21}).status_code == 422
    assert len(cliente.get(f"{URL}/usuarios", params={"q": "quetzal", "limite": 2}).json()["resultado"]) == 2
    # '%' y '_' se buscan literalmente, no como comodines
    assert cliente.get(f"{URL}/usuarios", params={"q": "%%"}).json()["resultado"] == []
    assert cliente.get(f"{URL}/usuarios", params={"q": "__"}).json()["resultado"] == []


# ---------------------------------------------------------------------------
# Crear y listar chats
# ---------------------------------------------------------------------------


def test_crear_chat_es_idempotente_y_no_duplica_el_par(cliente_como, sesion, juan, pedro, idiomas):
    primera = cliente_como(juan).post(URL, json={"id_usuario": pedro.id, "codigo_idioma_lectura": "en"})
    assert primera.status_code == 201
    detalle = primera.json()["resultado"]
    assert detalle["otro_usuario"] == {"id_usuario": pedro.id, "nombre": pedro.nombre}
    assert detalle["mi_idioma_lectura"]["codigo"] == "en"
    assert detalle["no_leidos"] == 0 and detalle["ultimo_mensaje"] is None

    segunda = cliente_como(juan).post(URL, json={"id_usuario": pedro.id})
    inversa = cliente_como(pedro).post(URL, json={"id_usuario": juan.id})
    assert segunda.status_code == 200 and inversa.status_code == 200
    assert segunda.json()["resultado"]["id_chat"] == detalle["id_chat"] == inversa.json()["resultado"]["id_chat"]
    # Pedro no tiene preferencia: lee en espanol por defecto
    assert inversa.json()["resultado"]["mi_idioma_lectura"]["codigo"] == "es"

    menor, mayor = sorted((juan.id, pedro.id))
    filas = sesion.scalars(select(Chat).where(Chat.id_usuario_menor == menor, Chat.id_usuario_mayor == mayor)).all()
    assert len(filas) == 1


def test_crear_chat_usa_el_idioma_preferido_del_otro(cliente_como, sesion, juan, pedro, idiomas):
    contexto = sesion.scalar(select(Contexto).where(Contexto.id_usuario.is_(None)).order_by(Contexto.id_contexto))
    if contexto is None:
        pytest.skip("Se necesita el seed de contextos.")
    sesion.add(ConfiguracionTraduccion(
        id_usuario=pedro.id, id_contexto=contexto.id_contexto, id_idioma_destino=idiomas["fr"].id_idioma
    ))
    sesion.commit()

    id_chat = cliente_como(juan).post(URL, json={"id_usuario": pedro.id}).json()["resultado"]["id_chat"]
    participante = sesion.get(ParticipanteChat, (id_chat, pedro.id))
    assert participante.id_idioma_lectura == idiomas["fr"].id_idioma


def test_crear_chat_errores(cliente_como, sesion, juan, idiomas):
    suspendido = crear_usuario(sesion, nombre="Suspendido Chat", estado="SUSPENDIDO")
    otro = crear_usuario(sesion, nombre="Otro Chat")
    cliente = cliente_como(juan)

    assert cliente.post(URL, json={"id_usuario": juan.id}).status_code == 400
    assert cliente.post(URL, json={"id_usuario": suspendido.id}).status_code == 404
    assert cliente.post(URL, json={"id_usuario": 999_999_999}).status_code == 404
    assert cliente.post(URL, json={"id_usuario": otro.id, "codigo_idioma_lectura": "xx"}).status_code == 400
    respuesta = cliente.post(URL, json={"id_usuario": suspendido.id})
    assert set(respuesta.json()) == {"mensaje", "resultado"}


def test_quien_no_es_miembro_recibe_404(cliente_como, sesion, chat_juan_pedro):
    intruso = cliente_como(crear_usuario(sesion, nombre="Intruso Chat"))
    id_chat = chat_juan_pedro

    assert intruso.get(f"{URL}/{id_chat}").status_code == 404
    assert intruso.get(f"{URL}/{id_chat}/mensajes").status_code == 404
    assert enviar(intruso, id_chat, "hola").status_code == 404
    assert intruso.patch(f"{URL}/{id_chat}/idioma-lectura", json={"codigo_idioma": "en"}).status_code == 404
    assert intruso.post(f"{URL}/{id_chat}/leido", json={"id_mensaje": 1}).status_code == 404
    assert intruso.get(URL).json()["resultado"] == []
    # Un chat inexistente responde igual que uno ajeno
    assert intruso.get(f"{URL}/999999999").status_code == 404


# ---------------------------------------------------------------------------
# Ejemplo de aceptacion: Juan (en) y Pedro (es)
# ---------------------------------------------------------------------------


def test_juan_y_pedro_leen_cada_uno_en_su_idioma(cliente_como, juan, pedro, chat_juan_pedro, motor_simulado):
    id_chat = chat_juan_pedro

    enviado = enviar(cliente_como(juan), id_chat, "How are you?")
    assert enviado.status_code == 201
    propio = enviado.json()["resultado"]
    assert propio["es_mio"] is True and propio["estado_lectura"] == "propio"
    assert propio["texto"] == "How are you?"

    recibido = mensajes(cliente_como(pedro), id_chat)["elementos"][-1]
    assert recibido["texto"] == "¿Cómo estás?"
    assert recibido["texto_original"] == "How are you?"
    assert recibido["estado_lectura"] == "traducido"
    # Texto corto: se uso el idioma de lectura de Juan como idioma del original
    assert recibido["idioma_original"] == "en" and recibido["idioma_texto"] == "es"

    assert enviar(cliente_como(pedro), id_chat, "Estoy muy bien, gracias por preguntar").status_code == 201
    respuesta = mensajes(cliente_como(juan), id_chat)["elementos"]
    assert [m["texto"] for m in respuesta] == ["How are you?", "I am very well, thanks for asking"]
    assert respuesta[-1]["idioma_original"] == "es" and respuesta[-1]["idioma_texto"] == "en"
    assert motor_simulado == [
        ("How are you?", "en", "es"),
        ("Estoy muy bien, gracias por preguntar", "es", "en"),
    ]


def test_mismo_idioma_no_se_traduce(cliente_como, sesion, juan, pedro, chat_juan_pedro, motor_simulado):
    id_chat = chat_juan_pedro
    enviar(cliente_como(pedro), id_chat, "This sentence is clearly written in English")

    recibido = mensajes(cliente_como(juan), id_chat)["elementos"][-1]
    assert recibido["estado_lectura"] == "sin_traduccion"
    assert recibido["texto"] == "This sentence is clearly written in English"
    assert motor_simulado == []


def test_deteccion_poco_fiable_usa_el_idioma_del_remitente(cliente_como, sesion, juan, pedro, chat_juan_pedro, motor_simulado):
    id_chat = chat_juan_pedro
    id_mensaje = enviar(cliente_como(pedro), id_chat, "Texto ambiguo con pocas pistas claras").json()["resultado"]["id_mensaje"]

    mensaje = sesion.get(MensajeChat, id_mensaje)
    assert mensaje.idioma_por_respaldo is True
    assert mensaje.confianza_deteccion == pytest.approx(0.40)
    assert motor_simulado == [("Texto ambiguo con pocas pistas claras", "es", "en")]


def test_error_de_traduccion_entrega_el_original(cliente_como, sesion, juan, pedro, chat_juan_pedro, monkeypatch):
    def falla(*_args, **_kwargs):
        raise RuntimeError("fallo con texto secreto")

    monkeypatch.setattr(servicio, "_traducir", falla)
    id_chat = chat_juan_pedro
    id_mensaje = enviar(cliente_como(juan), id_chat, "How are you?").json()["resultado"]["id_mensaje"]

    recibido = mensajes(cliente_como(pedro), id_chat)["elementos"][-1]
    assert recibido["estado_lectura"] == "error" and recibido["texto"] == "How are you?"
    fila = sesion.scalar(select(TraduccionMensajeChat).where(TraduccionMensajeChat.id_mensaje == id_mensaje))
    assert fila.error == servicio.MENSAJE_ERROR_TRADUCCION
    assert "secreto" not in fila.error


def test_mensaje_pendiente_se_ve_original_con_marca(cliente_como, sesion, juan, pedro, chat_juan_pedro, monkeypatch):
    # Sin ejecutar la tarea en segundo plano el mensaje queda 'pendiente'
    monkeypatch.setattr(servicio, "procesar_mensaje", lambda _id: None)
    id_chat = chat_juan_pedro
    enviar(cliente_como(juan), id_chat, "How are you?")

    recibido = mensajes(cliente_como(pedro), id_chat)["elementos"][-1]
    assert recibido["estado_lectura"] == "pendiente"
    assert recibido["texto"] == "How are you?" and recibido["idioma_original"] is None


def test_procesar_mensaje_que_falla_queda_en_error(cliente_como, sesion, juan, chat_juan_pedro, monkeypatch):
    def explota(*_args):
        raise RuntimeError("fallo inesperado")

    monkeypatch.setattr(servicio, "_procesar_mensaje", explota)
    id_mensaje = enviar(cliente_como(juan), chat_juan_pedro, "How are you?").json()["resultado"]["id_mensaje"]
    sesion.expire_all()
    assert sesion.get(MensajeChat, id_mensaje).estado == "error"


# ---------------------------------------------------------------------------
# Cambio de idioma de lectura
# ---------------------------------------------------------------------------


def test_cambiar_idioma_retraduce_los_ultimos_50(cliente_como, sesion, juan, pedro, idiomas, chat_juan_pedro, motor_simulado):
    id_chat = chat_juan_pedro
    # 55 mensajes de Juan ya procesados (en ingles) y traducidos al espanol para Pedro
    ids = []
    for numero in range(55):
        mensaje = MensajeChat(
            id_chat=id_chat, id_remitente=juan.id, texto_original=f"Message number {numero}",
            id_idioma_detectado=idiomas["en"].id_idioma, estado="procesado",
        )
        sesion.add(mensaje)
        sesion.flush()
        sesion.add(TraduccionMensajeChat(
            id_mensaje=mensaje.id_mensaje, id_destinatario=pedro.id, id_idioma_destino=idiomas["es"].id_idioma,
            texto_traducido=f"Mensaje numero {numero}", estado="traducido",
        ))
        ids.append(mensaje.id_mensaje)
    sesion.commit()

    respuesta = cliente_como(pedro).patch(f"{URL}/{id_chat}/idioma-lectura", json={"codigo_idioma": "fr"})
    assert respuesta.status_code == 200
    assert respuesta.json()["resultado"]["mi_idioma_lectura"]["codigo"] == "fr"
    assert len(motor_simulado) == 50
    assert {destino for _, _, destino in motor_simulado} == {"fr"}

    recientes = mensajes(cliente_como(pedro), id_chat, limite=50)["elementos"]
    assert all(m["estado_lectura"] == "traducido" and m["texto"].startswith("[fr]") for m in recientes)

    # Los 5 mas antiguos se ven en el original con marca y se retraducen al consultarlos
    antiguos = mensajes(cliente_como(pedro), id_chat, antes_de=ids[5])["elementos"]
    assert [m["id_mensaje"] for m in antiguos] == ids[:5]
    assert all(m["estado_lectura"] == "pendiente" and m["texto"].startswith("Message") for m in antiguos)
    assert len(motor_simulado) == 55
    antiguos = mensajes(cliente_como(pedro), id_chat, antes_de=ids[5])["elementos"]
    assert all(m["estado_lectura"] == "traducido" for m in antiguos)

    # Volver al mismo idioma no retraduce nada
    cliente_como(pedro).patch(f"{URL}/{id_chat}/idioma-lectura", json={"codigo_idioma": "fr"})
    assert len(motor_simulado) == 55


def test_cambiar_idioma_inexistente_da_400(cliente_como, juan, chat_juan_pedro):
    respuesta = cliente_como(juan).patch(f"{URL}/{chat_juan_pedro}/idioma-lectura", json={"codigo_idioma": "xx"})
    assert respuesta.status_code == 400


def test_no_se_guarda_traduccion_si_el_idioma_cambio_mientras_se_traducia(
    cliente_como, sesion, juan, pedro, idiomas, chat_juan_pedro, monkeypatch
):
    llamadas = []

    def traducir_y_cambiar(_sesion, _id, texto, origen, destino):
        llamadas.append(destino)
        if len(llamadas) == 1:
            # Pedro cambia a frances justo mientras se traduce al espanol
            participante = sesion.get(ParticipanteChat, (chat_juan_pedro, pedro.id))
            participante.id_idioma_lectura = idiomas["fr"].id_idioma
            sesion.commit()
        return f"[{destino}] {texto}"

    monkeypatch.setattr(servicio, "_traducir", traducir_y_cambiar)
    enviar(cliente_como(juan), chat_juan_pedro, "How are you?")

    assert llamadas == ["es", "fr"]
    recibido = mensajes(cliente_como(pedro), chat_juan_pedro)["elementos"][-1]
    assert recibido["texto"] == "[fr] How are you?" and recibido["idioma_texto"] == "fr"


# ---------------------------------------------------------------------------
# Lista de chats, no leidos y paginacion
# ---------------------------------------------------------------------------


def test_lista_de_chats_con_ultimo_mensaje_y_no_leidos(cliente_como, juan, pedro, chat_juan_pedro):
    id_chat = chat_juan_pedro
    enviar(cliente_como(juan), id_chat, "How are you?")
    ultimo = enviar(cliente_como(juan), id_chat, "This sentence is clearly written in English").json()["resultado"]

    chat = cliente_como(pedro).get(URL).json()["resultado"][0]
    assert chat["id_chat"] == id_chat and chat["no_leidos"] == 2
    assert chat["ultimo_mensaje"]["id_mensaje"] == ultimo["id_mensaje"]
    assert chat["otro_usuario"]["nombre"] == juan.nombre
    # Lo propio no cuenta como no leido
    assert cliente_como(juan).get(URL).json()["resultado"][0]["no_leidos"] == 0

    leido = cliente_como(pedro).post(f"{URL}/{id_chat}/leido", json={"id_mensaje": ultimo["id_mensaje"] - 1})
    assert leido.json()["resultado"]["no_leidos"] == 1
    leido = cliente_como(pedro).post(f"{URL}/{id_chat}/leido", json={"id_mensaje": ultimo["id_mensaje"]})
    assert leido.json()["resultado"] == {"id_ultimo_mensaje_leido": ultimo["id_mensaje"], "no_leidos": 0}
    # Nunca retrocede
    leido = cliente_como(pedro).post(f"{URL}/{id_chat}/leido", json={"id_mensaje": ultimo["id_mensaje"] - 1})
    assert leido.json()["resultado"]["id_ultimo_mensaje_leido"] == ultimo["id_mensaje"]


def test_marcar_leido_con_mensaje_de_otro_chat_da_404(cliente_como, sesion, juan, pedro, chat_juan_pedro):
    otro = crear_usuario(sesion, nombre="Tercero Chat")
    otro_chat = cliente_como(juan).post(URL, json={"id_usuario": otro.id}).json()["resultado"]["id_chat"]
    ajeno = enviar(cliente_como(juan), otro_chat, "How are you?").json()["resultado"]["id_mensaje"]

    respuesta = cliente_como(pedro).post(f"{URL}/{chat_juan_pedro}/leido", json={"id_mensaje": ajeno})
    assert respuesta.status_code == 404


def test_paginacion_despues_de_y_antes_de(cliente_como, juan, pedro, chat_juan_pedro):
    id_chat = chat_juan_pedro
    ids = [enviar(cliente_como(juan), id_chat, f"Mensaje {n}").json()["resultado"]["id_mensaje"] for n in range(5)]

    ultimos = mensajes(cliente_como(pedro), id_chat, limite=2)
    assert [m["id_mensaje"] for m in ultimos["elementos"]] == ids[3:] and ultimos["hay_mas"] is True
    anteriores = mensajes(cliente_como(pedro), id_chat, antes_de=ids[3], limite=10)
    assert [m["id_mensaje"] for m in anteriores["elementos"]] == ids[:3] and anteriores["hay_mas"] is False
    nuevos = mensajes(cliente_como(pedro), id_chat, despues_de=ids[1], limite=2)
    assert [m["id_mensaje"] for m in nuevos["elementos"]] == ids[2:4] and nuevos["hay_mas"] is True
    assert mensajes(cliente_como(pedro), id_chat, despues_de=ids[-1])["elementos"] == []

    ambos = cliente_como(pedro).get(f"{URL}/{id_chat}/mensajes", params={"despues_de": 1, "antes_de": 5})
    assert ambos.status_code == 400


# ---------------------------------------------------------------------------
# Validaciones y antiabuso
# ---------------------------------------------------------------------------


def test_validacion_del_texto(cliente_como, juan, chat_juan_pedro):
    cliente = cliente_como(juan)
    assert enviar(cliente, chat_juan_pedro, "   ").status_code == 422
    assert enviar(cliente, chat_juan_pedro, "a" * 2001).status_code == 422
    assert enviar(cliente, chat_juan_pedro, "a" * 2000).status_code == 201


def test_no_se_puede_escribir_a_un_usuario_suspendido(cliente_como, sesion, juan, pedro, chat_juan_pedro):
    pedro.estado = "SUSPENDIDO"
    sesion.commit()
    assert enviar(cliente_como(juan), chat_juan_pedro, "How are you?").status_code == 400


def test_limite_de_mensajes_por_minuto(cliente_como, sesion, juan, chat_juan_pedro, monkeypatch):
    monkeypatch.setattr(servicio, "MAXIMO_MENSAJES_POR_MINUTO", 2)
    cliente = cliente_como(juan)
    assert enviar(cliente, chat_juan_pedro, "uno").status_code == 201
    assert enviar(cliente, chat_juan_pedro, "dos").status_code == 201
    respuesta = enviar(cliente, chat_juan_pedro, "tres")
    assert respuesta.status_code == 429
    assert respuesta.json()["resultado"] is None

    # Los mensajes de hace mas de un minuto ya no cuentan
    for mensaje in sesion.scalars(select(MensajeChat).where(MensajeChat.id_remitente == juan.id)):
        mensaje.fecha_envio = datetime.now(timezone.utc) - timedelta(minutes=2)
    sesion.commit()
    assert enviar(cliente, chat_juan_pedro, "cuatro").status_code == 201


def test_las_traducciones_pasan_por_el_semaforo(cliente_como, juan, chat_juan_pedro, monkeypatch):
    eventos = []

    class SemaforoEspia:
        def __enter__(self):
            eventos.append("entra")

        def __exit__(self, *_args):
            eventos.append("sale")

    monkeypatch.setattr(servicio, "_semaforo_traduccion", SemaforoEspia())
    enviar(cliente_como(juan), chat_juan_pedro, "How are you?")
    assert eventos == ["entra", "sale"]
    assert servicio.MAXIMO_TRADUCCIONES_SIMULTANEAS >= 1


def test_al_arrancar_lo_pendiente_pasa_a_error(sesion, juan, pedro, idiomas, chat_juan_pedro):
    mensaje = MensajeChat(id_chat=chat_juan_pedro, id_remitente=juan.id, texto_original="hola", estado="pendiente")
    procesado = MensajeChat(
        id_chat=chat_juan_pedro, id_remitente=juan.id, texto_original="hello",
        estado="procesado", id_idioma_detectado=idiomas["en"].id_idioma,
    )
    sesion.add_all([mensaje, procesado])
    sesion.flush()
    traduccion = TraduccionMensajeChat(
        id_mensaje=procesado.id_mensaje, id_destinatario=pedro.id, id_idioma_destino=idiomas["es"].id_idioma,
    )
    sesion.add(traduccion)
    sesion.commit()

    mensajes_error, traducciones_error = servicio.marcar_pendientes_como_error(sesion)
    assert mensajes_error >= 1 and traducciones_error >= 1
    sesion.expire_all()
    assert sesion.get(MensajeChat, mensaje.id_mensaje).estado == "error"
    assert sesion.get(TraduccionMensajeChat, traduccion.id_traduccion).estado == "error"

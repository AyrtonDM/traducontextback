"""M1 Notificaciones: dispositivos push, bandeja de notificaciones y notificar()."""

import pytest
from fastapi import BackgroundTasks
from sqlalchemy import select

from app.core.configuracion import configuracion
from app.models.notificacion.dispositivo_push import DispositivoPush
from app.models.notificacion.notificacion import Notificacion
from app.services import notificaciones as servicio
from app.services import push_fcm
from tests.conftest import crear_usuario

URL_DISPOSITIVOS = f"{configuracion.api_v1_prefix}/dispositivos"
URL_NOTIFICACIONES = f"{configuracion.api_v1_prefix}/notificaciones"


@pytest.fixture(autouse=True)
def tablas_notificaciones(sesion):
    """
    Crea las tablas dentro de la transaccion de la prueba si la migracion aun no se aplico
    (el DDL de PostgreSQL es transaccional: se revierte al terminar).
    """
    conexion = sesion.connection()
    for tabla in (DispositivoPush.__table__, Notificacion.__table__):
        tabla.create(bind=conexion, checkfirst=True)


@pytest.fixture()
def otro_usuario(sesion):
    return crear_usuario(sesion, nombre="Otro Usuario")


@pytest.fixture()
def push_simulado(monkeypatch):
    """Simula FCM disponible y registra los envios."""
    envios = []
    respuesta = push_fcm.ResultadoEnvioPush()

    def enviar_falso(tokens, titulo, cuerpo, datos):
        envios.append({"tokens": list(tokens), "titulo": titulo, "cuerpo": cuerpo, "datos": datos})
        return respuesta

    monkeypatch.setattr(push_fcm, "push_disponible", lambda: True)
    monkeypatch.setattr(push_fcm, "enviar_a_tokens", enviar_falso)
    return envios, respuesta


def registrar(cliente, token="token-a", plataforma="android"):
    return cliente.post(URL_DISPOSITIVOS, json={"token_fcm": token, "plataforma": plataforma})


# ---------------------------------------------------------------------------
# Autenticacion
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "metodo, ruta",
    [
        ("post", URL_DISPOSITIVOS),
        ("delete", f"{URL_DISPOSITIVOS}/token-a"),
        ("get", URL_NOTIFICACIONES),
        ("patch", f"{URL_NOTIFICACIONES}/leidas"),
        ("patch", f"{URL_NOTIFICACIONES}/1/leida"),
    ],
)
def test_sin_token_responde_401(cliente_como, metodo, ruta):
    respuesta = getattr(cliente_como(None), metodo)(ruta)
    assert respuesta.status_code == 401


# ---------------------------------------------------------------------------
# Dispositivos
# ---------------------------------------------------------------------------


def test_registrar_dispositivo(cliente, sesion, usuario):
    respuesta = registrar(cliente, " token-a ")
    assert respuesta.status_code == 200
    resultado = respuesta.json()["resultado"]
    assert resultado["plataforma"] == "android"
    assert resultado["activo"] is True
    assert "token_fcm" not in resultado

    dispositivo = sesion.scalar(select(DispositivoPush).where(DispositivoPush.token_fcm == "token-a"))
    assert dispositivo.id_usuario == usuario.id


def test_registrar_mismo_token_es_idempotente_y_reactiva(cliente, sesion):
    registrar(cliente)
    dispositivo = sesion.scalar(select(DispositivoPush).where(DispositivoPush.token_fcm == "token-a"))
    dispositivo.activo = False
    sesion.commit()

    respuesta = registrar(cliente, plataforma="ios")
    assert respuesta.status_code == 200
    assert respuesta.json()["resultado"]["activo"] is True
    filas = sesion.scalars(select(DispositivoPush).where(DispositivoPush.token_fcm == "token-a")).all()
    assert len(filas) == 1
    assert filas[0].plataforma == "ios"


def test_token_de_otra_cuenta_pasa_al_usuario_actual(cliente_como, sesion, usuario, otro_usuario):
    registrar(cliente_como(otro_usuario))
    registrar(cliente_como(usuario))
    dispositivo = sesion.scalar(select(DispositivoPush).where(DispositivoPush.token_fcm == "token-a"))
    assert dispositivo.id_usuario == usuario.id


def test_registrar_valida_plataforma_y_token(cliente):
    assert registrar(cliente, plataforma="windows").status_code == 422
    assert registrar(cliente, token="   ").status_code == 422


@pytest.fixture()
def restriccion_plataforma_con_web(sesion):
    """
    Si la base aun no tiene la migracion c5e7a9b1d3f5, recrea la restriccion como la deja esa
    migracion, dentro de la transaccion de la prueba (el DDL de PostgreSQL se revierte al terminar).
    """
    conexion = sesion.connection()
    definicion = conexion.exec_driver_sql(
        "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'ck_dispositivo_push_plataforma'"
    ).scalar()
    if definicion is not None and "'web'" not in definicion:
        conexion.exec_driver_sql("ALTER TABLE dispositivo_push DROP CONSTRAINT ck_dispositivo_push_plataforma")
        conexion.exec_driver_sql(
            "ALTER TABLE dispositivo_push ADD CONSTRAINT ck_dispositivo_push_plataforma "
            "CHECK (plataforma IN ('android', 'ios', 'web'))"
        )


def test_registrar_navegador_web_y_rechazar_plataforma_desconocida(
    cliente, sesion, usuario, restriccion_plataforma_con_web
):
    respuesta = registrar(cliente, "token-web", plataforma="web")
    assert respuesta.status_code == 200
    assert respuesta.json()["resultado"]["plataforma"] == "web"
    dispositivo = sesion.scalar(select(DispositivoPush).where(DispositivoPush.token_fcm == "token-web"))
    assert dispositivo.plataforma == "web"
    assert dispositivo.id_usuario == usuario.id

    assert registrar(cliente, "token-pc", plataforma="windows").status_code == 422


def test_eliminar_dispositivo_propio(cliente, sesion):
    registrar(cliente)
    respuesta = cliente.delete(f"{URL_DISPOSITIVOS}/token-a")
    assert respuesta.status_code == 200
    assert sesion.scalar(select(DispositivoPush).where(DispositivoPush.token_fcm == "token-a")) is None


def test_no_se_puede_eliminar_dispositivo_ajeno(cliente_como, sesion, usuario, otro_usuario):
    registrar(cliente_como(otro_usuario))
    respuesta = cliente_como(usuario).delete(f"{URL_DISPOSITIVOS}/token-a")
    assert respuesta.status_code == 404
    assert sesion.scalar(select(DispositivoPush).where(DispositivoPush.token_fcm == "token-a")) is not None


# ---------------------------------------------------------------------------
# notificar()
# ---------------------------------------------------------------------------


def test_notificar_sin_credenciales_solo_guarda(sesion, usuario, monkeypatch):
    monkeypatch.setattr(push_fcm, "push_disponible", lambda: False)

    def no_debe_llamarse(*args, **kwargs):
        raise AssertionError("No debe intentar enviar push sin credenciales")

    monkeypatch.setattr(push_fcm, "enviar_a_tokens", no_debe_llamarse)

    notificacion = servicio.notificar(sesion, usuario.id, "SISTEMA", "Prueba", "Hola")
    assert notificacion.id_notificacion is not None
    assert notificacion.leida is False


def test_notificar_envia_a_dispositivos_activos_del_usuario(sesion, usuario, otro_usuario, push_simulado):
    envios, _ = push_simulado
    sesion.add_all([
        DispositivoPush(id_usuario=usuario.id, token_fcm="activo", plataforma="android"),
        DispositivoPush(id_usuario=usuario.id, token_fcm="inactivo", plataforma="android", activo=False),
        DispositivoPush(id_usuario=otro_usuario.id, token_fcm="ajeno", plataforma="ios"),
    ])
    sesion.commit()

    notificacion = servicio.notificar(
        sesion, usuario.id, "DOCUMENTO_LISTO", "Tu documento esta listo", "Toca para verlo",
        datos={"id_traduccion_documento": 7},
    )

    assert len(envios) == 1
    assert envios[0]["tokens"] == ["activo"]
    assert envios[0]["datos"] == {
        "id_traduccion_documento": "7",
        "tipo": "DOCUMENTO_LISTO",
        "id_notificacion": str(notificacion.id_notificacion),
    }


def test_notificar_desactiva_tokens_invalidos(sesion, usuario, push_simulado):
    _, respuesta = push_simulado
    respuesta.tokens_invalidos = ["viejo"]
    sesion.add_all([
        DispositivoPush(id_usuario=usuario.id, token_fcm="viejo", plataforma="android"),
        DispositivoPush(id_usuario=usuario.id, token_fcm="nuevo", plataforma="android"),
    ])
    sesion.commit()

    servicio.notificar(sesion, usuario.id, "SISTEMA", "Prueba", "Hola")

    estados = dict(sesion.execute(select(DispositivoPush.token_fcm, DispositivoPush.activo)).all())
    assert estados["viejo"] is False
    assert estados["nuevo"] is True


def test_fallo_de_fcm_no_rompe_el_flujo(sesion, usuario, monkeypatch):
    sesion.add(DispositivoPush(id_usuario=usuario.id, token_fcm="t", plataforma="android"))
    sesion.commit()

    def explota(*args, **kwargs):
        raise RuntimeError("FCM caido")

    monkeypatch.setattr(push_fcm, "push_disponible", lambda: True)
    monkeypatch.setattr(push_fcm, "enviar_a_tokens", explota)

    notificacion = servicio.notificar(sesion, usuario.id, "SISTEMA", "Prueba", "Hola")
    assert sesion.get(Notificacion, notificacion.id_notificacion) is not None


def test_notificar_con_tareas_programa_el_envio(sesion, usuario, monkeypatch):
    monkeypatch.setattr(push_fcm, "enviar_a_tokens", lambda *a, **k: pytest.fail("No debe enviar en linea"))
    tareas = BackgroundTasks()

    notificacion = servicio.notificar(sesion, usuario.id, "SISTEMA", "Prueba", "Hola", tareas_segundo_plano=tareas)

    assert len(tareas.tasks) == 1
    assert tareas.tasks[0].args == (notificacion.id_notificacion,)


def test_notificar_rechaza_tipo_desconocido(sesion, usuario):
    with pytest.raises(ValueError):
        servicio.notificar(sesion, usuario.id, "OTRO", "Prueba", "Hola")


# ---------------------------------------------------------------------------
# Bandeja
# ---------------------------------------------------------------------------


@pytest.fixture()
def bandeja(sesion, usuario, otro_usuario, monkeypatch):
    monkeypatch.setattr(push_fcm, "push_disponible", lambda: False)
    propias = [servicio.notificar(sesion, usuario.id, "SISTEMA", f"N{i}", "cuerpo") for i in range(3)]
    ajena = servicio.notificar(sesion, otro_usuario.id, "SISTEMA", "Ajena", "cuerpo")
    return propias, ajena


def test_listar_solo_mis_notificaciones_y_contador(cliente, bandeja):
    propias, _ = bandeja
    respuesta = cliente.get(URL_NOTIFICACIONES)
    assert respuesta.status_code == 200
    resultado = respuesta.json()["resultado"]
    assert resultado["total"] == 3
    assert resultado["no_leidas"] == 3
    ids = [n["id_notificacion"] for n in resultado["elementos"]]
    assert sorted(ids) == sorted(n.id_notificacion for n in propias)
    assert "Ajena" not in [n["titulo"] for n in resultado["elementos"]]


def test_listar_paginado_y_filtro_no_leidas(cliente, bandeja):
    propias, _ = bandeja
    cliente.patch(f"{URL_NOTIFICACIONES}/{propias[0].id_notificacion}/leida")

    resultado = cliente.get(URL_NOTIFICACIONES, params={"solo_no_leidas": True}).json()["resultado"]
    assert resultado["total"] == 2
    assert resultado["no_leidas"] == 2

    pagina = cliente.get(URL_NOTIFICACIONES, params={"tamano_pagina": 2, "pagina": 2}).json()["resultado"]
    assert len(pagina["elementos"]) == 1
    assert pagina["total_paginas"] == 2


def test_marcar_una_como_leida(cliente, bandeja):
    propias, _ = bandeja
    respuesta = cliente.patch(f"{URL_NOTIFICACIONES}/{propias[0].id_notificacion}/leida")
    assert respuesta.status_code == 200
    resultado = respuesta.json()["resultado"]
    assert resultado["leida"] is True
    assert resultado["fecha_lectura"] is not None


def test_no_se_puede_marcar_notificacion_ajena(cliente, sesion, bandeja):
    _, ajena = bandeja
    respuesta = cliente.patch(f"{URL_NOTIFICACIONES}/{ajena.id_notificacion}/leida")
    assert respuesta.status_code == 404
    sesion.refresh(ajena)
    assert ajena.leida is False


def test_marcar_todas_como_leidas_solo_afecta_las_mias(cliente, sesion, bandeja):
    _, ajena = bandeja
    respuesta = cliente.patch(f"{URL_NOTIFICACIONES}/leidas")
    assert respuesta.status_code == 200
    assert respuesta.json()["resultado"]["actualizadas"] == 3
    assert cliente.get(URL_NOTIFICACIONES).json()["resultado"]["no_leidas"] == 0
    sesion.refresh(ajena)
    assert ajena.leida is False

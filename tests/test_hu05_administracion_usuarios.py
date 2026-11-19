"""HU-05 Administracion de usuarios: endpoints /usuarios (solo con permiso gestionar_usuarios)."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.configuracion import configuracion
from app.models.usuario.rol import Rol
from app.models.usuario.sesion import Sesion
from app.utilities.seguridad import hashear_contrasena
from tests.conftest import crear_usuario

PREFIJO = configuracion.api_v1_prefix
URL = f"{PREFIJO}/usuarios"


@pytest.fixture()
def rol_usuario(sesion):
    return sesion.scalar(select(Rol).where(Rol.nombre == "USUARIO"))


def crear_sesion_activa(sesion, id_usuario) -> Sesion:
    registro = Sesion(
        token=uuid.uuid4().hex,
        fecha_inicio=datetime.now(UTC),
        fecha_expiracion=datetime.now(UTC) + timedelta(days=1),
        estado="ACTIVA",
        id_usuario=id_usuario,
    )
    sesion.add(registro)
    sesion.commit()
    return registro


# ---------------------------------------------------------------------------
# Acceso solo para administradores
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("metodo", "ruta"),
    [
        ("get", ""),
        ("get", "/roles"),
        ("get", "/{id}"),
        ("patch", "/{id}/suspender"),
        ("patch", "/{id}/reactivar"),
        ("patch", "/{id}/rol"),
    ],
)
def test_usuario_sin_rol_admin_recibe_403(cliente_como, sesion, admin, metodo, ruta):
    normal = crear_usuario(sesion, "USUARIO")
    cliente = cliente_como(normal)
    kwargs = {"json": {"id_rol": admin.id_rol}} if ruta.endswith("/rol") else {}

    respuesta = getattr(cliente, metodo)(URL + ruta.format(id=admin.id), **kwargs)
    assert respuesta.status_code == 403


def test_sin_token_responde_401(cliente_como):
    respuesta = cliente_como(None).get(URL)
    assert respuesta.status_code == 401


# ---------------------------------------------------------------------------
# Listado, busqueda, filtros y detalle
# ---------------------------------------------------------------------------


def test_listado_paginado_con_campos_requeridos(cliente_admin, sesion):
    for _ in range(3):
        crear_usuario(sesion, "USUARIO")

    respuesta = cliente_admin.get(URL, params={"pagina": 1, "tamano_pagina": 2})
    assert respuesta.status_code == 200, respuesta.text
    resultado = respuesta.json()["resultado"]
    assert len(resultado["elementos"]) == 2
    assert resultado["total"] >= 4
    assert resultado["total_paginas"] >= 2
    fila = resultado["elementos"][0]
    for campo in ("id", "nombre", "correo", "estado", "fecha_creacion", "rol"):
        assert campo in fila


def test_busqueda_por_nombre_o_correo(cliente_admin, sesion):
    marca = uuid.uuid4().hex[:8]
    buscado = crear_usuario(sesion, "USUARIO", nombre=f"Buscado {marca}")

    por_nombre = cliente_admin.get(URL, params={"busqueda": marca}).json()["resultado"]
    assert [u["id"] for u in por_nombre["elementos"]] == [buscado.id]

    por_correo = cliente_admin.get(URL, params={"busqueda": buscado.correo.upper()}).json()
    assert [u["id"] for u in por_correo["resultado"]["elementos"]] == [buscado.id]


def test_filtros_por_rol_y_estado_combinados(cliente_admin, sesion, rol_usuario):
    marca = uuid.uuid4().hex[:8]
    activo = crear_usuario(sesion, "USUARIO", nombre=f"F {marca}")
    crear_usuario(sesion, "USUARIO", nombre=f"F {marca}", estado="INACTIVO")
    crear_usuario(sesion, "ADMINISTRADOR", nombre=f"F {marca}")

    respuesta = cliente_admin.get(
        URL, params={"busqueda": marca, "id_rol": rol_usuario.id, "estado": "ACTIVO"}
    )
    ids = [u["id"] for u in respuesta.json()["resultado"]["elementos"]]
    assert ids == [activo.id]


def test_filtro_estado_invalido_responde_422(cliente_admin):
    assert cliente_admin.get(URL, params={"estado": "BORRADO"}).status_code == 422


def test_detalle_de_una_cuenta(cliente_admin, sesion):
    otro = crear_usuario(sesion, "USUARIO")
    crear_sesion_activa(sesion, otro.id)

    respuesta = cliente_admin.get(f"{URL}/{otro.id}")
    assert respuesta.status_code == 200, respuesta.text
    detalle = respuesta.json()["resultado"]
    assert detalle["correo"] == otro.correo
    assert detalle["rol"]["nombre"] == "USUARIO"
    assert detalle["sesiones_activas"] == 1
    assert detalle["ultimo_acceso"] is not None
    assert detalle["total_traducciones"] == 0


def test_detalle_de_cuenta_inexistente_responde_404(cliente_admin):
    assert cliente_admin.get(f"{URL}/999999999").status_code == 404


def test_listar_roles(cliente_admin):
    roles = cliente_admin.get(f"{URL}/roles").json()["resultado"]
    assert {"ADMINISTRADOR", "USUARIO"} <= {r["nombre"] for r in roles}


# ---------------------------------------------------------------------------
# Suspender y reactivar
# ---------------------------------------------------------------------------


def test_suspender_invalida_sesiones_y_conserva_datos(cliente_admin, sesion):
    otro = crear_usuario(sesion, "USUARIO")
    registro = crear_sesion_activa(sesion, otro.id)

    respuesta = cliente_admin.patch(f"{URL}/{otro.id}/suspender")
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["resultado"]["estado"] == "SUSPENDIDO"
    assert respuesta.json()["resultado"]["sesiones_activas"] == 0

    sesion.refresh(registro)
    assert registro.estado == "CERRADA"
    assert registro.fecha_cierre is not None
    # La cuenta no se elimina
    assert cliente_admin.get(f"{URL}/{otro.id}").status_code == 200


def test_usuario_suspendido_no_puede_iniciar_sesion(cliente_como, cliente_admin, sesion):
    otro = crear_usuario(sesion, "USUARIO", contrasena=hashear_contrasena("Clave1234"))
    cliente_admin.patch(f"{URL}/{otro.id}/suspender")

    respuesta = cliente_como(None).post(
        f"{PREFIJO}/autenticacion/iniciar-sesion",
        json={"correo": otro.correo, "contrasena": "Clave1234"},
    )
    assert respuesta.status_code == 403
    assert "suspendida" in respuesta.json()["mensaje"]


def test_usuario_suspendido_no_se_reactiva_con_codigo_de_verificacion(
    cliente_como, cliente_admin, sesion
):
    otro = crear_usuario(sesion, "USUARIO")
    cliente_admin.patch(f"{URL}/{otro.id}/suspender")
    publico = cliente_como(None)

    reenviar = publico.post(f"{URL}/reenviar-codigo", json={"correo": otro.correo})
    assert reenviar.status_code == 403

    verificar = publico.post(
        f"{URL}/verificar-codigo", json={"correo": otro.correo, "codigo": "123456"}
    )
    assert verificar.status_code == 403
    sesion.refresh(otro)
    assert otro.estado == "SUSPENDIDO"


def test_reactivar_cuenta_suspendida(cliente_admin, sesion):
    otro = crear_usuario(sesion, "USUARIO")
    cliente_admin.patch(f"{URL}/{otro.id}/suspender")

    respuesta = cliente_admin.patch(f"{URL}/{otro.id}/reactivar")
    assert respuesta.status_code == 200
    assert respuesta.json()["resultado"]["estado"] == "ACTIVO"


def test_reactivar_cuenta_no_suspendida_responde_400(cliente_admin, sesion):
    otro = crear_usuario(sesion, "USUARIO")
    assert cliente_admin.patch(f"{URL}/{otro.id}/reactivar").status_code == 400


def test_no_se_suspende_cuenta_sin_verificar(cliente_admin, sesion):
    otro = crear_usuario(sesion, "USUARIO", estado="INACTIVO")
    assert cliente_admin.patch(f"{URL}/{otro.id}/suspender").status_code == 400


def test_admin_no_puede_suspenderse_a_si_mismo(cliente_admin, admin):
    respuesta = cliente_admin.patch(f"{URL}/{admin.id}/suspender")
    assert respuesta.status_code == 400
    assert "propia cuenta" in respuesta.json()["mensaje"]


# ---------------------------------------------------------------------------
# Cambio de rol
# ---------------------------------------------------------------------------


def test_cambiar_rol_de_un_usuario(cliente_admin, sesion, admin):
    otro = crear_usuario(sesion, "USUARIO")

    respuesta = cliente_admin.patch(f"{URL}/{otro.id}/rol", json={"id_rol": admin.id_rol})
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["resultado"]["rol"]["nombre"] == "ADMINISTRADOR"


def test_admin_no_puede_quitarse_el_rol(cliente_admin, admin, rol_usuario):
    respuesta = cliente_admin.patch(f"{URL}/{admin.id}/rol", json={"id_rol": rol_usuario.id})
    assert respuesta.status_code == 400
    assert "Administrador" in respuesta.json()["mensaje"]


def test_cambiar_a_rol_inexistente_responde_404(cliente_admin, sesion):
    otro = crear_usuario(sesion, "USUARIO")
    assert cliente_admin.patch(f"{URL}/{otro.id}/rol", json={"id_rol": 999999}).status_code == 404

"""
Infraestructura de pruebas de endpoints (FastAPI TestClient).

Cada prueba se ejecuta dentro de una transaccion de la base de datos configurada en `.env`
que se revierte al terminar: los `commit()` de los servicios se convierten en savepoints,
por lo que ninguna prueba deja datos en la base.
"""

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.seguridad import requiere_token
from app.database.conexion import motor, obtener_sesion
from app.main import app
from app.models.conversacion.conversacion import Conversacion
from app.models.conversacion.entorno import Entorno
from app.models.documento.traduccion_documento import TraduccionDocumento
from app.models.traduccion.configuracion_traduccion import ConfiguracionTraduccion
from app.models.traduccion.contexto import Contexto
from app.models.traduccion.idioma import Idioma
from app.models.traduccion.traduccion import Traduccion
from app.models.usuario.rol import Rol
from app.models.usuario.usuario import Usuario
from app.services.usuarios import obtener_usuario_actual


@pytest.fixture()
def sesion():
    conexion = motor.connect()
    transaccion = conexion.begin()
    sesion_db = Session(
        bind=conexion,
        join_transaction_mode="create_savepoint",
        autoflush=False,
        expire_on_commit=False,
    )
    try:
        yield sesion_db
    finally:
        sesion_db.close()
        transaccion.rollback()
        conexion.close()


def crear_usuario(
    sesion: Session,
    nombre_rol: str | None = None,
    *,
    nombre: str = "Usuario Prueba",
    estado: str = "ACTIVO",
    contrasena: str = "no-usada-en-pruebas",
) -> Usuario:
    consulta = select(Rol).order_by(Rol.id)
    if nombre_rol:
        consulta = consulta.where(Rol.nombre == nombre_rol)
    rol = sesion.scalar(consulta)
    assert rol is not None, "La base de pruebas necesita al menos un rol (ejecutar seeds)."

    usuario = Usuario(
        nombre=nombre,
        correo=f"prueba_{uuid.uuid4().hex[:12]}@test.local",
        contrasena=contrasena,
        estado=estado,
        id_rol=rol.id,
    )
    sesion.add(usuario)
    sesion.commit()
    sesion.refresh(usuario)
    return usuario


@pytest.fixture()
def usuario(sesion):
    return crear_usuario(sesion)


@pytest.fixture()
def cliente_como(sesion):
    """
    Fabrica de clientes autenticados como el usuario indicado. Los permisos por rol
    (`requiere_permiso`) se siguen verificando contra la base de datos.
    """

    def fabricar(usuario_autenticado: Usuario | None) -> TestClient:
        app.dependency_overrides[obtener_sesion] = lambda: sesion
        if usuario_autenticado is not None:
            app.dependency_overrides[requiere_token] = lambda: usuario_autenticado
            app.dependency_overrides[obtener_usuario_actual] = lambda: usuario_autenticado
        else:
            app.dependency_overrides.pop(requiere_token, None)
            app.dependency_overrides.pop(obtener_usuario_actual, None)
        return TestClient(app)

    try:
        yield fabricar
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def cliente(cliente_como, usuario):
    """Cliente autenticado como `usuario`, usando la sesion transaccional de la prueba."""
    return cliente_como(usuario)


# ---------------------------------------------------------------------------
# Administracion (HU-46, HU-47, HU-48): administrador y actividad de prueba en marzo de 2001
# ---------------------------------------------------------------------------


def momento(dia: int, hora: int = 12, mes: int = 3) -> datetime:
    """Fecha y hora UTC dentro de marzo de 2001."""
    return datetime(2001, mes, dia, hora, tzinfo=timezone.utc)


@pytest.fixture()
def admin(sesion):
    if sesion.scalar(select(Rol).where(Rol.nombre == "ADMINISTRADOR")) is None:
        pytest.skip("Se necesita el seed de roles (ADMINISTRADOR).")
    return crear_usuario(sesion, "ADMINISTRADOR", nombre="Admin Prueba")


@pytest.fixture()
def cliente_admin(cliente_como, admin):
    return cliente_como(admin)


@pytest.fixture()
def datos(sesion):
    """
    En marzo de 2001: 2 usuarios nuevos, 3 traducciones de texto (es→en), 1 documento
    completado y 1 fallido (es→fr) y 1 conversacion (en→es).
    """
    idiomas = {
        i.codigo: i for i in sesion.scalars(select(Idioma).where(Idioma.codigo.in_(["es", "en", "fr"])))
    }
    contextos = sesion.scalars(
        select(Contexto).where(Contexto.id_usuario.is_(None)).order_by(Contexto.id_contexto)
    ).all()
    entorno = sesion.scalar(select(Entorno).order_by(Entorno.id_entorno))
    if len(idiomas) < 3 or len(contextos) < 2 or entorno is None:
        pytest.skip("Se necesitan seeds de idiomas (es, en, fr), contextos y entornos.")

    usuario_a = crear_usuario(sesion, "USUARIO")
    usuario_b = crear_usuario(sesion, "USUARIO")
    usuario_a.fecha_creacion = momento(1)
    usuario_b.fecha_creacion = momento(2)

    config = ConfiguracionTraduccion(id_usuario=usuario_a.id, id_contexto=contextos[0].id_contexto)
    sesion.add(config)
    sesion.flush()

    for dia in (5, 5, 6):
        sesion.add(Traduccion(
            texto_original="hola", texto_traducido="hello", fecha_creacion=momento(dia),
            id_configuracion_traduccion=config.id_configuracion_traduccion,
            id_idioma_origen=idiomas["es"].id_idioma, id_idioma_destino=idiomas["en"].id_idioma,
            id_usuario=usuario_a.id,
        ))
    for estado in ("COMPLETADO", "ERROR"):
        sesion.add(TraduccionDocumento(
            nombre="doc.docx", extension="docx", estado=estado, fecha=momento(6),
            ruta_archivo="/x", id_usuario=usuario_a.id,
            id_idioma_origen=idiomas["es"].id_idioma, id_idioma_destino=idiomas["fr"].id_idioma,
        ))
    sesion.add(Conversacion(
        fecha_inicio=momento(7), id_usuario=usuario_b.id, id_entorno=entorno.id_entorno,
        id_idioma_origen=idiomas["en"].id_idioma, id_idioma_destino=idiomas["es"].id_idioma,
        id_contexto=contextos[1].id_contexto,
    ))
    sesion.commit()
    return {"idiomas": idiomas, "contextos": contextos, "usuarios": (usuario_a, usuario_b)}

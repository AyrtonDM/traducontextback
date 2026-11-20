from datetime import datetime, timedelta, timezone

try:
    from datetime import UTC
except ImportError:
    UTC = timezone.utc

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session, selectinload

from app.database.conexion import obtener_sesion
from app.models.usuario.codigo_verificacion import CodigoVerificacion

from app.models.usuario.rol_permiso import RolPermiso
from app.models.usuario.permiso import Permiso
from app.models.usuario.rol import Rol
from app.models.usuario.usuario import Usuario
from app.models.usuario.sesion import Sesion
from app.schemas.usuario import (
    ReenviarCodigoSolicitud,
    RegistroUsuarioSolicitud,
    VerificarCodigoSolicitud,
)
from app.utilities.correo import enviar_correo
from app.utilities.seguridad import generar_codigo_verificacion, hashear_contrasena


ESTADO_ACTIVO = "ACTIVO"
ESTADO_INACTIVO = "INACTIVO"
ESTADO_SUSPENDIDO = "SUSPENDIDO"
ESTADOS_USUARIO = (ESTADO_ACTIVO, ESTADO_INACTIVO, ESTADO_SUSPENDIDO)
ROL_USUARIO = "USUARIO"
ROL_ADMINISTRADOR = "ADMINISTRADOR"
MENSAJE_CUENTA_SUSPENDIDA = "La cuenta esta suspendida. Contacta con un administrador."
MINUTOS_EXPIRACION_CODIGO = 10


def obtener_usuario_actual(
    authorization: str | None = Header(None, description="Token Bearer de autorizacion"),
    sesion_db: Session = Depends(obtener_sesion),
) -> Usuario:
    """Valida el token de sesion y retorna el usuario actual con su rol."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales de autenticacion no proporcionadas o invalidas.",
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Formato de autorizacion invalido. Use 'Bearer <token>'.",
        )

    partes = authorization.split(" ")
    if len(partes) < 2 or not partes[1].strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token no proporcionado en la cabecera de autorizacion.",
        )

    token = partes[1].strip()

    # Buscar sesion activa
    sesion_usuario = sesion_db.scalar(
        select(Sesion)
        .where(Sesion.token == token)
        .where(Sesion.estado == "ACTIVA")
    )

    if sesion_usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de sesion invalido o ya cerrado.",
        )

    # Verificar expiracion
    # Si la fecha de expiracion no tiene zona horaria, nos aseguramos de que coincida
    ahora = datetime.now(timezone.utc)
    if sesion_usuario.fecha_expiracion.tzinfo is None:
        ahora = ahora.replace(tzinfo=None)

    if sesion_usuario.fecha_expiracion < ahora:
        # Actualizar estado de la sesion a EXPIRADA
        sesion_usuario.estado = "EXPIRADA"
        sesion_db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La sesion ha expirado.",
        )

    # Buscar usuario
    usuario = sesion_db.scalar(
        select(Usuario)
        .where(Usuario.id == sesion_usuario.id_usuario)
        .where(Usuario.estado == ESTADO_ACTIVO)
    )

    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inactivo o no encontrado.",
        )

    return usuario

def obtener_permisos_usuario(
    sesion_db: Session,
    usuario: Usuario,
) -> list[str]:
    """Obtiene los permisos asociados al rol del usuario."""
    permisos = sesion_db.scalars(
        select(Permiso)
        .join(RolPermiso)
        .where(RolPermiso.id_rol == usuario.id_rol)
    ).all()

    return [permiso.nombre for permiso in permisos]

class CorreoYaRegistradoError(ValueError):
    pass


class RolUsuarioNoExisteError(RuntimeError):
    pass


class CodigoVerificacionInvalidoError(ValueError):
    pass


class UsuarioYaActivoError(ValueError):
    pass


class UsuarioNoEncontradoError(ValueError):
    pass


class UsuarioSuspendidoError(ValueError):
    pass


class OperacionAdministracionInvalidaError(ValueError):
    """Accion de administracion no permitida (sobre la propia cuenta o por el estado actual)."""


class RolNoEncontradoError(ValueError):
    pass


def registrar_usuario(
    sesion: Session,
    datos: RegistroUsuarioSolicitud,
) -> Usuario:
    usuario_existente = sesion.scalar(
        select(Usuario).where(Usuario.correo == datos.correo)
    )

    if usuario_existente is not None:
        raise CorreoYaRegistradoError("El correo ya se encuentra registrado.")

    rol_usuario = sesion.scalar(select(Rol).where(Rol.nombre == ROL_USUARIO))

    if rol_usuario is None:
        raise RolUsuarioNoExisteError("No existe el rol USUARIO.")

    usuario = Usuario(
        nombre=datos.nombre,
        correo=datos.correo,
        contrasena=hashear_contrasena(datos.contrasena),
        estado=ESTADO_INACTIVO,
        rol=rol_usuario,
    )

    sesion.add(usuario)
    sesion.flush()

    codigo = generar_codigo_verificacion()
    codigo_verificacion = CodigoVerificacion(
        id_usuario=usuario.id,
        codigo=codigo,
        expira_en=datetime.now(UTC) + timedelta(minutes=MINUTOS_EXPIRACION_CODIGO),
        utilizado=False,
    )

    sesion.add(codigo_verificacion)

    enviar_correo_verificacion(usuario.correo, usuario.nombre, codigo)
    sesion.commit()
    sesion.refresh(usuario)

    return usuario


def reenviar_codigo_verificacion(
    sesion: Session,
    datos: ReenviarCodigoSolicitud,
) -> Usuario:
    usuario = sesion.scalar(
        select(Usuario).where(Usuario.correo == datos.correo)
    )

    if usuario is None:
        raise UsuarioNoEncontradoError("No existe un usuario con ese correo.")

    if usuario.estado == ESTADO_SUSPENDIDO:
        raise UsuarioSuspendidoError(MENSAJE_CUENTA_SUSPENDIDA)

    if usuario.estado == ESTADO_ACTIVO:
        raise UsuarioYaActivoError("El usuario ya se encuentra activo.")

    invalidar_codigos_pendientes(sesion, usuario.id)

    codigo = generar_codigo_verificacion()
    codigo_verificacion = CodigoVerificacion(
        id_usuario=usuario.id,
        codigo=codigo,
        expira_en=datetime.now(UTC) + timedelta(minutes=MINUTOS_EXPIRACION_CODIGO),
        utilizado=False,
    )

    sesion.add(codigo_verificacion)

    enviar_correo_verificacion(usuario.correo, usuario.nombre, codigo)
    sesion.commit()
    sesion.refresh(usuario)

    return usuario


def verificar_codigo_usuario(
    sesion: Session,
    datos: VerificarCodigoSolicitud,
) -> Usuario:
    usuario = sesion.scalar(
        select(Usuario).where(Usuario.correo == datos.correo)
    )

    if usuario is None:
        raise CodigoVerificacionInvalidoError("Codigo de verificacion invalido.")

    if usuario.estado == ESTADO_SUSPENDIDO:
        raise UsuarioSuspendidoError(MENSAJE_CUENTA_SUSPENDIDA)

    if usuario.estado == ESTADO_ACTIVO:
        raise UsuarioYaActivoError("El usuario ya se encuentra activo.")

    codigo_verificacion = sesion.scalar(
        select(CodigoVerificacion)
        .where(CodigoVerificacion.id_usuario == usuario.id)
        .where(CodigoVerificacion.codigo == datos.codigo)
        .where(CodigoVerificacion.utilizado.is_(False))
        .order_by(CodigoVerificacion.creado_en.desc())
    )

    if codigo_verificacion is None:
        raise CodigoVerificacionInvalidoError("Codigo de verificacion invalido.")

    if codigo_verificacion.expira_en <= datetime.now(UTC):
        raise CodigoVerificacionInvalidoError("El codigo de verificacion expiro.")

    codigo_verificacion.utilizado = True
    usuario.estado = ESTADO_ACTIVO
    usuario.fecha_actualizacion = datetime.now(UTC)

    sesion.commit()
    sesion.refresh(usuario)

    return usuario


def invalidar_codigos_pendientes(sesion: Session, id_usuario: int) -> None:
    sesion.execute(
        update(CodigoVerificacion)
        .where(CodigoVerificacion.id_usuario == id_usuario)
        .where(CodigoVerificacion.utilizado.is_(False))
        .values(utilizado=True)
    )


def enviar_correo_verificacion(correo: str, nombre: str, codigo: str) -> None:
    enviar_correo(
        destinatarios=correo,
        asunto="Codigo de verificacion - TraduContext",
        html=(
            f"<p>Hola {nombre},</p>"
            "<p>Usa este codigo para activar tu cuenta:</p>"
            f"<h2>{codigo}</h2>"
            f"<p>Este codigo vence en {MINUTOS_EXPIRACION_CODIGO} minutos.</p>"
        ),
        texto=(
            f"Hola {nombre}. "
            f"Tu codigo de verificacion es {codigo}. "
            f"Vence en {MINUTOS_EXPIRACION_CODIGO} minutos."
        ),
    )


# ---------------------------------------------------------------------------
# Administracion de usuarios (HU-05)
# ---------------------------------------------------------------------------


def listar_usuarios_admin(
    sesion: Session,
    pagina: int = 1,
    tamano_pagina: int = 10,
    busqueda: str | None = None,
    id_rol: int | None = None,
    estado: str | None = None,
) -> tuple[list[Usuario], int]:
    """
    Lista paginada de usuarios con busqueda por nombre o correo y filtros por rol y estado.
    Retorna (usuarios de la pagina, total de coincidencias).
    """
    filtros = []
    if busqueda and busqueda.strip():
        patron = f"%{busqueda.strip()}%"
        filtros.append(or_(Usuario.nombre.ilike(patron), Usuario.correo.ilike(patron)))
    if id_rol is not None:
        filtros.append(Usuario.id_rol == id_rol)
    if estado:
        filtros.append(Usuario.estado == estado)

    total = sesion.scalar(select(func.count()).select_from(Usuario).where(*filtros)) or 0
    usuarios = sesion.scalars(
        select(Usuario)
        .options(selectinload(Usuario.rol))
        .where(*filtros)
        .order_by(Usuario.fecha_creacion.desc(), Usuario.id.desc())
        .offset((pagina - 1) * tamano_pagina)
        .limit(tamano_pagina)
    ).all()
    return list(usuarios), total


def obtener_usuario_admin(sesion: Session, id_usuario: int) -> Usuario:
    usuario = sesion.scalar(
        select(Usuario).options(selectinload(Usuario.rol)).where(Usuario.id == id_usuario)
    )
    if usuario is None:
        raise UsuarioNoEncontradoError("El usuario no existe.")
    return usuario


def obtener_resumen_actividad_usuario(sesion: Session, id_usuario: int) -> dict:
    """Datos complementarios del detalle de una cuenta: accesos y uso de la plataforma."""
    from app.models.conversacion.conversacion import Conversacion
    from app.models.documento.documento import Documento
    from app.models.glosario.glosario import Glosario
    from app.models.traduccion.traduccion import Traduccion

    def contar(modelo) -> int:
        return sesion.scalar(
            select(func.count()).select_from(modelo).where(modelo.id_usuario == id_usuario)
        ) or 0

    return {
        "ultimo_acceso": sesion.scalar(
            select(func.max(Sesion.fecha_inicio)).where(Sesion.id_usuario == id_usuario)
        ),
        "sesiones_activas": sesion.scalar(
            select(func.count())
            .select_from(Sesion)
            .where(Sesion.id_usuario == id_usuario, Sesion.estado == "ACTIVA")
        ) or 0,
        "total_traducciones": contar(Traduccion),
        "total_documentos": contar(Documento),
        "total_conversaciones": contar(Conversacion),
        "total_glosarios": contar(Glosario),
    }


def cerrar_sesiones_usuario(sesion: Session, id_usuario: int) -> None:
    """Invalida todas las sesiones activas del usuario."""
    sesion.execute(
        update(Sesion)
        .where(Sesion.id_usuario == id_usuario)
        .where(Sesion.estado == "ACTIVA")
        .values(estado="CERRADA", fecha_cierre=datetime.now(UTC))
    )


def suspender_usuario(sesion: Session, administrador: Usuario, id_usuario: int) -> Usuario:
    """Suspende una cuenta activa e invalida sus sesiones. No elimina informacion asociada."""
    if administrador.id == id_usuario:
        raise OperacionAdministracionInvalidaError("No puedes suspender tu propia cuenta.")

    usuario = obtener_usuario_admin(sesion, id_usuario)
    if usuario.estado == ESTADO_SUSPENDIDO:
        raise OperacionAdministracionInvalidaError("La cuenta ya se encuentra suspendida.")
    if usuario.estado != ESTADO_ACTIVO:
        raise OperacionAdministracionInvalidaError(
            "Solo se pueden suspender cuentas activas; esta cuenta aun no fue verificada."
        )

    usuario.estado = ESTADO_SUSPENDIDO
    usuario.fecha_actualizacion = datetime.now(UTC)
    cerrar_sesiones_usuario(sesion, usuario.id)
    sesion.commit()
    sesion.refresh(usuario)
    return usuario


def reactivar_usuario(sesion: Session, id_usuario: int) -> Usuario:
    usuario = obtener_usuario_admin(sesion, id_usuario)
    if usuario.estado != ESTADO_SUSPENDIDO:
        raise OperacionAdministracionInvalidaError("Solo se pueden reactivar cuentas suspendidas.")

    usuario.estado = ESTADO_ACTIVO
    usuario.fecha_actualizacion = datetime.now(UTC)
    sesion.commit()
    sesion.refresh(usuario)
    return usuario


def cambiar_rol_usuario(
    sesion: Session,
    administrador: Usuario,
    id_usuario: int,
    id_rol: int,
) -> Usuario:
    rol = sesion.get(Rol, id_rol)
    if rol is None:
        raise RolNoEncontradoError("El rol indicado no existe.")

    if administrador.id == id_usuario and rol.nombre != ROL_ADMINISTRADOR:
        raise OperacionAdministracionInvalidaError(
            "No puedes quitarte el rol de Administrador."
        )

    usuario = obtener_usuario_admin(sesion, id_usuario)
    if usuario.id_rol != rol.id:
        usuario.id_rol = rol.id
        usuario.fecha_actualizacion = datetime.now(UTC)
        sesion.commit()
        sesion.expire(usuario, ["rol"])
        sesion.refresh(usuario)
    return usuario


def listar_roles(sesion: Session) -> list[Rol]:
    return list(sesion.scalars(select(Rol).order_by(Rol.id)).all())


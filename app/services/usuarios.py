from datetime import UTC, datetime, timedelta, timezone

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

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
ROL_USUARIO = "USUARIO"
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


def obtener_todos_usuarios(sesion: Session) -> list[Usuario]:
    """Retorna la lista de todos los usuarios registrados en el sistema."""
    return list(sesion.scalars(select(Usuario)).all())


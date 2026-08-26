from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.usuario.codigo_verificacion import CodigoVerificacion
from app.models.usuario.rol import Rol
from app.models.usuario.usuario import Usuario
from app.schemas.usuario import RegistroUsuarioSolicitud, VerificarCodigoSolicitud
from app.utilities.correo import enviar_correo
from app.utilities.seguridad import generar_codigo_verificacion, hashear_contrasena


ESTADO_ACTIVO = "ACTIVO"
ESTADO_INACTIVO = "INACTIVO"
ROL_CLIENTE = "CLIENTE"
MINUTOS_EXPIRACION_CODIGO = 10


class CorreoYaRegistradoError(ValueError):
    pass


class RolClienteNoExisteError(RuntimeError):
    pass


class CodigoVerificacionInvalidoError(ValueError):
    pass


class UsuarioYaActivoError(ValueError):
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

    rol_cliente = sesion.scalar(select(Rol).where(Rol.nombre == ROL_CLIENTE))

    if rol_cliente is None:
        raise RolClienteNoExisteError("No existe el rol CLIENTE.")

    usuario = Usuario(
        nombre=datos.nombre,
        correo=datos.correo,
        contrasena=hashear_contrasena(datos.contrasena),
        estado=ESTADO_INACTIVO,
        rol=rol_cliente,
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

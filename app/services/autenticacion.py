from datetime import datetime, timedelta, UTC
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.usuario.usuario import Usuario
from app.models.usuario.sesion import Sesion
from app.models.usuario.codigo_verificacion import CodigoVerificacion
from app.schemas.autenticacion import (
    LoginSolicitud,
    RestablecerContrasenaSolicitud,
    SolicitarRecuperacionSolicitud,
)
from app.core.seguridad import verificar_contrasena, generar_token_sesion
from app.utilities.correo import enviar_correo
from app.utilities.seguridad import generar_codigo_verificacion, hashear_contrasena

DURACION_SESION_DIAS = 7
MINUTOS_EXPIRACION_RECUPERACION = 10


class CredencialesInvalidasError(ValueError):
    pass


class UsuarioInactivoError(ValueError):
    pass


class SesionInvalidaError(ValueError):
    pass


class CodigoRecuperacionInvalidoError(ValueError):
    pass


def iniciar_sesion(sesion_db: Session, datos: LoginSolicitud) -> Sesion:
    """Valida credenciales, inactiva sesiones anteriores y genera una nueva sesión activa."""
    usuario = sesion_db.scalar(
        select(Usuario).where(Usuario.correo == datos.correo)
    )

    if usuario is None:
        raise CredencialesInvalidasError("Correo o contrasena incorrectos.")

    if not verificar_contrasena(datos.contrasena, usuario.contrasena):
        raise CredencialesInvalidasError("Correo o contrasena incorrectos.")

    if usuario.estado != "ACTIVO":
        raise UsuarioInactivoError("La cuenta del usuario no esta activa.")

    # Marcar sesiones previas de este usuario como CERRADAS
    sesion_db.execute(
        update(Sesion)
        .where(Sesion.id_usuario == usuario.id)
        .where(Sesion.estado == "ACTIVA")
        .values(estado="CERRADA", fecha_cierre=datetime.now(UTC))
    )

    token = generar_token_sesion()
    nueva_sesion = Sesion(
        id_usuario=usuario.id,
        token=token,
        fecha_inicio=datetime.now(UTC),
        fecha_expiracion=datetime.now(UTC) + timedelta(days=DURACION_SESION_DIAS),
        estado="ACTIVA",
    )

    sesion_db.add(nueva_sesion)
    sesion_db.commit()
    sesion_db.refresh(nueva_sesion)

    return nueva_sesion


def cerrar_sesion(sesion_db: Session, token: str) -> None:
    """Busca una sesión activa por su token y la cierra actualizando estado y fecha de cierre."""
    sesion_usuario = sesion_db.scalar(
        select(Sesion).where(Sesion.token == token).where(Sesion.estado == "ACTIVA")
    )

    if sesion_usuario is None:
        raise SesionInvalidaError("Token de sesion invalido o ya expirado.")

    sesion_usuario.estado = "CERRADA"
    sesion_usuario.fecha_cierre = datetime.now(UTC)

    sesion_db.commit()


def solicitar_recuperacion(
    sesion_db: Session,
    datos: SolicitarRecuperacionSolicitud,
) -> None:
    """Genera y envia un codigo sin revelar si el correo esta registrado."""
    usuario = sesion_db.scalar(
        select(Usuario).where(
            Usuario.correo == datos.correo,
            Usuario.estado == "ACTIVO",
        )
    )

    if usuario is None:
        return

    invalidar_codigos_recuperacion(sesion_db, usuario.id)
    codigo = generar_codigo_verificacion()
    sesion_db.add(
        CodigoVerificacion(
            id_usuario=usuario.id,
            codigo=codigo,
            expira_en=datetime.now(UTC)
            + timedelta(minutes=MINUTOS_EXPIRACION_RECUPERACION),
            utilizado=False,
        )
    )
    enviar_correo_recuperacion(usuario.correo, usuario.nombre, codigo)
    sesion_db.commit()


def restablecer_contrasena(
    sesion_db: Session,
    datos: RestablecerContrasenaSolicitud,
) -> None:
    usuario = sesion_db.scalar(
        select(Usuario).where(
            Usuario.correo == datos.correo,
            Usuario.estado == "ACTIVO",
        )
    )
    codigo = None
    if usuario is not None:
        codigo = sesion_db.scalar(
            select(CodigoVerificacion)
            .where(CodigoVerificacion.id_usuario == usuario.id)
            .where(CodigoVerificacion.codigo == datos.codigo)
            .where(CodigoVerificacion.utilizado.is_(False))
            .order_by(CodigoVerificacion.creado_en.desc())
        )

    if codigo is None or codigo.expira_en <= datetime.now(UTC):
        raise CodigoRecuperacionInvalidoError(
            "El codigo de recuperacion es invalido o expiro."
        )

    codigo.utilizado = True
    usuario.contrasena = hashear_contrasena(datos.nueva_contrasena)
    usuario.fecha_actualizacion = datetime.now(UTC)
    sesion_db.execute(
        update(Sesion)
        .where(Sesion.id_usuario == usuario.id)
        .where(Sesion.estado == "ACTIVA")
        .values(estado="CERRADA", fecha_cierre=datetime.now(UTC))
    )
    sesion_db.commit()


def invalidar_codigos_recuperacion(sesion_db: Session, id_usuario: int) -> None:
    sesion_db.execute(
        update(CodigoVerificacion)
        .where(CodigoVerificacion.id_usuario == id_usuario)
        .where(CodigoVerificacion.utilizado.is_(False))
        .values(utilizado=True)
    )


def enviar_correo_recuperacion(correo: str, nombre: str, codigo: str) -> None:
    enviar_correo(
        destinatarios=correo,
        asunto="Recuperacion de contrasena - TraduContext",
        html=(
            f"<p>Hola {nombre},</p>"
            "<p>Usa este codigo para cambiar tu contrasena:</p>"
            f"<h2>{codigo}</h2>"
            f"<p>Este codigo vence en {MINUTOS_EXPIRACION_RECUPERACION} minutos.</p>"
        ),
        texto=(
            f"Hola {nombre}. Tu codigo de recuperacion es {codigo}. "
            f"Vence en {MINUTOS_EXPIRACION_RECUPERACION} minutos."
        ),
    )

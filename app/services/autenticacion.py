from datetime import datetime, timedelta, UTC
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.usuario.usuario import Usuario
from app.models.usuario.sesion import Sesion
from app.schemas.autenticacion import LoginSolicitud
from app.core.seguridad import verificar_contrasena, generar_token_sesion

DURACION_SESION_DIAS = 7


class CredencialesInvalidasError(ValueError):
    pass


class UsuarioInactivoError(ValueError):
    pass


class SesionInvalidaError(ValueError):
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

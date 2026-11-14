from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.usuario.usuario import Usuario
from app.schemas.perfil import (
    ActualizarPerfilSolicitud,
    PerfilDetalle,
)
from app.schemas.usuario import RolDetalle
from app.services.configuracion_traduccion import (
    armar_detalle_configuracion,
    obtener_configuracion_usuario,
)


class CorreoEnUsoError(ValueError):
    pass


def armar_detalle_perfil(sesion: Session, usuario: Usuario) -> PerfilDetalle:
    """Construye el perfil del usuario autenticado junto a su configuracion de traduccion."""
    config = obtener_configuracion_usuario(sesion=sesion, id_usuario=usuario.id)
    detalle_config = (
        armar_detalle_configuracion(config=config, sesion=sesion) if config else None
    )

    return PerfilDetalle(
        id=usuario.id,
        nombre=usuario.nombre,
        correo=usuario.correo,
        estado=usuario.estado,
        rol=RolDetalle.model_validate(usuario.rol),
        fecha_creacion=usuario.fecha_creacion,
        fecha_actualizacion=usuario.fecha_actualizacion,
        configuracion_traduccion=detalle_config,
    )


def actualizar_perfil(
    sesion: Session,
    usuario: Usuario,
    datos: ActualizarPerfilSolicitud,
) -> Usuario:
    """Actualiza los datos editables del perfil (nombre y correo) del usuario autenticado."""
    if datos.correo is not None and datos.correo != usuario.correo:
        correo_ocupado = sesion.scalar(
            select(Usuario.id)
            .where(Usuario.correo == datos.correo)
            .where(Usuario.id != usuario.id)
        )
        if correo_ocupado is not None:
            raise CorreoEnUsoError("El correo ya pertenece a otra cuenta.")

        usuario.correo = datos.correo

    if datos.nombre is not None:
        usuario.nombre = datos.nombre

    usuario.fecha_actualizacion = datetime.now(UTC)

    try:
        sesion.commit()
    except IntegrityError as error:
        # Otra cuenta tomo el correo entre la validacion y el guardado
        sesion.rollback()
        raise CorreoEnUsoError("El correo ya pertenece a otra cuenta.") from error

    sesion.refresh(usuario)
    return usuario


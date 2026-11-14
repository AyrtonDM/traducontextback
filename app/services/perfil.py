import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.configuracion import RUTA_BASE
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


CARPETA_FOTOS_PERFIL = RUTA_BASE / "documentos" / "fotos_perfil"
CARPETA_FOTOS_PERFIL.mkdir(parents=True, exist_ok=True)

URL_FOTO_PERFIL = "/api/v1/perfil/foto"

TAMANO_MAXIMO_FOTO = 5 * 1024 * 1024  # 5 MB

TIPOS_FOTO_PERMITIDOS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}

TIPOS_MIME_POR_EXTENSION = {ext: mime for mime, ext in TIPOS_FOTO_PERMITIDOS.items()}


class FotoPerfilInvalidaError(ValueError):
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
        url_foto_perfil=URL_FOTO_PERFIL if obtener_ruta_foto(usuario) else None,
        configuracion_traduccion=detalle_config,
    )


def actualizar_perfil(
    sesion: Session,
    usuario: Usuario,
    datos: ActualizarPerfilSolicitud,
) -> Usuario:
    """Actualiza el nombre del usuario autenticado (el correo no es editable)."""
    usuario.nombre = datos.nombre
    usuario.fecha_actualizacion = datetime.now(UTC)

    sesion.commit()
    sesion.refresh(usuario)
    return usuario


def obtener_ruta_foto(usuario: Usuario) -> Path | None:
    """Ruta absoluta de la foto de perfil, solo si existe fisicamente."""
    if not usuario.foto_perfil:
        return None

    ruta = RUTA_BASE / usuario.foto_perfil
    return ruta if ruta.is_file() else None


def _eliminar_archivo_foto(ruta_relativa: str | None) -> None:
    if not ruta_relativa:
        return

    ruta = RUTA_BASE / ruta_relativa
    # Solo se borran archivos dentro de la carpeta de fotos de perfil
    if ruta.resolve().parent == CARPETA_FOTOS_PERFIL.resolve():
        ruta.unlink(missing_ok=True)


def guardar_foto_perfil(
    sesion: Session,
    usuario: Usuario,
    archivo: UploadFile,
) -> Usuario:
    """Guarda la foto en documentos/fotos_perfil y registra su ruta relativa en el usuario."""
    extension = TIPOS_FOTO_PERMITIDOS.get((archivo.content_type or "").lower())
    if extension is None:
        raise FotoPerfilInvalidaError(
            "Formato de imagen no soportado. Solo se permiten JPG, PNG o WEBP."
        )

    contenido = archivo.file.read(TAMANO_MAXIMO_FOTO + 1)
    if not contenido:
        raise FotoPerfilInvalidaError("La imagen esta vacia.")
    if len(contenido) > TAMANO_MAXIMO_FOTO:
        raise FotoPerfilInvalidaError("La imagen no puede superar los 5 MB.")

    nombre_archivo = f"usuario_{usuario.id}_{uuid.uuid4().hex}.{extension}"
    ruta_absoluta = CARPETA_FOTOS_PERFIL / nombre_archivo
    ruta_absoluta.write_bytes(contenido)

    ruta_anterior = usuario.foto_perfil
    usuario.foto_perfil = ruta_absoluta.relative_to(RUTA_BASE).as_posix()
    usuario.fecha_actualizacion = datetime.now(UTC)

    try:
        sesion.commit()
    except Exception:
        sesion.rollback()
        ruta_absoluta.unlink(missing_ok=True)
        raise

    _eliminar_archivo_foto(ruta_anterior)
    sesion.refresh(usuario)
    return usuario


def eliminar_foto_perfil(sesion: Session, usuario: Usuario) -> Usuario:
    """Quita la foto de perfil del usuario y borra el archivo."""
    ruta_anterior = usuario.foto_perfil
    if ruta_anterior is None:
        return usuario

    usuario.foto_perfil = None
    usuario.fecha_actualizacion = datetime.now(UTC)
    sesion.commit()

    _eliminar_archivo_foto(ruta_anterior)
    sesion.refresh(usuario)
    return usuario

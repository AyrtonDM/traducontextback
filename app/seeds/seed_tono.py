from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.traduccion.tono import Tono


TONOS_BASE = (
    (
        "Neutral",
        "Tono equilibrado, claro y directo, adecuado para comunicacion general sin inclinacion formal ni informal.",
    ),
    (
        "Formal",
        "Tono respetuoso, protocolar y estructurado, adecuado para documentos oficiales, correspondencia institucional o ambitos academicos.",
    ),
    (
        "Informal",
        "Tono cercano, casual y coloquial, adecuado para conversaciones cotidianas, mensajes amistosos y redes sociales.",
    ),
    (
        "Profesional",
        "Tono corporativo, preciso y pulido, adecuado para entornos laborales, presentaciones de negocios y comunicacion entre colegas o clientes.",
    ),
)


def sembrar_tonos(sesion: Session) -> None:
    """Crea los tonos base en la base de datos si no existen."""
    nombres_existentes = set(
        sesion.scalars(select(Tono.nombre)).all()
    )

    for nombre, descripcion in TONOS_BASE:
        if nombre not in nombres_existentes:
            sesion.add(
                Tono(
                    nombre=nombre,
                    descripcion=descripcion,
                    activo=True,
                )
            )

    sesion.flush()


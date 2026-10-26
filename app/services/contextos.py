from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.traduccion.contexto import Contexto
from app.seeds.seed_contexto import sembrar_contextos


def obtener_todos_contextos(
    sesion: Session,
    solo_activos: bool = True,
    id_usuario: int | None = None,
) -> list[Contexto]:
    """Retorna la lista de contextos registrados en el sistema."""
    consulta = select(Contexto)
    if solo_activos:
        consulta = consulta.where(Contexto.activo.is_(True))
    if id_usuario is not None:
        consulta = consulta.where(
            (Contexto.id_usuario == id_usuario) | (Contexto.id_usuario.is_(None))
        )
    consulta = consulta.order_by(Contexto.id_contexto.asc())

    contextos = list(sesion.scalars(consulta).all())
    if not contextos:
        sembrar_contextos(sesion)
        sesion.commit()
        contextos = list(sesion.scalars(consulta).all())

    return contextos


def guardar_nuevo_contexto(
    sesion: Session,
    nombre: str,
    descripcion: str | None = None,
    id_usuario: int | None = None,
) -> Contexto:
    """Crea y guarda un nuevo contexto en la base de datos."""
    nombre_limpio = nombre.strip()
    descripcion_limpia = descripcion.strip() if descripcion else None

    consulta_existente = select(Contexto).where(
        func.lower(Contexto.nombre) == func.lower(nombre_limpio)
    )
    if id_usuario is not None:
        consulta_existente = consulta_existente.where(
            (Contexto.id_usuario == id_usuario) | (Contexto.id_usuario.is_(None))
        )

    existente = sesion.scalar(consulta_existente)
    if existente:
        raise ValueError(f"Ya existe un contexto registrado con el nombre '{nombre_limpio}'.")

    nuevo_contexto = Contexto(
        nombre=nombre_limpio,
        descripcion=descripcion_limpia,
        personalizado=True,
        activo=True,
        id_usuario=id_usuario,
    )
    sesion.add(nuevo_contexto)
    sesion.commit()
    sesion.refresh(nuevo_contexto)
    return nuevo_contexto

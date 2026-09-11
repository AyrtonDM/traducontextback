from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.traduccion.contexto import Contexto
from app.models.usuario.usuario import Usuario


CONTEXTOS_BASE = (
    (
        "Tecnico",
        "Contexto relacionado con tecnologia, ingenieria, informatica, software, "
        "hardware y terminologia especializada. Se deben conservar o interpretar "
        "correctamente los terminos tecnicos y acronimos propios del area.",
    ),
    (
        "Legal",
        "Contexto relacionado con leyes, contratos, normativa, procedimientos "
        "juridicos, derechos y obligaciones. Se debe mantener la precisi\u00f3n de la "
        "terminologia juridica y evitar interpretaciones coloquiales.",
    ),
    (
        "Medico",
        "Contexto relacionado con medicina, salud, enfermedades, sintomas, "
        "diagnosticos, tratamientos, medicamentos y terminologia clinica. Se debe "
        "preservar el significado preciso de los terminos medicos.",
    ),
    (
        "Comercial",
        "Contexto relacionado con negocios, ventas, marketing, clientes, productos, "
        "servicios, precios, acuerdos y transacciones comerciales. Se debe utilizar "
        "terminologia apropiada para comunicaciones empresariales y comerciales.",
    ),
    (
        "Coloquial",
        "Contexto relacionado con conversaciones cotidianas e informales. Se deben "
        "interpretar expresiones comunes, modismos, frases informales y formas "
        "naturales de comunicacion, priorizando un lenguaje fluido y comprensible.",
    ),
)


def sembrar_contextos(sesion: Session) -> None:
    """Crea los contextos base para cada usuario existente, sin duplicarlos."""

    usuarios = sesion.scalars(select(Usuario)).all()

    for usuario in usuarios:
        nombres_existentes = set(
            sesion.scalars(
                select(Contexto.nombre).where(Contexto.id_usuario == usuario.id)
            ).all()
        )

        for nombre, descripcion in CONTEXTOS_BASE:
            if nombre not in nombres_existentes:
                sesion.add(
                    Contexto(
                        nombre=nombre,
                        descripcion=descripcion,
                        id_usuario=usuario.id,
                    )
                )

    sesion.flush()
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conversacion.entorno import Entorno


ENTORNOS_BASE = (
    (
        "Reunion",
        "Reunion de trabajo o de equipo. Se priorizan acuerdos, tareas y un lenguaje "
        "claro y profesional entre varios participantes.",
    ),
    (
        "Conferencia",
        "Exposicion ante un publico, con predominio de un orador. Se priorizan la "
        "terminologia del tema y la fluidez del discurso.",
    ),
    (
        "Clase",
        "Entorno educativo entre docente y estudiantes. Se priorizan las explicaciones, "
        "los conceptos y las preguntas didacticas.",
    ),
    (
        "Entrevista",
        "Dialogo estructurado de preguntas y respuestas (laboral, periodistica, etc.). "
        "Se prioriza la precision y el registro formal.",
    ),
    (
        "Conversacion informal",
        "Charla cotidiana y espontanea. Se aceptan expresiones coloquiales y un "
        "registro cercano.",
    ),
)


def sembrar_entornos(sesion: Session) -> None:
    """Crea los entornos de conversacion base, sin duplicarlos."""

    nombres_existentes = set(
        sesion.scalars(
            select(Entorno.nombre)
        ).all()
    )

    for nombre, descripcion in ENTORNOS_BASE:
        if nombre not in nombres_existentes:
            sesion.add(
                Entorno(
                    nombre=nombre,
                    descripcion=descripcion,
                    activo=True,
                )
            )

    sesion.flush()

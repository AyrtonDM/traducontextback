from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.traduccion.variante_regional import VarianteRegional
from app.seeds.seed_variante_regional import sembrar_variantes_regionales


def obtener_todas_variantes_regionales(
    sesion: Session,
    id_idioma: int | None = None,
    solo_activos: bool = True,
) -> list[VarianteRegional]:
    """Retorna la lista de variantes regionales registradas en el sistema."""
    consulta = select(VarianteRegional)
    if solo_activos:
        consulta = consulta.where(VarianteRegional.activo.is_(True))
    if id_idioma is not None:
        consulta = consulta.where(VarianteRegional.id_idioma == id_idioma)
    consulta = consulta.order_by(VarianteRegional.id_variante_regional.asc())

    variantes = list(sesion.scalars(consulta).all())
    if not variantes and id_idioma is None:
        sembrar_variantes_regionales(sesion)
        sesion.commit()
        variantes = list(sesion.scalars(consulta).all())

    return variantes


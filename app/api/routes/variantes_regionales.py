from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.seguridad import requiere_token
from app.database.conexion import obtener_sesion
from app.models.usuario.usuario import Usuario
from app.schemas.variante_regional import ListaVariantesRegionalesRespuesta
from app.services.variantes_regionales import obtener_todas_variantes_regionales


enrutador = APIRouter(
    prefix="/variantes-regionales",
    tags=["variantes-regionales"],
    dependencies=[Depends(requiere_token)],
)


@enrutador.get(
    "",
    response_model=ListaVariantesRegionalesRespuesta,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(requiere_token)],
    summary="Listar variantes regionales disponibles (requiere token)",
    description="Retorna la lista de variantes regionales registradas en la tabla variante_regional. Requiere token Bearer de autenticacion.",
)
def listar_variantes_regionales(
    id_idioma: int | None = Query(
        default=None,
        description="Filtrar por id de idioma",
    ),
    solo_activos: bool = Query(
        default=True,
        description="Filtrar solo variantes activas",
    ),
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> ListaVariantesRegionalesRespuesta:
    variantes = obtener_todas_variantes_regionales(
        sesion=sesion,
        id_idioma=id_idioma,
        solo_activos=solo_activos,
    )
    return ListaVariantesRegionalesRespuesta(
        mensaje="Variantes regionales obtenidas correctamente.",
        resultado=variantes,
    )


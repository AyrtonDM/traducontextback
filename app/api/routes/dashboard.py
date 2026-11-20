from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.seguridad import requiere_permiso
from app.database.conexion import obtener_sesion
from app.schemas.dashboard import DashboardRespuesta
from app.services.dashboard import PeriodoInvalidoError, obtener_dashboard


PERMISO_VER_DASHBOARD = "ver_dashboard"

enrutador = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(requiere_permiso(PERMISO_VER_DASHBOARD))],
)


@enrutador.get(
    "",
    response_model=DashboardRespuesta,
    status_code=status.HTTP_200_OK,
    summary="Indicadores del dashboard administrativo (HU-46)",
    description=(
        "Indicadores de uso de la plataforma en el periodo indicado: usuarios registrados, "
        "activos y nuevos; traducciones de texto, documentos traducidos, conversaciones y "
        "sesiones externas; idiomas y contextos mas utilizados, y evolucion de las traducciones. "
        "Sin fechas se usan los ultimos 30 dias. Las fechas son inclusivas y se interpretan en "
        "'zona_horaria' (por ejemplo 'America/La_Paz'). Solo para el rol Administrador."
    ),
)
def consultar_dashboard(
    fecha_desde: date | None = Query(default=None, description="Inicio del periodo (AAAA-MM-DD)"),
    fecha_hasta: date | None = Query(default=None, description="Fin del periodo (AAAA-MM-DD)"),
    zona_horaria: str = Query(default="UTC", max_length=64, description="Zona horaria IANA"),
    sesion: Session = Depends(obtener_sesion),
) -> DashboardRespuesta:
    try:
        resultado = obtener_dashboard(
            sesion,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            zona_horaria=zona_horaria,
        )
    except PeriodoInvalidoError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    return DashboardRespuesta(
        mensaje="Indicadores obtenidos correctamente.",
        resultado=resultado,
    )

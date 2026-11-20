from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.seguridad import requiere_permiso
from app.database.conexion import obtener_sesion
from app.schemas.reporte import ReporteActividadRespuesta, TipoServicio
from app.services.exportacion_reportes import (
    MAXIMO_FILAS_EXPORTACION,
    ErrorExportacionError,
    FormatoExportacion,
    exportar_reporte,
)
from app.services.reportes import (
    FiltroReporteInvalidoError,
    PeriodoInvalidoError,
    ReporteDemasiadoGrandeError,
    generar_reporte_actividad,
)


PERMISO_GENERAR_REPORTES = "generar_reportes"

enrutador = APIRouter(
    prefix="/reportes",
    tags=["reportes"],
    dependencies=[Depends(requiere_permiso(PERMISO_GENERAR_REPORTES))],
)


@enrutador.get(
    "/actividad",
    response_model=ReporteActividadRespuesta,
    status_code=status.HTTP_200_OK,
    summary="Reporte de actividad de la plataforma (HU-47)",
    description=(
        "Detalle paginado de la actividad (traducciones de texto, documentos y conversaciones) "
        "con sus totales por tipo de servicio. Los filtros son opcionales y se combinan: rango de "
        "fechas (inclusivo, en 'zona_horaria'; por defecto los ultimos 30 dias), tipo de servicio, "
        "idioma de origen, idioma de destino y contexto. Solo para el rol Administrador."
    ),
)
def reporte_actividad(
    fecha_desde: date | None = Query(default=None, description="Inicio del periodo (AAAA-MM-DD)"),
    fecha_hasta: date | None = Query(default=None, description="Fin del periodo (AAAA-MM-DD)"),
    zona_horaria: str = Query(default="UTC", max_length=64, description="Zona horaria IANA"),
    tipo_servicio: TipoServicio | None = Query(default=None),
    id_idioma_origen: int | None = Query(default=None),
    id_idioma_destino: int | None = Query(default=None),
    id_contexto: int | None = Query(default=None),
    pagina: int = Query(default=1, ge=1),
    tamano_pagina: int = Query(default=20, ge=1, le=100),
    sesion: Session = Depends(obtener_sesion),
) -> ReporteActividadRespuesta:
    try:
        reporte = generar_reporte_actividad(
            sesion,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            zona_horaria=zona_horaria,
            tipo_servicio=tipo_servicio,
            id_idioma_origen=id_idioma_origen,
            id_idioma_destino=id_idioma_destino,
            id_contexto=id_contexto,
            pagina=pagina,
            tamano_pagina=tamano_pagina,
        )
    except (PeriodoInvalidoError, FiltroReporteInvalidoError) as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    mensaje = (
        "Reporte generado correctamente."
        if reporte.totales.total
        else "No se encontraron actividades con los filtros seleccionados."
    )
    return ReporteActividadRespuesta(mensaje=mensaje, resultado=reporte)


@enrutador.get(
    "/actividad/exportar",
    response_class=Response,
    status_code=status.HTTP_200_OK,
    summary="Exportar el reporte de actividad a PDF o Excel (HU-48)",
    description=(
        "Genera un archivo descargable con el mismo reporte de /reportes/actividad (mismos filtros, "
        "todas las filas y los totales), los filtros aplicados y la fecha de generacion. El nombre "
        "del archivo incluye el tipo de reporte y la fecha. Maximo "
        f"{MAXIMO_FILAS_EXPORTACION} actividades por archivo."
    ),
    responses={
        200: {
            "content": {
                "application/pdf": {},
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {},
            },
            "description": "Archivo del reporte",
        }
    },
)
def exportar_reporte_actividad(
    formato: FormatoExportacion = Query(..., description="pdf o xlsx"),
    fecha_desde: date | None = Query(default=None),
    fecha_hasta: date | None = Query(default=None),
    zona_horaria: str = Query(default="UTC", max_length=64),
    tipo_servicio: TipoServicio | None = Query(default=None),
    id_idioma_origen: int | None = Query(default=None),
    id_idioma_destino: int | None = Query(default=None),
    id_contexto: int | None = Query(default=None),
    sesion: Session = Depends(obtener_sesion),
) -> Response:
    try:
        reporte = generar_reporte_actividad(
            sesion,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            zona_horaria=zona_horaria,
            tipo_servicio=tipo_servicio,
            id_idioma_origen=id_idioma_origen,
            id_idioma_destino=id_idioma_destino,
            id_contexto=id_contexto,
            pagina=None,
            maximo_filas=MAXIMO_FILAS_EXPORTACION,
        )
        archivo = exportar_reporte(reporte, formato)
    except (PeriodoInvalidoError, FiltroReporteInvalidoError, ReporteDemasiadoGrandeError) as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    except ErrorExportacionError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error

    return Response(
        content=archivo.contenido,
        media_type=archivo.tipo_mime,
        headers={"Content-Disposition": f'attachment; filename="{archivo.nombre}"'},
    )

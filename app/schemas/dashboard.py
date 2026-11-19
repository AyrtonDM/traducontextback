from datetime import date
from typing import Literal

from pydantic import BaseModel


AgrupacionDashboard = Literal["dia", "mes"]


class PeriodoDashboard(BaseModel):
    fecha_desde: date
    fecha_hasta: date
    zona_horaria: str
    agrupacion: AgrupacionDashboard


class IndicadoresUsuarios(BaseModel):
    total: int
    activos_periodo: int
    nuevos_periodo: int


class IndicadoresActividad(BaseModel):
    traducciones_texto: int
    documentos_traducidos: int
    conversaciones: int
    sesiones_externas: int
    # Las sesiones externas (Meet/Zoom, HU-35 a HU-41) aun no estan implementadas
    sesiones_externas_disponible: bool


class IdiomaUso(BaseModel):
    id_idioma: int
    nombre: str
    codigo: str
    total: int


class ContextoUso(BaseModel):
    id_contexto: int
    nombre: str
    total: int


class PuntoEvolucion(BaseModel):
    fecha: date
    traducciones_texto: int
    documentos: int
    conversaciones: int


class DashboardResultado(BaseModel):
    periodo: PeriodoDashboard
    usuarios: IndicadoresUsuarios
    actividad: IndicadoresActividad
    idiomas_mas_utilizados: list[IdiomaUso]
    contextos_mas_utilizados: list[ContextoUso]
    evolucion: list[PuntoEvolucion]


class DashboardRespuesta(BaseModel):
    mensaje: str
    resultado: DashboardResultado

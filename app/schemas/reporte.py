from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


TipoServicio = Literal["texto", "documento", "conversacion", "sesion_externa"]


class FiltrosReporte(BaseModel):
    """Filtros aplicados, con los nombres resueltos para mostrarlos (y exportarlos, HU-48)."""

    fecha_desde: date
    fecha_hasta: date
    zona_horaria: str
    tipo_servicio: TipoServicio | None = None
    id_idioma_origen: int | None = None
    nombre_idioma_origen: str | None = None
    id_idioma_destino: int | None = None
    nombre_idioma_destino: str | None = None
    id_contexto: int | None = None
    nombre_contexto: str | None = None


class TotalesReporte(BaseModel):
    total: int
    texto: int
    documento: int
    conversacion: int
    sesion_externa: int
    # Las sesiones externas (Meet/Zoom, HU-35 a HU-41) aun no estan implementadas
    sesion_externa_disponible: bool


class ActividadReporte(BaseModel):
    tipo_servicio: TipoServicio
    id_registro: int
    fecha: datetime
    # Misma fecha expresada en la zona horaria del reporte (para exportar, HU-48)
    fecha_local: datetime
    id_usuario: int
    nombre_usuario: str
    correo_usuario: str
    idioma_origen: str | None = None
    idioma_destino: str | None = None
    contexto: str | None = None
    estado: str | None = None
    # Dato descriptivo sin contenido del usuario: archivo (documento) o entorno (conversacion)
    detalle: str | None = None


class ReporteActividad(BaseModel):
    filtros: FiltrosReporte
    totales: TotalesReporte
    actividades: list[ActividadReporte]
    pagina: int
    tamano_pagina: int
    total_paginas: int
    fecha_generacion: datetime
    fecha_generacion_local: datetime


class ReporteActividadRespuesta(BaseModel):
    mensaje: str
    resultado: ReporteActividad

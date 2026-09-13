from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TraduccionSolicitud(BaseModel):
    texto: str = Field(..., min_length=1, max_length=5000, description="Texto a traducir")
    idioma_origen: str = Field(default="en", description="Codigo del idioma de origen (ej. 'en', 'es')")
    idioma_destino: str = Field(default="es", description="Codigo del idioma de destino (ej. 'es', 'en')")
    dominio: Optional[str] = Field(default="General", description="Dominio o contexto tematico")
    tono: Optional[str] = Field(default="Neutral", description="Tono de la traduccion")
    variante_regional: Optional[str] = Field(default=None, description="Variante regional o dialecto")
    contexto_adicional: Optional[str] = Field(default=None, max_length=300, description="Descripcion adicional del contexto")
    mostrar_alternativas: bool = Field(default=True, description="Indica si se generan alternativas de traduccion")
    explicar_modismos: bool = Field(default=False, description="Indica si se explican modismos y expresiones")
    adaptar_formato_local: bool = Field(default=False, description="Adaptar fechas, monedas y formatos locales")


class TraduccionResultado(BaseModel):
    id: Optional[int] = None
    texto_original: str
    texto_traducido: str
    idioma_origen: str
    idioma_destino: str
    dominio: str
    alternativas: list[str] = Field(default_factory=list)
    explicacion_modismos: Optional[str] = None
    fecha_creacion: Optional[str] = None


class TraduccionRespuesta(BaseModel):
    mensaje: str
    resultado: TraduccionResultado


class TraduccionItemHistorial(BaseModel):
    id: int
    texto_original: str
    texto_traducido: str
    fecha_creacion: str
    id_idioma_origen: int
    id_idioma_destino: int
    codigo_idioma_origen: Optional[str] = None
    codigo_idioma_destino: Optional[str] = None
    nombre_idioma_origen: Optional[str] = None
    nombre_idioma_destino: Optional[str] = None
    contexto: Optional[str] = None


class ListaTraduccionesRespuesta(BaseModel):
    mensaje: str
    resultado: list[TraduccionItemHistorial]


class IdiomaItem(BaseModel):
    id: int
    codigo: str
    nombre: str


class ListaIdiomasRespuesta(BaseModel):
    mensaje: str
    resultado: list[IdiomaItem]


class ContextoItem(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None


class ListaContextosRespuesta(BaseModel):
    mensaje: str
    resultado: list[ContextoItem]


class DeteccionIdiomaSolicitud(BaseModel):
    texto: str = Field(..., min_length=1, max_length=5000, description="Texto para detectar el idioma")


class DeteccionIdiomaResultado(BaseModel):
    codigo: str
    nombre: str
    confianza: float


class DeteccionIdiomaRespuesta(BaseModel):
    mensaje: str
    resultado: DeteccionIdiomaResultado

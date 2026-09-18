from pydantic import BaseModel, Field


class SolicitudTraduccion(BaseModel):
    idioma_origen: str | None = None
    idioma_destino: str
    texto_origen: str = Field(min_length=1)


class RespuestaTraduccion(BaseModel):
    texto_origen: str
    idioma_origen: str
    idioma_destino: str
    traduccion: str
    confianza_deteccion: float | None = None
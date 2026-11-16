from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class SolicitudTraduccion(BaseModel):
    idioma_destino: str
    texto_a_traducir: str | None = None
    texto_origen: str | None = None
    texto: str | None = None
    idioma_origen: str | None = None

    @model_validator(mode="before")
    @classmethod
    def normalizar_campos(cls, data: dict):
        if isinstance(data, dict):
            texto = (
                data.get("texto_a_traducir")
                or data.get("texto_origen")
                or data.get("texto")
            )
            if not texto or not str(texto).strip():
                raise ValueError("El texto a traducir es obligatorio y no puede estar vacio.")
            texto_limpio = str(texto).strip()
            data["texto_origen"] = texto_limpio
            data["texto_a_traducir"] = texto_limpio
            data["texto"] = texto_limpio

            # Normalizar idioma_origen si viene vacio
            if "idioma_origen" in data and data["idioma_origen"] is not None:
                idioma_orig = str(data["idioma_origen"]).strip()
                data["idioma_origen"] = idioma_orig.lower() if idioma_orig else None

            if "idioma_destino" in data and data["idioma_destino"] is not None:
                data["idioma_destino"] = str(data["idioma_destino"]).strip().lower()

        return data


class AlternativaTraduccion(BaseModel):
    traduccion: str
    explicacion: str | None = None


class ExplicacionExpresion(BaseModel):
    expresion: str
    significado: str
    equivalente: str | None = None


class ResultadoEnriquecimiento(BaseModel):
    alternativas: list[AlternativaTraduccion] = Field(default_factory=list)
    explicacion_expresiones: list[ExplicacionExpresion] = Field(default_factory=list)


class TraduccionResultado(BaseModel):
    texto_origen: str
    idioma_origen: str
    idioma_destino: str
    traduccion: str
    confianza_deteccion: float | None = None
    id_configuracion_traduccion: int | None = None
    id_contexto: int | None = None
    nombre_contexto: str | None = None
    id_tono: int | None = None
    nombre_tono: str | None = None
    id_variante_regional: int | None = None
    nombre_variante_regional: str | None = None
    explicar_expresiones: bool = False
    generar_alternativas: bool = False
    alternativas: list[AlternativaTraduccion] = Field(default_factory=list)
    explicacion_expresiones: list[ExplicacionExpresion] = Field(default_factory=list)
    analisis_contextual: dict | None = None


class RespuestaTraduccion(BaseModel):
    mensaje: str
    resultado: TraduccionResultado


class TraduccionHistorialDetalle(BaseModel):
    id_traduccion: int
    texto_original: str
    texto_traducido: str
    fecha_creacion: datetime
    idioma_origen: str
    idioma_destino: str
    nombre_contexto: str | None = None
    nombre_tono: str | None = None
    nombre_variante_regional: str | None = None
    explicar_expresiones: bool = False
    generar_alternativas: bool = False
    analisis_contextual: dict | None = None
    favorito: bool = False


class RespuestaHistorial(BaseModel):
    mensaje: str
    resultado: list[TraduccionHistorialDetalle]


class SolicitudFavorito(BaseModel):
    favorito: bool


class FavoritoDetalle(BaseModel):
    id_traduccion: int
    favorito: bool


class RespuestaFavorito(BaseModel):
    mensaje: str
    resultado: FavoritoDetalle


class RespuestaEliminarTraduccion(BaseModel):
    mensaje: str

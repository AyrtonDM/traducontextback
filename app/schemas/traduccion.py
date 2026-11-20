from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.glosario import TerminoAplicado


class SolicitudTraduccion(BaseModel):
    idioma_destino: str
    texto_a_traducir: str | None = None
    texto_origen: str | None = None
    texto: str | None = None
    idioma_origen: str | None = None
    id_glosario: int | None = Field(
        default=None,
        description="Glosario a aplicar (debe ser del mismo par de idiomas)",
    )
    guardar_en_historial: bool = Field(
        default=True,
        description=(
            "Si es false, la traduccion no se guarda en el historial (por ejemplo, la traduccion "
            "automatica mientras se escribe). Se puede registrar al terminar con POST /traducciones/historial."
        ),
    )
    # Valores puntuales (HU-33): si se envian, se usan solo en esta traduccion y no
    # modifican la configuracion guardada. Si se omiten, se usa la configuracion guardada.
    # Enviar null en id_tono o id_variante_regional significa "sin tono" / "sin variante".
    id_contexto: int | None = Field(default=None, description="Contexto para esta traduccion")
    id_tono: int | None = Field(default=None, description="Tono para esta traduccion")
    id_variante_regional: int | None = Field(
        default=None,
        description="Variante regional para esta traduccion",
    )
    explicar_expresiones: bool | None = Field(
        default=None,
        description="Explicar expresiones en esta traduccion",
    )
    generar_alternativas: bool | None = Field(
        default=None,
        description="Generar alternativas en esta traduccion",
    )

    def valores_sobrescritos(self) -> dict:
        """Campos de configuracion enviados explicitamente en la solicitud."""
        campos = {
            "id_contexto",
            "id_tono",
            "id_variante_regional",
            "explicar_expresiones",
            "generar_alternativas",
        }
        return {campo: getattr(self, campo) for campo in campos & self.model_fields_set}

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
    # Traduccion adaptada a la variante regional (null si no se solicito la adaptacion)
    traduccion_adaptada: str | None = None
    alternativas: list[AlternativaTraduccion] = Field(default_factory=list)
    explicacion_expresiones: list[ExplicacionExpresion] = Field(default_factory=list)


class SugerenciaTraduccion(BaseModel):
    """Traduccion anterior similar del historial del usuario (HU-44)."""

    id_traduccion: int
    texto_original: str
    texto_traducido: str
    fecha_creacion: datetime
    # 0 a 1: parecido entre el texto nuevo y el texto original de la sugerencia
    similitud: float


class TraduccionResultado(BaseModel):
    # Registro del historial creado por esta traduccion (null si no se guardo)
    id_traduccion: int | None = None
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
    # Localizacion cultural (HU-17)
    region_aplicada: bool = False
    estado_region: Literal["sin_region", "aplicada", "incompatible", "error_adaptacion"] = "sin_region"
    explicar_expresiones: bool = False
    # True solo si las explicaciones estaban activadas y el modelo respondio correctamente (HU-16)
    explicaciones_procesadas: bool = False
    generar_alternativas: bool = False
    alternativas: list[AlternativaTraduccion] = Field(default_factory=list)
    explicacion_expresiones: list[ExplicacionExpresion] = Field(default_factory=list)
    analisis_contextual: dict | None = None
    id_glosario: int | None = None
    nombre_glosario: str | None = None
    terminos_glosario_aplicados: list[TerminoAplicado] = Field(default_factory=list)
    # Reutilizacion de traducciones (HU-44): maximo 3, de mayor a menor similitud
    sugerencias: list[SugerenciaTraduccion] = Field(default_factory=list)
    # Aprendizaje de preferencias (HU-34): correcciones del usuario consideradas en esta traduccion
    correcciones_aplicadas: int = 0


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


class SolicitudRegistrarTraduccion(BaseModel):
    """Registra en el historial una traduccion ya realizada (sin volver a traducir)."""

    texto_original: str = Field(..., min_length=1, max_length=5000)
    # Puede diferir de la traduccion generada si el usuario eligio una alternativa o sugerencia
    texto_traducido: str = Field(..., min_length=1, max_length=20000)
    idioma_origen: str = Field(..., min_length=2, max_length=10)
    idioma_destino: str = Field(..., min_length=2, max_length=10)
    id_glosario: int | None = None

    @model_validator(mode="before")
    @classmethod
    def normalizar(cls, data):
        if isinstance(data, dict):
            for campo in ("texto_original", "texto_traducido"):
                if isinstance(data.get(campo), str):
                    data[campo] = data[campo].strip()
            for campo in ("idioma_origen", "idioma_destino"):
                if isinstance(data.get(campo), str):
                    data[campo] = data[campo].strip().lower()
        return data


class TraduccionRegistrada(BaseModel):
    id_traduccion: int
    fecha_creacion: datetime


class RespuestaRegistrarTraduccion(BaseModel):
    mensaje: str
    resultado: TraduccionRegistrada


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

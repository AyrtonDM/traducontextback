from pydantic import BaseModel, Field, model_validator


class SolicitudTraduccion(BaseModel):
    idioma_destino: str
    texto_a_traducir: str | None = None
    texto_origen: str | None = None
    texto: str | None = None
    idioma_origen: str | None = None
    id_contexto: int | None = None

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


class TraduccionResultado(BaseModel):
    texto_origen: str
    idioma_origen: str
    idioma_destino: str
    traduccion: str
    confianza_deteccion: float | None = None
    id_contexto: int | None = None
    nombre_contexto: str | None = None
    analisis_contextual: dict | None = None


class RespuestaTraduccion(BaseModel):
    mensaje: str
    resultado: TraduccionResultado

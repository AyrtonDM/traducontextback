from datetime import datetime

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator


def _limpiar_texto_opcional(valor: str | None) -> str | None:
    if valor is None:
        return None
    valor_limpio = valor.strip()
    return valor_limpio or None


# ---------------------------------------------------------------------------
# Terminos
# ---------------------------------------------------------------------------


class TerminoGlosarioSolicitud(BaseModel):
    termino_origen: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Termino en el idioma de origen del glosario",
    )
    traduccion_preferida: str | None = Field(
        default=None,
        max_length=255,
        description="Traduccion que debe usarse para el termino (obligatoria si no se conserva)",
    )
    conservar_original: bool = Field(
        default=False,
        description="Si es True, el termino se conserva en su idioma original",
    )
    distinguir_mayusculas: bool = Field(
        default=False,
        description="Si es True, solo coincide respetando mayusculas/minusculas",
    )
    nota: str | None = Field(default=None, description="Regla u observacion sobre el termino")

    @field_validator("termino_origen")
    @classmethod
    def validar_termino(cls, valor: str) -> str:
        valor_limpio = valor.strip()
        if not valor_limpio:
            raise ValueError("El termino de origen no puede estar vacio.")
        return valor_limpio

    @field_validator("traduccion_preferida", "nota")
    @classmethod
    def limpiar_opcionales(cls, valor: str | None) -> str | None:
        return _limpiar_texto_opcional(valor)

    @model_validator(mode="after")
    def validar_regla(self):
        if self.conservar_original:
            # Si se conserva, la traduccion preferida no aplica
            self.traduccion_preferida = None
        elif not self.traduccion_preferida:
            raise ValueError(
                "Debe indicar una traduccion preferida o marcar el termino para conservarse en su idioma original."
            )
        return self


class ActualizarTerminoGlosarioSolicitud(BaseModel):
    termino_origen: str | None = Field(default=None, min_length=1, max_length=255)
    traduccion_preferida: str | None = Field(default=None, max_length=255)
    conservar_original: bool | None = None
    distinguir_mayusculas: bool | None = None
    nota: str | None = None

    @field_validator("termino_origen")
    @classmethod
    def validar_termino(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        valor_limpio = valor.strip()
        if not valor_limpio:
            raise ValueError("El termino de origen no puede estar vacio.")
        return valor_limpio

    @field_validator("traduccion_preferida", "nota")
    @classmethod
    def limpiar_opcionales(cls, valor: str | None) -> str | None:
        return _limpiar_texto_opcional(valor)


class TerminoGlosarioDetalle(BaseModel):
    model_config = {"from_attributes": True}

    id_termino_glosario: int
    id_glosario: int
    termino_origen: str
    traduccion_preferida: str | None = None
    conservar_original: bool = False
    distinguir_mayusculas: bool = False
    nota: str | None = None

    @computed_field
    @property
    def id(self) -> int:
        return self.id_termino_glosario


class RespuestaTerminoGlosario(BaseModel):
    mensaje: str
    resultado: TerminoGlosarioDetalle


# ---------------------------------------------------------------------------
# Glosarios
# ---------------------------------------------------------------------------


class CrearGlosarioSolicitud(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100, description="Nombre del glosario")
    descripcion: str | None = Field(default=None, description="Descripcion del glosario")
    id_idioma_origen: int = Field(..., description="ID del idioma de origen")
    id_idioma_destino: int = Field(..., description="ID del idioma de destino")
    terminos: list[TerminoGlosarioSolicitud] = Field(
        default_factory=list,
        description="Terminos iniciales del glosario (opcional)",
    )

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, valor: str) -> str:
        valor_limpio = valor.strip()
        if not valor_limpio:
            raise ValueError("El nombre del glosario no puede estar vacio.")
        return valor_limpio

    @field_validator("descripcion")
    @classmethod
    def limpiar_descripcion(cls, valor: str | None) -> str | None:
        return _limpiar_texto_opcional(valor)

    @model_validator(mode="after")
    def validar_idiomas(self):
        if self.id_idioma_origen == self.id_idioma_destino:
            raise ValueError("El idioma de origen y el de destino deben ser distintos.")
        return self


class ActualizarGlosarioSolicitud(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    descripcion: str | None = None
    id_idioma_origen: int | None = None
    id_idioma_destino: int | None = None

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        valor_limpio = valor.strip()
        if not valor_limpio:
            raise ValueError("El nombre del glosario no puede estar vacio.")
        return valor_limpio

    @field_validator("descripcion")
    @classmethod
    def limpiar_descripcion(cls, valor: str | None) -> str | None:
        return _limpiar_texto_opcional(valor)


class GlosarioResumen(BaseModel):
    id_glosario: int
    nombre: str
    descripcion: str | None = None
    id_usuario: int
    id_idioma_origen: int
    id_idioma_destino: int
    codigo_idioma_origen: str | None = None
    codigo_idioma_destino: str | None = None
    nombre_idioma_origen: str | None = None
    nombre_idioma_destino: str | None = None
    cantidad_terminos: int = 0
    fecha_creacion: datetime
    fecha_actualizacion: datetime | None = None

    @computed_field
    @property
    def id(self) -> int:
        return self.id_glosario

    @computed_field
    @property
    def par_idiomas(self) -> str:
        """Texto para mostrar debajo del nombre, por ejemplo 'EN → ES'."""
        origen = (self.codigo_idioma_origen or "?").upper()
        destino = (self.codigo_idioma_destino or "?").upper()
        return f"{origen} → {destino}"


class GlosarioDetalle(GlosarioResumen):
    terminos: list[TerminoGlosarioDetalle] = Field(default_factory=list)


class RespuestaGlosario(BaseModel):
    mensaje: str
    resultado: GlosarioDetalle


class ListaGlosariosRespuesta(BaseModel):
    mensaje: str
    resultado: list[GlosarioResumen]


class RespuestaEliminarGlosario(BaseModel):
    mensaje: str
    resultado: None = None


# ---------------------------------------------------------------------------
# Uso durante la traduccion
# ---------------------------------------------------------------------------


class TerminoAplicado(BaseModel):
    termino_origen: str
    resultado: str
    conservar_original: bool = False

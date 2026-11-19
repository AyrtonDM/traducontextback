from pydantic import BaseModel, Field, computed_field


class GuardarConfiguracionTraduccionSolicitud(BaseModel):
    id_contexto: int = Field(..., description="ID del contexto")
    id_tono: int = Field(..., description="ID del tono")
    id_variante_regional: int | None = Field(default=None, description="ID de la variante regional opcional")
    explicar_expresiones: bool = Field(default=False, description="Indica si debe explicar expresiones")
    generar_alternativas: bool = Field(default=False, description="Indica si debe generar alternativas")
    # Preferencias (HU-33): se guardan como valores predeterminados del usuario
    idioma_destino: str | None = Field(
        default=None,
        max_length=10,
        description=(
            "Codigo del idioma de destino preferido (opcional). Se guarda y se usa para "
            "validar que la variante regional y el glosario sean compatibles"
        ),
    )
    id_glosario: int | None = Field(
        default=None,
        description="Glosario predeterminado (opcional, debe ser del usuario y del idioma de destino)",
    )


class ConfiguracionTraduccionDetalle(BaseModel):
    model_config = {"from_attributes": True}

    id_configuracion_traduccion: int
    id_contexto: int
    id_tono: int | None = None
    id_variante_regional: int | None = None
    id_usuario: int | None = None
    explicar_expresiones: bool = False
    generar_alternativas: bool = False

    id_idioma_destino: int | None = None
    id_glosario: int | None = None

    nombre_contexto: str | None = None
    nombre_tono: str | None = None
    nombre_variante_regional: str | None = None
    codigo_idioma_destino: str | None = None
    nombre_idioma_destino: str | None = None
    nombre_glosario: str | None = None

    @computed_field
    @property
    def id(self) -> int:
        return self.id_configuracion_traduccion


class RespuestaConfiguracionTraduccion(BaseModel):
    mensaje: str
    resultado: ConfiguracionTraduccionDetalle


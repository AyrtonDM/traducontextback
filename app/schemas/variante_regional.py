from pydantic import BaseModel, computed_field


class VarianteRegionalDetalle(BaseModel):
    model_config = {"from_attributes": True}

    id_variante_regional: int
    nombre: str
    codigo: str
    activo: bool = True
    id_idioma: int

    @computed_field
    @property
    def id(self) -> int:
        return self.id_variante_regional


class ListaVariantesRegionalesRespuesta(BaseModel):
    mensaje: str
    resultado: list[VarianteRegionalDetalle]


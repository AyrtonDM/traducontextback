from pydantic import BaseModel, computed_field


class IdiomaDetalle(BaseModel):
    model_config = {"from_attributes": True}

    id_idioma: int
    nombre: str
    codigo: str

    @computed_field
    @property
    def id(self) -> int:
        return self.id_idioma


class ListaIdiomasRespuesta(BaseModel):
    mensaje: str
    resultado: list[IdiomaDetalle]

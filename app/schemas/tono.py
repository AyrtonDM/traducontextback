from pydantic import BaseModel, computed_field


class TonoDetalle(BaseModel):
    model_config = {"from_attributes": True}

    id_tono: int
    nombre: str
    descripcion: str | None = None
    activo: bool = True

    @computed_field
    @property
    def id(self) -> int:
        return self.id_tono


class ListaTonosRespuesta(BaseModel):
    mensaje: str
    resultado: list[TonoDetalle]


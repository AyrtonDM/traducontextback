from pydantic import BaseModel


class EntornoItem(BaseModel):
    id_entorno: int
    nombre: str
    descripcion: str | None = None
    activo: bool

    model_config = {"from_attributes": True}


class ListaEntornosRespuesta(BaseModel):
    mensaje: str
    resultado: list[EntornoItem]

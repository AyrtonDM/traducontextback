from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentoDetalle(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_documento: int
    nombre: str
    tipo_mime: str
    extension: str
    tamano: int
    ruta_archivo: str
    fecha_carga: datetime
    id_usuario: int


class RespuestaSubirDocumento(BaseModel):
    mensaje: str
    resultado: DocumentoDetalle


class SolicitudTraducirDocumento(BaseModel):
    id_documento: int
    idioma_destino: str
    idioma_origen: str | None = None
    id_idioma_destino: int | None = None
    id_idioma_origen: int | None = None


class TraduccionDocumentoDetalle(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_traduccion_documento: int
    id_documento: int
    nombre: str
    extension: str
    estado: str
    fecha: datetime
    ruta_archivo: str
    id_usuario: int
    id_idioma_origen: int
    id_idioma_destino: int
    codigo_idioma_origen: str | None = None
    codigo_idioma_destino: str | None = None
    url_descarga: str | None = None


class RespuestaTraduccionDocumento(BaseModel):
    mensaje: str
    resultado: TraduccionDocumentoDetalle


class ListaDocumentosRespuesta(BaseModel):
    mensaje: str
    resultado: list[DocumentoDetalle]


class ListaTraduccionesDocumentoRespuesta(BaseModel):
    mensaje: str
    resultado: list[TraduccionDocumentoDetalle]

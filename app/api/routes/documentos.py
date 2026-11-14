from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.seguridad import requiere_token
from app.database.conexion import obtener_sesion
from app.models.documento.documento import Documento
from app.models.documento.traduccion_documento import TraduccionDocumento
from app.models.traduccion.idioma import Idioma
from app.models.usuario.usuario import Usuario
from app.schemas.documento import (
    DocumentoDetalle,
    ListaDocumentosRespuesta,
    ListaTraduccionesDocumentoRespuesta,
    RespuestaSubirDocumento,
    RespuestaTraduccionDocumento,
    SolicitudTraducirDocumento,
    TraduccionDocumentoDetalle,
)
from app.services.traduccion_documentos import (
    ejecutar_traduccion_documento,
    guardar_documento_subido,
)

enrutador = APIRouter(
    prefix="/documentos",
    tags=["documentos"],
)


@enrutador.post(
    "/subir",
    response_model=RespuestaSubirDocumento,
    status_code=status.HTTP_201_CREATED,
    summary="Subir documento para traduccion (requiere token)",
    description=(
        "Sube un archivo (.docx o .xlsx) al servidor, lo almacena en la carpeta "
        "'documentos/original' y registra sus metadatos en la tabla 'documento'. "
        "Requiere autenticacion con token Bearer."
    ),
)
def subir_documento(
    archivo: UploadFile = File(..., description="Archivo a subir (.docx o .xlsx)"),
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaSubirDocumento:
    try:
        doc = guardar_documento_subido(
            archivo=archivo,
            id_usuario=usuario.id,
            sesion=sesion,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    return RespuestaSubirDocumento(
        mensaje="Documento subido y registrado correctamente.",
        resultado=DocumentoDetalle.model_validate(doc),
    )


@enrutador.post(
    "/traducir",
    response_model=RespuestaTraduccionDocumento,
    status_code=status.HTTP_200_OK,
    summary="Traducir documento previamente subido (requiere token)",
    description=(
        "Toma un documento existente del usuario, traduce su contenido respetando el formato original "
        "e imagenes, genera el archivo traducido en 'documentos/traducido' y registra "
        "la entrada correspondiente en la tabla 'traduccion_documento'."
    ),
)
def traducir_documento(
    solicitud: SolicitudTraducirDocumento,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaTraduccionDocumento:
    try:
        trad = ejecutar_traduccion_documento(
            id_documento=solicitud.id_documento,
            id_usuario=usuario.id,
            idioma_destino=solicitud.idioma_destino,
            idioma_origen=solicitud.idioma_origen,
            sesion=sesion,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    idioma_orig = sesion.scalar(
        select(Idioma).where(Idioma.id_idioma == trad.id_idioma_origen)
    )
    idioma_dest = sesion.scalar(
        select(Idioma).where(Idioma.id_idioma == trad.id_idioma_destino)
    )

    detalle = TraduccionDocumentoDetalle(
        id_traduccion_documento=trad.id_traduccion_documento,
        id_documento=trad.id_documento,
        nombre=trad.nombre,
        extension=trad.extension,
        estado=trad.estado,
        fecha=trad.fecha,
        ruta_archivo=trad.ruta_archivo,
        id_usuario=trad.id_usuario,
        id_idioma_origen=trad.id_idioma_origen,
        id_idioma_destino=trad.id_idioma_destino,
        codigo_idioma_origen=idioma_orig.codigo if idioma_orig else None,
        codigo_idioma_destino=idioma_dest.codigo if idioma_dest else None,
        url_descarga=f"/api/v1/documentos/descargar/{trad.id_traduccion_documento}",
    )

    return RespuestaTraduccionDocumento(
        mensaje="Documento traducido correctamente.",
        resultado=detalle,
    )


@enrutador.get(
    "/descargar/{id_traduccion_documento}",
    summary="Descargar documento traducido",
    description="Descarga el archivo traducido generado correspondiente al id de traduccion de documento.",
)
def descargar_documento_traducido(
    id_traduccion_documento: int,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
):
    trad = sesion.scalar(
        select(TraduccionDocumento).where(
            TraduccionDocumento.id_traduccion_documento == id_traduccion_documento,
            TraduccionDocumento.id_usuario == usuario.id,
        )
    )
    if not trad:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La traduccion de documento no existe o no pertenece al usuario autenticado.",
        )

    ruta = Path(trad.ruta_archivo)
    if not ruta.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El archivo fisico traducido no se encuentra disponible en el servidor.",
        )

    return FileResponse(
        path=str(ruta),
        filename=trad.nombre,
        media_type="application/octet-stream",
    )


@enrutador.get(
    "",
    response_model=ListaDocumentosRespuesta,
    status_code=status.HTTP_200_OK,
    summary="Listar documentos del usuario autenticado",
)
def listar_documentos_usuario(
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> ListaDocumentosRespuesta:
    documentos = sesion.scalars(
        select(Documento)
        .where(Documento.id_usuario == usuario.id)
        .order_by(Documento.fecha_carga.desc())
    ).all()

    return ListaDocumentosRespuesta(
        mensaje="Documentos obtenidos correctamente.",
        resultado=[DocumentoDetalle.model_validate(d) for d in documentos],
    )


@enrutador.get(
    "/{id_documento}/traducciones",
    response_model=ListaTraduccionesDocumentoRespuesta,
    status_code=status.HTTP_200_OK,
    summary="Listar traducciones de un documento",
)
def listar_traducciones_de_documento(
    id_documento: int,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> ListaTraduccionesDocumentoRespuesta:
    documento = sesion.scalar(
        select(Documento).where(
            Documento.id_documento == id_documento,
            Documento.id_usuario == usuario.id,
        )
    )
    if not documento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento no encontrado.",
        )

    traducciones = sesion.scalars(
        select(TraduccionDocumento)
        .where(TraduccionDocumento.id_documento == id_documento)
        .order_by(TraduccionDocumento.fecha.desc())
    ).all()

    resultados = []
    for t in traducciones:
        idioma_orig = sesion.scalar(select(Idioma).where(Idioma.id_idioma == t.id_idioma_origen))
        idioma_dest = sesion.scalar(select(Idioma).where(Idioma.id_idioma == t.id_idioma_destino))
        resultados.append(
            TraduccionDocumentoDetalle(
                id_traduccion_documento=t.id_traduccion_documento,
                id_documento=t.id_documento,
                nombre=t.nombre,
                extension=t.extension,
                estado=t.estado,
                fecha=t.fecha,
                ruta_archivo=t.ruta_archivo,
                id_usuario=t.id_usuario,
                id_idioma_origen=t.id_idioma_origen,
                id_idioma_destino=t.id_idioma_destino,
                codigo_idioma_origen=idioma_orig.codigo if idioma_orig else None,
                codigo_idioma_destino=idioma_dest.codigo if idioma_dest else None,
                url_descarga=f"/api/v1/documentos/descargar/{t.id_traduccion_documento}",
            )
        )

    return ListaTraduccionesDocumentoRespuesta(
        mensaje="Traducciones de documento obtenidas correctamente.",
        resultado=resultados,
    )

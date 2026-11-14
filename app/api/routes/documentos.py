from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.configuracion import RUTA_BASE
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
    RespuestaEliminarDocumento,
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
        "Sube un archivo (.docx, .xlsx o .pdf) al servidor, lo almacena en la carpeta "
        "'documentos/original' y registra sus metadatos en la tabla 'documento'. "
        "Requiere autenticacion con token Bearer."
    ),
)
def subir_documento(
    archivo: UploadFile = File(..., description="Archivo a subir (.docx, .xlsx o .pdf)"),
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

    idioma_orig = (
        sesion.scalar(select(Idioma).where(Idioma.id_idioma == doc.id_idioma_origen))
        if doc.id_idioma_origen
        else None
    )

    detalle = DocumentoDetalle(
        id_documento=doc.id_documento,
        nombre=doc.nombre,
        tipo_mime=doc.tipo_mime,
        extension=doc.extension,
        tamano=doc.tamano,
        ruta_archivo=doc.ruta_archivo,
        fecha_carga=doc.fecha_carga,
        id_usuario=doc.id_usuario,
        id_idioma_origen=doc.id_idioma_origen,
        codigo_idioma_origen=idioma_orig.codigo if idioma_orig else None,
        nombre_idioma_origen=idioma_orig.nombre if idioma_orig else None,
        id_configuracion_traduccion=doc.id_configuracion_traduccion,
    )

    return RespuestaSubirDocumento(
        mensaje="Documento subido y registrado correctamente.",
        resultado=detalle,
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
        url_descarga=trad.ruta_archivo,
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

    ruta_relativa = trad.ruta_archivo.lstrip("/\\")
    ruta = RUTA_BASE / ruta_relativa
    if not ruta.exists():
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

    resultados = []
    for d in documentos:
        idioma_orig = (
            sesion.scalar(select(Idioma).where(Idioma.id_idioma == d.id_idioma_origen))
            if d.id_idioma_origen
            else None
        )
        resultados.append(
            DocumentoDetalle(
                id_documento=d.id_documento,
                nombre=d.nombre,
                tipo_mime=d.tipo_mime,
                extension=d.extension,
                tamano=d.tamano,
                ruta_archivo=d.ruta_archivo,
                fecha_carga=d.fecha_carga,
                id_usuario=d.id_usuario,
                id_idioma_origen=d.id_idioma_origen,
                codigo_idioma_origen=idioma_orig.codigo if idioma_orig else None,
                nombre_idioma_origen=idioma_orig.nombre if idioma_orig else None,
                id_configuracion_traduccion=d.id_configuracion_traduccion,
            )
        )

    return ListaDocumentosRespuesta(
        mensaje="Documentos obtenidos correctamente.",
        resultado=resultados,
    )


@enrutador.get(
    "/traducidos",
    response_model=ListaTraduccionesDocumentoRespuesta,
    status_code=status.HTTP_200_OK,
    summary="Listar todos los documentos traducidos del usuario (del más reciente al más antiguo)",
    description=(
        "Retorna la lista de todos los documentos traducidos del usuario autenticado, "
        "ordenados de forma descendente por fecha (desde el más reciente hasta el más antiguo)."
    ),
)
@enrutador.get(
    "/traducciones",
    response_model=ListaTraduccionesDocumentoRespuesta,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def listar_documentos_traducidos_usuario(
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> ListaTraduccionesDocumentoRespuesta:
    traducciones = sesion.scalars(
        select(TraduccionDocumento)
        .where(TraduccionDocumento.id_usuario == usuario.id)
        .order_by(TraduccionDocumento.fecha.desc())
    ).all()

    resultados = []
    for t in traducciones:
        doc_orig = (
            sesion.scalar(select(Documento).where(Documento.id_documento == t.id_documento))
            if t.id_documento
            else None
        )
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
                nombre_idioma_origen=idioma_orig.nombre if idioma_orig else None,
                nombre_idioma_destino=idioma_dest.nombre if idioma_dest else None,
                nombre_documento_original=doc_orig.nombre if doc_orig else None,
                url_descarga=t.ruta_archivo,
            )
        )

    return ListaTraduccionesDocumentoRespuesta(
        mensaje="Documentos traducidos obtenidos correctamente.",
        resultado=resultados,
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
                nombre_idioma_origen=idioma_orig.nombre if idioma_orig else None,
                nombre_idioma_destino=idioma_dest.nombre if idioma_dest else None,
                nombre_documento_original=documento.nombre,
                url_descarga=t.ruta_archivo,
            )
        )

    return ListaTraduccionesDocumentoRespuesta(
        mensaje="Traducciones de documento obtenidas correctamente.",
        resultado=resultados,
    )


def _eliminar_archivo_fisico(ruta_archivo: str) -> None:
    """Elimina de forma segura un archivo físico en disco a partir de su ruta web o absoluta."""
    try:
        ruta_relativa = ruta_archivo.lstrip("/\\")
        ruta_fisica = RUTA_BASE / ruta_relativa
        if not ruta_fisica.exists():
            ruta_fisica = Path(ruta_archivo)
        if ruta_fisica.exists() and ruta_fisica.is_file():
            ruta_fisica.unlink()
    except Exception:
        pass


@enrutador.delete(
    "/{id_documento}",
    response_model=RespuestaEliminarDocumento,
    status_code=status.HTTP_200_OK,
    summary="Eliminar documento original (conservando sus traducciones)",
    description=(
        "Elimina el documento original de la base de datos y su archivo físico de 'documentos/original'. "
        "Las traducciones que se hayan derivado de este documento se conservan intactas tanto en la "
        "base de datos (con id_documento = null) como sus archivos físicos en 'documentos/traducido'."
    ),
)
def eliminar_documento_original(
    id_documento: int,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaEliminarDocumento:
    documento = sesion.scalar(
        select(Documento).where(
            Documento.id_documento == id_documento,
            Documento.id_usuario == usuario.id,
        )
    )
    if not documento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento no encontrado o no pertenece al usuario autenticado.",
        )

    # 1. Eliminar archivo físico del documento original únicamente
    if documento.ruta_archivo:
        _eliminar_archivo_fisico(documento.ruta_archivo)

    # 2. Eliminar registro en base de datos (las traducciones se conservan con id_documento = NULL)
    sesion.delete(documento)
    sesion.commit()

    return RespuestaEliminarDocumento(
        mensaje="Documento original y su archivo físico eliminados correctamente. Las traducciones asociadas se conservaron.",
        resultado=None,
    )


@enrutador.delete(
    "/traducidos/{id_traduccion_documento}",
    response_model=RespuestaEliminarDocumento,
    status_code=status.HTTP_200_OK,
    summary="Eliminar documento traducido",
    description=(
        "Elimina un documento traducido específico de la base de datos y su archivo físico "
        "de la carpeta 'documentos/traducido', manteniendo intacto el documento original."
    ),
)
@enrutador.delete(
    "/traducciones/{id_traduccion_documento}",
    response_model=RespuestaEliminarDocumento,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def eliminar_documento_traducido(
    id_traduccion_documento: int,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaEliminarDocumento:
    trad = sesion.scalar(
        select(TraduccionDocumento).where(
            TraduccionDocumento.id_traduccion_documento == id_traduccion_documento,
            TraduccionDocumento.id_usuario == usuario.id,
        )
    )
    if not trad:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Traducción de documento no encontrada o no pertenece al usuario autenticado.",
        )

    # 1. Eliminar archivo físico del traducido
    if trad.ruta_archivo:
        _eliminar_archivo_fisico(trad.ruta_archivo)

    # 2. Eliminar registro en base de datos
    sesion.delete(trad)
    sesion.commit()

    return RespuestaEliminarDocumento(
        mensaje="Documento traducido y su archivo físico eliminados correctamente.",
        resultado=None,
    )

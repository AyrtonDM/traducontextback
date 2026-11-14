import os
import shutil
import uuid
from pathlib import Path
from typing import BinaryIO

import docx
import openpyxl
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.configuracion import RUTA_BASE
from app.models.documento.documento import Documento
from app.models.documento.traduccion_documento import TraduccionDocumento
from app.models.traduccion.idioma import Idioma
from app.services.detector_idioma import DetectorIdioma
from app.services.traduccion import detector_idioma, motor_nllb

CARPETA_ORIGINAL = RUTA_BASE / "documentos" / "original"
CARPETA_TRADUCIDO = RUTA_BASE / "documentos" / "traducido"

CARPETA_ORIGINAL.mkdir(parents=True, exist_ok=True)
CARPETA_TRADUCIDO.mkdir(parents=True, exist_ok=True)

EXTENSIONES_PERMITIDAS = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def guardar_documento_subido(
    archivo: UploadFile,
    id_usuario: int,
    sesion: Session,
) -> Documento:
    nombre_original = archivo.filename or "documento_sin_nombre"
    extension = nombre_original.split(".")[-1].lower() if "." in nombre_original else ""

    if extension not in EXTENSIONES_PERMITIDAS:
        raise ValueError(
            f"Extension de archivo no soportada: .{extension}. Solo se permiten: {', '.join(EXTENSIONES_PERMITIDAS.keys())}"
        )

    # Generar nombre unico en disco para evitar colisiones
    nombre_guardado = f"{uuid.uuid4().hex}_{nombre_original}"
    ruta_guardado = CARPETA_ORIGINAL / nombre_guardado

    archivo.file.seek(0)
    with open(ruta_guardado, "wb") as f_out:
        shutil.copyfileobj(archivo.file, f_out)

    tamano = ruta_guardado.stat().st_size
    tipo_mime = archivo.content_type or EXTENSIONES_PERMITIDAS.get(extension, "application/octet-stream")

    documento = Documento(
        nombre=nombre_original,
        tipo_mime=tipo_mime,
        extension=extension,
        tamano=tamano,
        ruta_archivo=str(ruta_guardado),
        id_usuario=id_usuario,
    )
    sesion.add(documento)
    sesion.commit()
    sesion.refresh(documento)

    return documento


def _extraer_muestra_texto(ruta_archivo: Path, extension: str) -> str:
    """Extrae las primeras lineas de texto de un documento para deteccion automatica de idioma."""
    try:
        if extension == "docx":
            doc = docx.Document(ruta_archivo)
            textos = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            return " ".join(textos[:5])
        elif extension == "xlsx":
            wb = openpyxl.load_workbook(ruta_archivo, data_only=True)
            textos = []
            for sheet in wb.sheetnames:
                ws = wb[sheet]
                for row in ws.iter_rows(values_only=True):
                    for val in row:
                        if isinstance(val, str) and val.strip() and not val.startswith("="):
                            textos.append(val.strip())
                            if len(textos) >= 5:
                                break
                    if len(textos) >= 5:
                        break
            return " ".join(textos)
    except Exception:
        pass
    return ""


def traducir_archivo_docx(
    ruta_entrada: Path,
    ruta_salida: Path,
    idioma_origen: str,
    idioma_destino: str,
) -> None:
    doc = docx.Document(ruta_entrada)

    # Traducir párrafos
    for p in doc.paragraphs:
        for run in p.runs:
            texto = run.text
            if texto and texto.strip():
                run.text = motor_nllb.traducir(texto, idioma_origen, idioma_destino)

    # Traducir celdas de tablas
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    for run in p.runs:
                        texto = run.text
                        if texto and texto.strip():
                            run.text = motor_nllb.traducir(texto, idioma_origen, idioma_destino)

    doc.save(ruta_salida)


def traducir_archivo_xlsx(
    ruta_entrada: Path,
    ruta_salida: Path,
    idioma_origen: str,
    idioma_destino: str,
) -> None:
    wb = openpyxl.load_workbook(ruta_entrada)

    for sheetname in wb.sheetnames:
        ws = wb[sheetname]
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str):
                    val = cell.value
                    if val.strip() and not val.startswith("="):
                        cell.value = motor_nllb.traducir(val, idioma_origen, idioma_destino)

    wb.save(ruta_salida)


def ejecutar_traduccion_documento(
    id_documento: int,
    id_usuario: int,
    idioma_destino: str,
    idioma_origen: str | None,
    sesion: Session,
) -> TraduccionDocumento:
    documento = sesion.scalar(
        select(Documento).where(
            Documento.id_documento == id_documento,
            Documento.id_usuario == id_usuario,
        )
    )
    if not documento:
        raise ValueError("El documento solicitado no existe o no pertenece al usuario autenticado.")

    ruta_origen = Path(documento.ruta_archivo)
    if not ruta_origen.exists():
        raise ValueError("El archivo fisico original del documento no fue encontrado en el servidor.")

    # Resolver idioma destino
    idioma_dest_db = sesion.scalar(
        select(Idioma).where(
            (Idioma.codigo == idioma_destino.strip().lower())
            | (Idioma.nombre.ilike(idioma_destino.strip()))
        )
    )
    if not idioma_dest_db:
        raise ValueError(f"El idioma de destino '{idioma_destino}' no esta registrado en el sistema.")

    # Resolver idioma origen
    if not idioma_origen or not idioma_origen.strip():
        muestra = _extraer_muestra_texto(ruta_origen, documento.extension)
        if muestra:
            resultado_det = detector_idioma.detectar(muestra)
            codigo_origen = resultado_det["codigo"]
        else:
            codigo_origen = "es"
    else:
        codigo_origen = idioma_origen.strip().lower()

    idioma_orig_db = sesion.scalar(
        select(Idioma).where(
            (Idioma.codigo == codigo_origen)
            | (Idioma.nombre.ilike(codigo_origen))
        )
    )
    if not idioma_orig_db:
        # Si no esta registrado en la tabla, buscamos 'es' o el primero
        idioma_orig_db = sesion.scalar(select(Idioma).where(Idioma.codigo == "es"))
        if not idioma_orig_db:
            idioma_orig_db = sesion.scalar(select(Idioma))

    # Definir nombre y ruta del archivo traducido
    nombre_traducido = f"traducido_{documento.nombre}"
    nombre_guardado_trad = f"{uuid.uuid4().hex}_{nombre_traducido}"
    ruta_salida = CARPETA_TRADUCIDO / nombre_guardado_trad

    # Ejecutar la traduccion segun la extension
    extension = documento.extension.lower()
    if extension == "docx":
        traducir_archivo_docx(
            ruta_entrada=ruta_origen,
            ruta_salida=ruta_salida,
            idioma_origen=idioma_orig_db.codigo,
            idioma_destino=idioma_dest_db.codigo,
        )
    elif extension == "xlsx":
        traducir_archivo_xlsx(
            ruta_entrada=ruta_origen,
            ruta_salida=ruta_salida,
            idioma_origen=idioma_orig_db.codigo,
            idioma_destino=idioma_dest_db.codigo,
        )
    else:
        raise ValueError(f"Formato de archivo .{extension} no soportado para traduccion. Solo se permiten .docx y .xlsx.")

    # Registrar en base de datos
    registro_traduccion = TraduccionDocumento(
        nombre=nombre_traducido,
        extension=documento.extension,
        estado="COMPLETADO",
        ruta_archivo=str(ruta_salida),
        id_documento=documento.id_documento,
        id_usuario=id_usuario,
        id_idioma_origen=idioma_orig_db.id_idioma,
        id_idioma_destino=idioma_dest_db.id_idioma,
    )
    sesion.add(registro_traduccion)
    sesion.commit()
    sesion.refresh(registro_traduccion)

    return registro_traduccion

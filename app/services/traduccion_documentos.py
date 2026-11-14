import os
import shutil
import uuid
from pathlib import Path
from typing import BinaryIO

import docx
import openpyxl
import pymupdf
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.configuracion import RUTA_BASE
from app.models.documento.documento import Documento
from app.models.documento.traduccion_documento import TraduccionDocumento
from app.models.traduccion.configuracion_traduccion import ConfiguracionTraduccion
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
    "pdf": "application/pdf",
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

    # 1. Detectar el idioma en el contenido del documento
    muestra = _extraer_muestra_texto(ruta_guardado, extension)
    id_idioma_origen = None
    if muestra:
        resultado_det = detector_idioma.detectar(muestra)
        codigo_detectado = resultado_det.get("codigo")
        if codigo_detectado:
            idioma_db = sesion.scalar(
                select(Idioma).where(
                    (Idioma.codigo == codigo_detectado.lower())
                    | (Idioma.nombre.ilike(codigo_detectado))
                )
            )
            if idioma_db:
                id_idioma_origen = idioma_db.id_idioma

    # 2. Obtener la configuracion de traduccion del usuario
    config_db = sesion.scalar(
        select(ConfiguracionTraduccion).where(
            ConfiguracionTraduccion.id_usuario == id_usuario
        )
    )
    id_config = config_db.id_configuracion_traduccion if config_db else None

    # Ruta web publica para que el frontend acceda directamente con urlback + ruta_archivo
    ruta_web_original = f"/documentos/original/{nombre_guardado}"

    documento = Documento(
        nombre=nombre_original,
        tipo_mime=tipo_mime,
        extension=extension,
        tamano=tamano,
        ruta_archivo=ruta_web_original,
        id_usuario=id_usuario,
        id_idioma_origen=id_idioma_origen,
        id_configuracion_traduccion=id_config,
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
        elif extension == "pdf":
            doc = pymupdf.open(ruta_archivo)
            textos = []
            for pagina in doc:
                txt = pagina.get_text().strip()
                if txt:
                    textos.append(txt)
                if len(textos) >= 3:
                    break
            doc.close()
            return " ".join(" ".join(textos[:3]).replace("\n", " ").split())
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


def insertar_texto_ajustado(
    page: pymupdf.Page,
    rect: pymupdf.Rect,
    texto: str,
    fontsize_inicial: float = 11.0,
    min_fontsize: float = 5.5,
    color: tuple[float, float, float] = (0, 0, 0),
) -> bool:
    """Inserta texto en un rectangulo de pagina de PDF reduciendo el tamano de fuente si es necesario para evitar desbordes."""
    r = pymupdf.Rect(rect)
    fs = max(fontsize_inicial, min_fontsize)
    while fs >= min_fontsize:
        rc = page.insert_textbox(r, texto, fontsize=fs, color=color)
        if rc >= 0:
            return True
        fs -= 0.5

    # Si aun no cupo con el tamano minimo, expandir ligeramente hacia abajo
    r_expandido = pymupdf.Rect(r.x0, r.y0, r.x1, r.y1 + max(r.height * 0.35, 10.0))
    fs = max(fontsize_inicial * 0.8, min_fontsize)
    while fs >= min_fontsize:
        rc = page.insert_textbox(r_expandido, texto, fontsize=fs, color=color)
        if rc >= 0:
            return True
        fs -= 0.5

    # Ultimo intento
    page.insert_textbox(r_expandido, texto, fontsize=min_fontsize, color=color)
    return False


def traducir_archivo_pdf(
    ruta_entrada: Path,
    ruta_salida: Path,
    idioma_origen: str,
    idioma_destino: str,
) -> None:
    """Traduce un archivo PDF reemplazando los bloques de texto en sus coordenadas y respetando el diseno/imagenes."""
    doc = pymupdf.open(ruta_entrada)

    for pagina in doc:
        bloques_data = pagina.get_text("dict").get("blocks", [])
        bloques_a_procesar = []

        for b in bloques_data:
            if b.get("type") == 0:  # Bloque de texto
                lineas = b.get("lines", [])
                textos_span = []
                for l in lineas:
                    for s in l.get("spans", []):
                        t = s.get("text", "")
                        if t:
                            textos_span.append(t)
                texto_bloque = " ".join("".join(textos_span).split())
                if texto_bloque:
                    primera_linea = lineas[0] if lineas else {}
                    primer_span = primera_linea.get("spans", [{}])[0] if primera_linea.get("spans") else {}
                    font_size = float(primer_span.get("size", 11.0))
                    color_int = int(primer_span.get("color", 0))
                    r = ((color_int >> 16) & 255) / 255.0
                    g = ((color_int >> 8) & 255) / 255.0
                    b_col = (color_int & 255) / 255.0

                    bloques_a_procesar.append({
                        "rect": pymupdf.Rect(b.get("bbox")),
                        "texto_original": texto_bloque,
                        "font_size": font_size,
                        "color": (r, g, b_col),
                    })

        if not bloques_a_procesar:
            continue

        # 1. Traducir textos y marcar redacciones sobre el texto original
        for item in bloques_a_procesar:
            item["texto_traducido"] = motor_nllb.traducir(
                item["texto_original"],
                idioma_origen,
                idioma_destino,
            )
            pagina.add_redact_annot(item["rect"])

        # 2. Aplicar redacciones sin tocar imagenes de fondo o graficos
        pagina.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE)

        # 3. Insertar textos traducidos en sus coordenadas ajustadas
        for item in bloques_a_procesar:
            insertar_texto_ajustado(
                page=pagina,
                rect=item["rect"],
                texto=item["texto_traducido"],
                fontsize_inicial=item["font_size"],
                color=item["color"],
            )

    doc.save(ruta_salida, garbage=4, deflate=True)
    doc.close()


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

    # Resolver ruta fisica en disco a partir de la ruta web relativa
    ruta_relativa = documento.ruta_archivo.lstrip("/\\")
    ruta_origen = RUTA_BASE / ruta_relativa
    if not ruta_origen.exists():
        # Respaldo por si existiera algun registro con ruta absoluta
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
        if documento.id_idioma_origen:
            idioma_orig_db = sesion.scalar(
                select(Idioma).where(Idioma.id_idioma == documento.id_idioma_origen)
            )
        else:
            muestra = _extraer_muestra_texto(ruta_origen, documento.extension)
            codigo_origen = detector_idioma.detectar(muestra)["codigo"] if muestra else "es"
            idioma_orig_db = sesion.scalar(
                select(Idioma).where(
                    (Idioma.codigo == codigo_origen)
                    | (Idioma.nombre.ilike(codigo_origen))
                )
            )
    else:
        codigo_origen = idioma_origen.strip().lower()
        idioma_orig_db = sesion.scalar(
            select(Idioma).where(
                (Idioma.codigo == codigo_origen)
                | (Idioma.nombre.ilike(codigo_origen))
            )
        )

    if not idioma_orig_db:
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
    elif extension == "pdf":
        traducir_archivo_pdf(
            ruta_entrada=ruta_origen,
            ruta_salida=ruta_salida,
            idioma_origen=idioma_orig_db.codigo,
            idioma_destino=idioma_dest_db.codigo,
        )
    else:
        raise ValueError(f"Formato de archivo .{extension} no soportado para traduccion. Solo se permiten .docx, .xlsx y .pdf.")

    # Ruta web publica para que el frontend acceda directamente con urlback + ruta_archivo
    ruta_web_traducido = f"/documentos/traducido/{nombre_guardado_trad}"

    # Registrar en base de datos
    registro_traduccion = TraduccionDocumento(
        nombre=nombre_traducido,
        extension=documento.extension,
        estado="COMPLETADO",
        ruta_archivo=ruta_web_traducido,
        id_documento=documento.id_documento,
        id_usuario=id_usuario,
        id_idioma_origen=idioma_orig_db.id_idioma,
        id_idioma_destino=idioma_dest_db.id_idioma,
    )
    sesion.add(registro_traduccion)
    sesion.commit()
    sesion.refresh(registro_traduccion)

    return registro_traduccion

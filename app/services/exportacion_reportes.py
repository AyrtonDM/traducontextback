"""
Exportacion de reportes administrativos a Excel y PDF (HU-48).

Se exporta el mismo reporte de la HU-47 (mismos filtros, filas y totales), sin paginar, junto
con los filtros aplicados y la fecha de generacion. Excel usa openpyxl y PDF usa PyMuPDF (Story,
HTML a PDF con paginacion automatica), dependencias que el proyecto ya tenia.
"""

from dataclasses import dataclass
from html import escape
from io import BytesIO
from typing import Literal

import pymupdf
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.schemas.reporte import ReporteActividad


FormatoExportacion = Literal["pdf", "xlsx"]

MAXIMO_FILAS_EXPORTACION = 10_000
NOMBRE_TIPO_REPORTE = "reporte_actividad"
TITULO_REPORTE = "Reporte de actividad - TraduContext"

ETIQUETAS_TIPO = {
    "texto": "Texto",
    "documento": "Documento",
    "conversacion": "Conversación",
    "sesion_externa": "Sesión externa",
}
TIPOS_MIME = {
    "pdf": "application/pdf",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
COLUMNAS_DETALLE = ("Fecha", "Servicio", "Usuario", "Correo", "Idioma origen", "Idioma destino", "Contexto", "Estado", "Detalle")
COLOR_PRIMARIO = "42149A"


class ErrorExportacionError(RuntimeError):
    """Fallo inesperado al construir el archivo."""


@dataclass
class ArchivoExportado:
    contenido: bytes
    nombre: str
    tipo_mime: str


# ---------------------------------------------------------------------------
# Datos comunes a ambos formatos
# ---------------------------------------------------------------------------


def _filtros_legibles(reporte: ReporteActividad) -> list[tuple[str, str]]:
    f = reporte.filtros
    return [
        ("Período", f"{f.fecha_desde:%d/%m/%Y} - {f.fecha_hasta:%d/%m/%Y}"),
        ("Tipo de servicio", ETIQUETAS_TIPO[f.tipo_servicio] if f.tipo_servicio else "Todos"),
        ("Idioma de origen", f.nombre_idioma_origen or "Todos"),
        ("Idioma de destino", f.nombre_idioma_destino or "Todos"),
        ("Contexto", f.nombre_contexto or "Todos"),
        ("Zona horaria", f.zona_horaria),
    ]


def _totales_legibles(reporte: ReporteActividad) -> list[tuple[str, int]]:
    t = reporte.totales
    return [
        ("Texto", t.texto),
        ("Documento", t.documento),
        ("Conversación", t.conversacion),
        ("Sesión externa", t.sesion_externa),
        ("Total", t.total),
    ]


def _filas_detalle(reporte: ReporteActividad) -> list[list]:
    return [
        [
            a.fecha_local.replace(tzinfo=None),
            ETIQUETAS_TIPO[a.tipo_servicio],
            a.nombre_usuario,
            a.correo_usuario,
            a.idioma_origen or "",
            a.idioma_destino or "",
            a.contexto or "",
            a.estado or "",
            a.detalle or "",
        ]
        for a in reporte.actividades
    ]


def nombre_archivo(reporte: ReporteActividad, formato: FormatoExportacion) -> str:
    """Incluye el tipo de reporte y la fecha de generacion: reporte_actividad_2026-11-19_1530.xlsx"""
    return f"{NOMBRE_TIPO_REPORTE}_{reporte.fecha_generacion_local:%Y-%m-%d_%H%M}.{formato}"


# ---------------------------------------------------------------------------
# Excel
# ---------------------------------------------------------------------------


def _generar_xlsx(reporte: ReporteActividad) -> bytes:
    libro = Workbook()
    hoja = libro.active
    hoja.title = "Reporte"

    negrita = Font(bold=True)
    titulo = Font(bold=True, size=14, color=COLOR_PRIMARIO)
    encabezado = Font(bold=True, color="FFFFFF")
    relleno = PatternFill("solid", fgColor=COLOR_PRIMARIO)
    relleno_suave = PatternFill("solid", fgColor="EEE9F7")
    borde = Border(bottom=Side(style="thin", color="D9D2EC"))

    hoja.append([TITULO_REPORTE])
    hoja["A1"].font = titulo
    hoja.append(["Generado el", reporte.fecha_generacion_local.replace(tzinfo=None)])
    hoja["B2"].number_format = "dd/mm/yyyy hh:mm"
    hoja.append([])

    hoja.append(["Filtros aplicados"])
    hoja.cell(row=hoja.max_row, column=1).font = negrita
    for etiqueta, valor in _filtros_legibles(reporte):
        hoja.append([etiqueta, valor])
    hoja.append([])

    hoja.append(["Totales"])
    hoja.cell(row=hoja.max_row, column=1).font = negrita
    for etiqueta, valor in _totales_legibles(reporte):
        hoja.append([etiqueta, valor])
        if etiqueta == "Total":
            for celda in hoja[hoja.max_row]:
                celda.font = negrita
    hoja.append([])

    hoja.append(["Detalle de actividades"])
    hoja.cell(row=hoja.max_row, column=1).font = negrita
    fila_encabezado = hoja.max_row + 1
    hoja.append(list(COLUMNAS_DETALLE))
    for celda in hoja[fila_encabezado]:
        celda.font = encabezado
        celda.fill = relleno
        celda.alignment = Alignment(vertical="center")

    filas = _filas_detalle(reporte)
    if filas:
        for indice, fila in enumerate(filas):
            hoja.append(fila)
            actual = hoja.max_row
            hoja.cell(row=actual, column=1).number_format = "dd/mm/yyyy hh:mm"
            if indice % 2:
                for celda in hoja[actual]:
                    celda.fill = relleno_suave
            for celda in hoja[actual]:
                celda.border = borde
        ultima = hoja.max_row
        hoja.auto_filter.ref = f"A{fila_encabezado}:{get_column_letter(len(COLUMNAS_DETALLE))}{ultima}"
    else:
        hoja.append(["No se encontraron actividades con los filtros seleccionados."])

    hoja.freeze_panes = f"A{fila_encabezado + 1}"
    anchos = (18, 16, 26, 32, 16, 16, 20, 14, 30)
    for indice, ancho in enumerate(anchos, start=1):
        hoja.column_dimensions[get_column_letter(indice)].width = ancho

    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------


# El resumen (titulo, filtros y totales) se maqueta con HTML (Story). La tabla de detalle se
# dibuja directamente: Story no reparte bien las tablas largas entre paginas (superpone el
# encabezado sobre una fila) y asi ademas se repite el encabezado en cada pagina.

PAGINA_PDF = pymupdf.paper_rect("a4-l")
MARGEN_PDF = 36
ALTO_PIE_PDF = 30
ALTO_FILA_PDF = 16
TAMANO_LETRA_PDF = 7.5
FUENTE_PDF = "helv"
FUENTE_NEGRITA_PDF = "hebo"
# Suma = ancho util de A4 horizontal (842 - 2 * 36)
ANCHOS_COLUMNAS_PDF = (72, 66, 112, 132, 70, 70, 82, 74, 92)

COLOR_PRIMARIO_PDF = (0x42 / 255, 0x14 / 255, 0x9A / 255)
COLOR_TEXTO_PDF = (0.12, 0.16, 0.22)
COLOR_SECUNDARIO_PDF = (0.42, 0.45, 0.5)
COLOR_LINEA_PDF = (0.85, 0.82, 0.93)
COLOR_ZEBRA_PDF = (0.97, 0.96, 0.99)

CSS_PDF = f"""
* {{ font-family: sans-serif; }}
body {{ font-size: 9px; color: #1F2937; }}
h1 {{ font-size: 16px; color: #{COLOR_PRIMARIO}; margin: 0 0 2px 0; }}
h2 {{ font-size: 11px; color: #{COLOR_PRIMARIO}; margin: 12px 0 4px 0; }}
p.generado {{ font-size: 9px; color: #6B7280; margin: 0 0 6px 0; }}
table {{ border-collapse: collapse; width: 360px; }}
td {{ padding: 3px 4px; border-bottom: 1px solid #D9D2EC; }}
td.etiqueta {{ font-weight: bold; width: 130px; }}
tr.total td {{ font-weight: bold; }}
p.vacio {{ color: #6B7280; }}
"""


def _tabla_clave_valor(pares: list[tuple[str, object]], clase_ultima: str = "") -> str:
    filas = []
    for indice, (etiqueta, valor) in enumerate(pares):
        clase = f' class="{clase_ultima}"' if clase_ultima and indice == len(pares) - 1 else ""
        filas.append(f'<tr{clase}><td class="etiqueta">{escape(etiqueta)}</td><td>{escape(str(valor))}</td></tr>')
    return f"<table>{''.join(filas)}</table>"


def _html_resumen(reporte: ReporteActividad) -> str:
    partes = [
        f"<h1>{escape(TITULO_REPORTE)}</h1>",
        f'<p class="generado">Generado el {reporte.fecha_generacion_local:%d/%m/%Y %H:%M}</p>',
        "<h2>Filtros aplicados</h2>",
        _tabla_clave_valor(_filtros_legibles(reporte)),
        "<h2>Totales</h2>",
        _tabla_clave_valor(_totales_legibles(reporte), clase_ultima="total"),
        "<h2>Detalle de actividades</h2>",
    ]
    if not reporte.actividades:
        partes.append('<p class="vacio">No se encontraron actividades con los filtros seleccionados.</p>')
    return f"<body>{''.join(partes)}</body>"


def _recortar(texto: str, ancho: float, fuente: str) -> str:
    """Recorta el texto para que entre en la celda."""
    if pymupdf.get_text_length(texto, fontname=fuente, fontsize=TAMANO_LETRA_PDF) <= ancho:
        return texto
    while texto and pymupdf.get_text_length(texto + "...", fontname=fuente, fontsize=TAMANO_LETRA_PDF) > ancho:
        texto = texto[:-1]
    return texto + "..."


def _dibujar_fila(hoja: pymupdf.Page, y: float, valores: list[str], encabezado: bool, zebra: bool) -> None:
    ancho_total = sum(ANCHOS_COLUMNAS_PDF)
    rect = pymupdf.Rect(MARGEN_PDF, y, MARGEN_PDF + ancho_total, y + ALTO_FILA_PDF)
    if encabezado:
        hoja.draw_rect(rect, color=None, fill=COLOR_PRIMARIO_PDF)
    elif zebra:
        hoja.draw_rect(rect, color=None, fill=COLOR_ZEBRA_PDF)
    if not encabezado:
        hoja.draw_line(rect.bl, rect.br, color=COLOR_LINEA_PDF, width=0.6)

    fuente = FUENTE_NEGRITA_PDF if encabezado else FUENTE_PDF
    color = (1, 1, 1) if encabezado else COLOR_TEXTO_PDF
    x = MARGEN_PDF
    for valor, ancho in zip(valores, ANCHOS_COLUMNAS_PDF):
        texto = _recortar(valor, ancho - 6, fuente)
        hoja.insert_text((x + 3, y + ALTO_FILA_PDF - 5), texto, fontname=fuente, fontsize=TAMANO_LETRA_PDF, color=color)
        x += ancho


def _dibujar_detalle(documento: pymupdf.Document, reporte: ReporteActividad, y_inicial: float) -> None:
    filas = [
        [f"{fila[0]:%d/%m/%Y %H:%M}", *(str(valor) for valor in fila[1:])]
        for fila in _filas_detalle(reporte)
    ]
    if not filas:
        return

    limite = PAGINA_PDF.height - MARGEN_PDF - ALTO_PIE_PDF
    hoja = documento[-1]
    y = y_inicial
    if y + 2 * ALTO_FILA_PDF > limite:
        hoja = documento.new_page(width=PAGINA_PDF.width, height=PAGINA_PDF.height)
        y = MARGEN_PDF
    _dibujar_fila(hoja, y, list(COLUMNAS_DETALLE), encabezado=True, zebra=False)
    y += ALTO_FILA_PDF

    for indice, fila in enumerate(filas):
        if y + ALTO_FILA_PDF > limite:
            hoja = documento.new_page(width=PAGINA_PDF.width, height=PAGINA_PDF.height)
            y = MARGEN_PDF
            _dibujar_fila(hoja, y, list(COLUMNAS_DETALLE), encabezado=True, zebra=False)
            y += ALTO_FILA_PDF
        _dibujar_fila(hoja, y, fila, encabezado=False, zebra=bool(indice % 2))
        y += ALTO_FILA_PDF


def _generar_pdf(reporte: ReporteActividad) -> bytes:
    area = PAGINA_PDF + (MARGEN_PDF, MARGEN_PDF, -MARGEN_PDF, -(MARGEN_PDF + ALTO_PIE_PDF))

    # 1. Resumen con HTML
    salida = BytesIO()
    escritor = pymupdf.DocumentWriter(salida)
    historia = pymupdf.Story(html=_html_resumen(reporte), user_css=CSS_PDF)
    hay_mas = True
    ocupado = area
    while hay_mas:
        dispositivo = escritor.begin_page(PAGINA_PDF)
        hay_mas, ocupado = historia.place(area)
        historia.draw(dispositivo)
        escritor.end_page()
    escritor.close()

    # 2. Tabla de detalle a continuacion del resumen
    documento = pymupdf.open("pdf", salida.getvalue())
    _dibujar_detalle(documento, reporte, y_inicial=pymupdf.Rect(ocupado).y1 + 4)

    # 3. Pie de pagina con la numeracion
    total = documento.page_count
    for numero, hoja in enumerate(documento, start=1):
        texto = f"{TITULO_REPORTE}  -  Página {numero} de {total}"
        hoja.insert_text(
            (MARGEN_PDF, PAGINA_PDF.height - MARGEN_PDF + 10),
            texto,
            fontname=FUENTE_PDF,
            fontsize=8,
            color=COLOR_SECUNDARIO_PDF,
        )
    contenido = documento.tobytes(garbage=3, deflate=True)
    documento.close()
    return contenido


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------


def exportar_reporte(reporte: ReporteActividad, formato: FormatoExportacion) -> ArchivoExportado:
    try:
        contenido = _generar_pdf(reporte) if formato == "pdf" else _generar_xlsx(reporte)
    except Exception as error:  # noqa: BLE001 - cualquier fallo de la libreria se informa igual
        raise ErrorExportacionError("Ocurrio un error al generar el archivo del reporte.") from error

    return ArchivoExportado(
        contenido=contenido,
        nombre=nombre_archivo(reporte, formato),
        tipo_mime=TIPOS_MIME[formato],
    )

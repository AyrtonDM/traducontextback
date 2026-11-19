"""
HU-48 Exportacion de reportes: GET /reportes/actividad/exportar?formato=pdf|xlsx.

Usa los datos de prueba de marzo de 2001 (fixture `datos` de conftest): 6 actividades
(3 de texto, 2 documentos y 1 conversacion).
"""

import re
from io import BytesIO

import pymupdf
import pytest
from openpyxl import load_workbook

from app.core.configuracion import configuracion
from tests.conftest import crear_usuario

URL = f"{configuracion.api_v1_prefix}/reportes/actividad/exportar"
MARZO = {"fecha_desde": "2001-03-01", "fecha_hasta": "2001-03-31", "zona_horaria": "America/La_Paz"}


def exportar(cliente, formato, **filtros):
    return cliente.get(URL, params={**MARZO, "formato": formato, **filtros})


def nombre_descargado(respuesta) -> str:
    return re.search(r'filename="([^"]+)"', respuesta.headers["content-disposition"]).group(1)


def texto_pdf(contenido: bytes) -> str:
    with pymupdf.open("pdf", contenido) as documento:
        return "\n".join(hoja.get_text() for hoja in documento)


def valores_xlsx(contenido: bytes) -> list[list]:
    hoja = load_workbook(BytesIO(contenido)).active
    return [[c for c in fila] for fila in hoja.iter_rows(values_only=True)]


# ---------------------------------------------------------------------------
# Acceso y validaciones
# ---------------------------------------------------------------------------


def test_usuario_sin_rol_admin_recibe_403(cliente_como, sesion, admin):
    normal = crear_usuario(sesion, "USUARIO")
    assert exportar(cliente_como(normal), "pdf").status_code == 403


def test_formato_obligatorio_y_valido(cliente_admin):
    assert cliente_admin.get(URL, params=MARZO).status_code == 422
    assert exportar(cliente_admin, "docx").status_code == 422


def test_fecha_inicial_posterior_a_final_responde_400(cliente_admin):
    respuesta = exportar(cliente_admin, "xlsx", fecha_desde="2001-03-10", fecha_hasta="2001-03-01")
    assert respuesta.status_code == 400


# ---------------------------------------------------------------------------
# Excel
# ---------------------------------------------------------------------------


def test_excel_contiene_filtros_totales_y_detalle(cliente_admin, datos):
    respuesta = exportar(cliente_admin, "xlsx", id_idioma_origen=datos["idiomas"]["es"].id_idioma)
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    filas = valores_xlsx(respuesta.content)
    planas = [[v for v in fila if v is not None] for fila in filas]
    assert ["Idioma de origen", datos["idiomas"]["es"].nombre] in planas
    assert ["Período", "01/03/2001 - 31/03/2001"] in planas
    assert ["Texto", 3] in planas
    assert ["Documento", 2] in planas
    assert ["Total", 5] in planas
    assert any(fila and fila[0] == "Generado el" for fila in planas)

    encabezado = filas.index(["Fecha", "Servicio", "Usuario", "Correo", "Idioma origen", "Idioma destino", "Contexto", "Estado", "Detalle"])
    detalle = [fila for fila in filas[encabezado + 1:] if fila[0] is not None]
    assert len(detalle) == 5  # mismas filas que el reporte con ese filtro


def test_nombre_del_archivo_incluye_tipo_y_fecha(cliente_admin, datos):
    for formato in ("xlsx", "pdf"):
        nombre = nombre_descargado(exportar(cliente_admin, formato))
        assert re.fullmatch(rf"reporte_actividad_\d{{4}}-\d{{2}}-\d{{2}}_\d{{4}}\.{formato}", nombre)


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------


def test_pdf_contiene_filtros_totales_y_detalle(cliente_admin, datos):
    respuesta = exportar(cliente_admin, "pdf", tipo_servicio="documento")
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.headers["content-type"] == "application/pdf"

    texto = texto_pdf(respuesta.content)
    assert "Reporte de actividad" in texto
    assert "Generado el" in texto
    assert "Filtros aplicados" in texto
    assert "Documento" in texto  # tipo de servicio filtrado
    assert "01/03/2001 - 31/03/2001" in texto
    assert texto.count("doc.docx") == 2  # las 2 filas del detalle
    assert datos["usuarios"][0].correo in texto


def test_pdf_largo_repite_encabezado_en_cada_pagina(cliente_admin, datos, monkeypatch):
    from app.schemas.reporte import ActividadReporte
    from app.services import reportes

    original = reportes._detalle

    def detalle_largo(*args, **kwargs):
        filas = original(*args, **kwargs)
        return [ActividadReporte(**{**filas[0].model_dump(), "id_registro": i}) for i in range(120)]

    monkeypatch.setattr(reportes, "_detalle", detalle_largo)
    respuesta = exportar(cliente_admin, "pdf")
    assert respuesta.status_code == 200

    with pymupdf.open("pdf", respuesta.content) as documento:
        assert documento.page_count > 1
        for numero, hoja in enumerate(documento, start=1):
            texto = hoja.get_text()
            assert "Idioma destino" in texto  # encabezado de la tabla
            assert f"Página {numero} de {documento.page_count}" in texto


# ---------------------------------------------------------------------------
# Casos limite y errores
# ---------------------------------------------------------------------------


def test_reporte_sin_resultados_se_exporta_con_aviso(cliente_admin, datos):
    respuesta = exportar(cliente_admin, "pdf", fecha_desde="2001-04-01", fecha_hasta="2001-04-30")
    assert respuesta.status_code == 200
    assert "No se encontraron actividades" in texto_pdf(respuesta.content)


def test_reporte_demasiado_grande_responde_400(cliente_admin, datos, monkeypatch):
    monkeypatch.setattr("app.api.routes.reportes.MAXIMO_FILAS_EXPORTACION", 2)
    respuesta = exportar(cliente_admin, "xlsx")
    assert respuesta.status_code == 400
    assert "Acota los filtros" in respuesta.json()["mensaje"]


@pytest.mark.parametrize("formato", ["pdf", "xlsx"])
def test_error_al_generar_el_archivo_responde_500(cliente_admin, datos, monkeypatch, formato):
    def fallar(_reporte):
        raise RuntimeError("fallo de la libreria")

    monkeypatch.setattr(f"app.services.exportacion_reportes._generar_{formato}", fallar)
    respuesta = exportar(cliente_admin, formato)
    assert respuesta.status_code == 500
    assert "error al generar el archivo" in respuesta.json()["mensaje"]

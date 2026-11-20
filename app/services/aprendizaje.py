"""
HU-34 Aprendizaje de preferencias: registro de correcciones y alternativas elegidas, y seleccion
de ejemplos que orientan las siguientes traducciones del mismo usuario y par de idiomas.
"""

from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.traduccion.correccion_traduccion import CorreccionTraduccion
from app.models.traduccion.idioma import Idioma
from app.models.usuario.usuario import Usuario
from app.schemas.aprendizaje import (
    CorreccionDetalle,
    EstadoAprendizaje,
    RegistrarCorreccionSolicitud,
)
from app.services.enriquecedor_traduccion import neutralizar_delimitadores
from app.services.historial_traducciones import _normalizar_para_comparar, calcular_similitud

# Ejemplos que se envian al modelo por traduccion y candidatos revisados para elegirlos
MAX_EJEMPLOS = 5
CANDIDATOS_EJEMPLOS = 200
MAX_CARACTERES_CAMPO_EJEMPLO = 300
MAX_CORRECCIONES_LISTADO = 500


class CorreccionNoEncontradaError(ValueError):
    """La correccion no existe o no pertenece al usuario autenticado."""


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _idioma_por_codigo(sesion: Session, codigo: str) -> Idioma:
    idioma = sesion.scalar(select(Idioma).where(func.lower(Idioma.codigo) == codigo.strip().lower()))
    if not idioma:
        raise ValueError(f"Idioma '{codigo}' no encontrado.")
    return idioma


def armar_detalle_correccion(correccion: CorreccionTraduccion) -> CorreccionDetalle:
    return CorreccionDetalle(
        id_correccion=correccion.id_correccion,
        tipo=correccion.tipo,
        texto_original=correccion.texto_original,
        traduccion_generada=correccion.traduccion_generada,
        traduccion_corregida=correccion.traduccion_corregida,
        codigo_idioma_origen=correccion.idioma_origen.codigo if correccion.idioma_origen else None,
        codigo_idioma_destino=correccion.idioma_destino.codigo if correccion.idioma_destino else None,
        nombre_idioma_origen=correccion.idioma_origen.nombre if correccion.idioma_origen else None,
        nombre_idioma_destino=correccion.idioma_destino.nombre if correccion.idioma_destino else None,
        fecha_creacion=correccion.fecha_creacion,
        fecha_actualizacion=correccion.fecha_actualizacion,
    )


def _consulta_correcciones():
    return select(CorreccionTraduccion).options(
        selectinload(CorreccionTraduccion.idioma_origen),
        selectinload(CorreccionTraduccion.idioma_destino),
    )


def _aprendizaje_activo(sesion: Session, id_usuario: int) -> bool:
    return bool(sesion.scalar(select(Usuario.aprendizaje_activo).where(Usuario.id == id_usuario)))


# ---------------------------------------------------------------------------
# Estado del aprendizaje
# ---------------------------------------------------------------------------


def obtener_estado(sesion: Session, id_usuario: int) -> EstadoAprendizaje:
    total = sesion.scalar(
        select(func.count()).select_from(CorreccionTraduccion).where(
            CorreccionTraduccion.id_usuario == id_usuario
        )
    )
    return EstadoAprendizaje(activo=_aprendizaje_activo(sesion, id_usuario), total_correcciones=total or 0)


def cambiar_estado(sesion: Session, id_usuario: int, activo: bool) -> EstadoAprendizaje:
    """Desactivar no borra lo aprendido: solo deja de registrarse y de aplicarse."""
    usuario = sesion.get(Usuario, id_usuario)
    if not usuario:
        raise ValueError("Usuario no encontrado.")
    usuario.aprendizaje_activo = activo
    usuario.fecha_actualizacion = _ahora()
    sesion.commit()
    return obtener_estado(sesion, id_usuario)


# ---------------------------------------------------------------------------
# Correcciones
# ---------------------------------------------------------------------------


def registrar_correccion(
    sesion: Session,
    id_usuario: int,
    datos: RegistrarCorreccionSolicitud,
) -> CorreccionTraduccion | None:
    """
    Guarda la correccion o alternativa elegida. Devuelve None (sin guardar) si el aprendizaje esta
    desactivado. Si ya hay una para el mismo texto original y par, se reemplaza: vale la ultima.
    """
    if not _aprendizaje_activo(sesion, id_usuario):
        return None

    origen = _idioma_por_codigo(sesion, datos.idioma_origen)
    destino = _idioma_por_codigo(sesion, datos.idioma_destino)

    existente = sesion.scalar(
        select(CorreccionTraduccion).where(
            CorreccionTraduccion.id_usuario == id_usuario,
            CorreccionTraduccion.id_idioma_origen == origen.id_idioma,
            CorreccionTraduccion.id_idioma_destino == destino.id_idioma,
            CorreccionTraduccion.texto_original == datos.texto_original,
        )
    )
    if existente:
        existente.traduccion_generada = datos.traduccion_generada
        existente.traduccion_corregida = datos.traduccion_corregida
        existente.tipo = datos.tipo
        existente.fecha_actualizacion = _ahora()
        correccion = existente
    else:
        correccion = CorreccionTraduccion(
            id_usuario=id_usuario,
            id_idioma_origen=origen.id_idioma,
            id_idioma_destino=destino.id_idioma,
            texto_original=datos.texto_original,
            traduccion_generada=datos.traduccion_generada,
            traduccion_corregida=datos.traduccion_corregida,
            tipo=datos.tipo,
        )
        sesion.add(correccion)
    sesion.commit()
    return sesion.scalar(
        _consulta_correcciones().where(CorreccionTraduccion.id_correccion == correccion.id_correccion)
    )


def listar_correcciones(
    sesion: Session,
    id_usuario: int,
    idioma_origen: str | None = None,
    idioma_destino: str | None = None,
) -> list[CorreccionTraduccion]:
    """Correcciones del usuario, de la mas reciente a la mas antigua, con filtro opcional por idioma."""
    consulta = _consulta_correcciones().where(CorreccionTraduccion.id_usuario == id_usuario)
    if idioma_origen:
        consulta = consulta.where(
            CorreccionTraduccion.id_idioma_origen == _idioma_por_codigo(sesion, idioma_origen).id_idioma
        )
    if idioma_destino:
        consulta = consulta.where(
            CorreccionTraduccion.id_idioma_destino == _idioma_por_codigo(sesion, idioma_destino).id_idioma
        )
    consulta = consulta.order_by(
        func.coalesce(CorreccionTraduccion.fecha_actualizacion, CorreccionTraduccion.fecha_creacion).desc(),
        CorreccionTraduccion.id_correccion.desc(),
    ).limit(MAX_CORRECCIONES_LISTADO)
    return list(sesion.scalars(consulta).all())


def eliminar_correccion(sesion: Session, id_usuario: int, id_correccion: int) -> None:
    correccion = sesion.scalar(
        select(CorreccionTraduccion).where(
            CorreccionTraduccion.id_correccion == id_correccion,
            CorreccionTraduccion.id_usuario == id_usuario,
        )
    )
    if not correccion:
        raise CorreccionNoEncontradaError(
            "Correccion no encontrada o no pertenece al usuario autenticado."
        )
    sesion.delete(correccion)
    sesion.commit()


def eliminar_todas(sesion: Session, id_usuario: int) -> int:
    resultado = sesion.execute(
        delete(CorreccionTraduccion).where(CorreccionTraduccion.id_usuario == id_usuario)
    )
    sesion.commit()
    return resultado.rowcount or 0


# ---------------------------------------------------------------------------
# Uso durante la traduccion
# ---------------------------------------------------------------------------


def _recortar(texto: str) -> str:
    linea = neutralizar_delimitadores(" ".join(texto.split()))
    if len(linea) > MAX_CARACTERES_CAMPO_EJEMPLO:
        linea = linea[: MAX_CARACTERES_CAMPO_EJEMPLO - 3].rstrip() + "..."
    return linea


def _puntaje(texto_normalizado: str, original: str) -> float:
    """Parecido de frases o, si comparten terminos, proporcion de palabras en comun."""
    original_normalizado = _normalizar_para_comparar(original)
    similitud = calcular_similitud(texto_normalizado, original_normalizado)
    palabras_texto = set(texto_normalizado.split())
    palabras_original = set(original_normalizado.split())
    if not palabras_texto or not palabras_original:
        return similitud
    comunes = len(palabras_texto & palabras_original) / len(palabras_texto | palabras_original)
    return max(similitud, comunes)


def ejemplos_para_traduccion(
    sesion: Session,
    id_usuario: int,
    codigo_idioma_origen: str,
    codigo_idioma_destino: str,
    texto: str,
) -> list[str]:
    """
    Hasta MAX_EJEMPLOS correcciones del usuario en el mismo par de idiomas, primero las mas parecidas
    al texto y, a igual parecido, las mas recientes. Lista vacia si el aprendizaje esta desactivado,
    si no hay correcciones o si los idiomas no existen. Solo usa correcciones del propio usuario.
    """
    if not _aprendizaje_activo(sesion, id_usuario):
        return []
    try:
        origen = _idioma_por_codigo(sesion, codigo_idioma_origen)
        destino = _idioma_por_codigo(sesion, codigo_idioma_destino)
    except ValueError:
        return []

    candidatas = sesion.scalars(
        select(CorreccionTraduccion)
        .where(
            CorreccionTraduccion.id_usuario == id_usuario,
            CorreccionTraduccion.id_idioma_origen == origen.id_idioma,
            CorreccionTraduccion.id_idioma_destino == destino.id_idioma,
        )
        .order_by(
            func.coalesce(CorreccionTraduccion.fecha_actualizacion, CorreccionTraduccion.fecha_creacion).desc(),
            CorreccionTraduccion.id_correccion.desc(),
        )
        .limit(CANDIDATOS_EJEMPLOS)
    ).all()
    if not candidatas:
        return []

    normalizado = _normalizar_para_comparar(texto)
    # sorted es estable: a igual puntaje se conserva el orden por fecha (mas recientes primero)
    elegidas = sorted(candidatas, key=lambda c: _puntaje(normalizado, c.texto_original), reverse=True)
    return [
        (
            f"Original: {_recortar(c.texto_original)} | Traduccion generada: {_recortar(c.traduccion_generada)}"
            f" | Version preferida por el usuario: {_recortar(c.traduccion_corregida)}"
        )
        for c in elegidas[:MAX_EJEMPLOS]
    ]

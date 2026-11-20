import re
import unicodedata
from datetime import date, datetime, time, timedelta
from difflib import SequenceMatcher

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, aliased, joinedload

from app.models.traduccion.configuracion_traduccion import ConfiguracionTraduccion
from app.models.traduccion.idioma import Idioma
from app.models.traduccion.traduccion import Traduccion
from app.schemas.traduccion import SugerenciaTraduccion, TraduccionHistorialDetalle


# Reutilizacion de traducciones (HU-44)
MAXIMO_SUGERENCIAS = 3
SIMILITUD_MINIMA = 0.6
CANDIDATOS_SUGERENCIAS = 500


def _escapar_like(texto: str) -> str:
    """Escapa los comodines de LIKE para que se busquen de forma literal."""
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def listar_historial(
    sesion: Session,
    id_usuario: int,
    texto: str | None = None,
    idioma_origen: str | None = None,
    idioma_destino: str | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    solo_favoritos: bool = False,
) -> list[TraduccionHistorialDetalle]:
    """Retorna el historial de traducciones del usuario aplicando los filtros combinados (AND)."""
    if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
        raise ValueError("La fecha desde no puede ser mayor que la fecha hasta.")

    IdiomaOrigen = aliased(Idioma)
    IdiomaDestino = aliased(Idioma)

    consulta = (
        select(Traduccion, IdiomaOrigen.codigo, IdiomaDestino.codigo)
        .join(IdiomaOrigen, Traduccion.id_idioma_origen == IdiomaOrigen.id_idioma)
        .join(IdiomaDestino, Traduccion.id_idioma_destino == IdiomaDestino.id_idioma)
        .options(
            joinedload(Traduccion.configuracion_traduccion).joinedload(ConfiguracionTraduccion.contexto),
            joinedload(Traduccion.configuracion_traduccion).joinedload(ConfiguracionTraduccion.tono),
            joinedload(Traduccion.configuracion_traduccion).joinedload(ConfiguracionTraduccion.variante_regional),
        )
        .where(Traduccion.id_usuario == id_usuario)
    )

    if texto and texto.strip():
        patron = f"%{_escapar_like(texto.strip())}%"
        consulta = consulta.where(
            or_(
                Traduccion.texto_original.ilike(patron, escape="\\"),
                Traduccion.texto_traducido.ilike(patron, escape="\\"),
            )
        )
    if idioma_origen:
        consulta = consulta.where(IdiomaOrigen.codigo == idioma_origen)
    if idioma_destino:
        consulta = consulta.where(IdiomaDestino.codigo == idioma_destino)
    if fecha_desde:
        consulta = consulta.where(
            Traduccion.fecha_creacion >= datetime.combine(fecha_desde, time.min)
        )
    if fecha_hasta:
        consulta = consulta.where(
            Traduccion.fecha_creacion < datetime.combine(fecha_hasta + timedelta(days=1), time.min)
        )
    if solo_favoritos:
        consulta = consulta.where(Traduccion.favorito.is_(True))

    consulta = consulta.order_by(Traduccion.fecha_creacion.desc(), Traduccion.id_traduccion.desc())

    historial: list[TraduccionHistorialDetalle] = []
    for traduccion, codigo_origen, codigo_destino in sesion.execute(consulta).unique().all():
        config = traduccion.configuracion_traduccion
        historial.append(
            TraduccionHistorialDetalle(
                id_traduccion=traduccion.id_traduccion,
                texto_original=traduccion.texto_original,
                texto_traducido=traduccion.texto_traducido,
                fecha_creacion=traduccion.fecha_creacion,
                idioma_origen=codigo_origen,
                idioma_destino=codigo_destino,
                nombre_contexto=config.contexto.nombre if config and config.contexto else None,
                nombre_tono=config.tono.nombre if config and config.tono else None,
                nombre_variante_regional=(
                    config.variante_regional.nombre if config and config.variante_regional else None
                ),
                explicar_expresiones=config.explicar_expresiones if config else False,
                generar_alternativas=config.generar_alternativas if config else False,
                favorito=traduccion.favorito,
            )
        )
    return historial


def obtener_traduccion_usuario(
    sesion: Session,
    id_traduccion: int,
    id_usuario: int,
) -> Traduccion | None:
    """Retorna la traduccion solo si pertenece al usuario indicado."""
    return sesion.scalar(
        select(Traduccion).where(
            Traduccion.id_traduccion == id_traduccion,
            Traduccion.id_usuario == id_usuario,
        )
    )


def definir_favorito(
    sesion: Session,
    traduccion: Traduccion,
    favorito: bool,
) -> Traduccion:
    """Marca o desmarca una traduccion como favorita."""
    traduccion.favorito = favorito
    sesion.commit()
    sesion.refresh(traduccion)
    return traduccion


def eliminar_traduccion(sesion: Session, traduccion: Traduccion) -> None:
    """Elimina una traduccion del historial. Ninguna tabla tiene FK hacia traduccion."""
    sesion.delete(traduccion)
    sesion.commit()


# ---------------------------------------------------------------------------
# Reutilizacion de traducciones (HU-44)
# ---------------------------------------------------------------------------


def _normalizar_para_comparar(texto: str) -> str:
    """Minusculas, sin tildes ni signos de puntuacion y con espacios simples."""
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    sin_signos = re.sub(r"[^\w\s]", " ", sin_tildes.lower())
    return " ".join(sin_signos.split())


def calcular_similitud(texto_a: str, texto_b: str) -> float:
    """Parecido entre 0 y 1 de dos textos ya normalizados."""
    if not texto_a or not texto_b:
        return 0.0
    if texto_a == texto_b:
        return 1.0
    comparador = SequenceMatcher(None, texto_a, texto_b, autojunk=False)
    # quick_ratio es una cota superior barata: descarta rapido los textos muy distintos
    if comparador.quick_ratio() < SIMILITUD_MINIMA:
        return 0.0
    return comparador.ratio()


def buscar_traducciones_similares(
    sesion: Session,
    id_usuario: int,
    texto: str,
    id_idioma_origen: int,
    id_idioma_destino: int,
    excluir_traduccion: str | None = None,
) -> list[SugerenciaTraduccion]:
    """
    Busca en el historial del usuario autenticado traducciones del mismo par de idiomas cuyo
    texto original se parezca al texto nuevo. Devuelve como maximo 3, de mayor a menor similitud.

    - Solo considera traducciones del usuario; las eliminadas del historial ya no existen.
    - Revisa las ultimas CANDIDATOS_SUGERENCIAS traducciones del par para acotar el costo.
    - Agrupa repeticiones (mismo original y misma traduccion) y se queda con la mas reciente.
    - `excluir_traduccion` omite sugerencias identicas a la traduccion recien generada.
    """
    normalizado = _normalizar_para_comparar(texto)
    if not normalizado:
        return []
    excluida = _normalizar_para_comparar(excluir_traduccion) if excluir_traduccion else None

    candidatas = sesion.scalars(
        select(Traduccion)
        .where(
            Traduccion.id_usuario == id_usuario,
            Traduccion.id_idioma_origen == id_idioma_origen,
            Traduccion.id_idioma_destino == id_idioma_destino,
        )
        .order_by(Traduccion.fecha_creacion.desc(), Traduccion.id_traduccion.desc())
        .limit(CANDIDATOS_SUGERENCIAS)
    ).all()

    vistas: set[tuple[str, str]] = set()
    sugerencias: list[SugerenciaTraduccion] = []
    for candidata in candidatas:
        original = _normalizar_para_comparar(candidata.texto_original)
        traducida = _normalizar_para_comparar(candidata.texto_traducido)
        clave = (original, traducida)
        if clave in vistas or (excluida is not None and traducida == excluida):
            continue
        vistas.add(clave)

        similitud = calcular_similitud(normalizado, original)
        if similitud >= SIMILITUD_MINIMA:
            sugerencias.append(
                SugerenciaTraduccion(
                    id_traduccion=candidata.id_traduccion,
                    texto_original=candidata.texto_original,
                    texto_traducido=candidata.texto_traducido,
                    fecha_creacion=candidata.fecha_creacion,
                    similitud=round(similitud, 3),
                )
            )

    # Orden estable: a igual similitud queda primero la mas reciente (ya vienen por fecha)
    sugerencias.sort(key=lambda s: s.similitud, reverse=True)
    return sugerencias[:MAXIMO_SUGERENCIAS]


# ---------------------------------------------------------------------------
# Registro en el historial al terminar la traduccion
# ---------------------------------------------------------------------------


def registrar_traduccion(
    sesion: Session,
    id_usuario: int,
    texto_original: str,
    texto_traducido: str,
    codigo_idioma_origen: str,
    codigo_idioma_destino: str,
    id_glosario: int | None = None,
) -> Traduccion:
    """
    Guarda en el historial del usuario una traduccion ya realizada. La traduccion automatica
    mientras se escribe no se guarda; el cliente la registra cuando el usuario termina.
    """
    from app.services.glosarios import obtener_glosario_para_traduccion

    origen = sesion.scalar(select(Idioma).where(Idioma.codigo == codigo_idioma_origen))
    destino = sesion.scalar(select(Idioma).where(Idioma.codigo == codigo_idioma_destino))
    if origen is None or destino is None:
        raise ValueError("El idioma de origen o de destino no esta registrado.")

    config = sesion.scalar(
        select(ConfiguracionTraduccion).where(ConfiguracionTraduccion.id_usuario == id_usuario)
    )
    if config is None:
        raise ValueError(
            "El usuario no tiene una configuracion de traduccion registrada. "
            "Debe guardar su configuracion previamente."
        )

    if id_glosario is not None:
        # Valida que el glosario sea del usuario y del mismo par (GlosarioNoEncontradoError si no)
        obtener_glosario_para_traduccion(
            sesion=sesion,
            id_usuario=id_usuario,
            id_glosario=id_glosario,
            codigo_idioma_origen=origen.codigo,
            codigo_idioma_destino=destino.codigo,
        )

    registro = Traduccion(
        texto_original=texto_original,
        texto_traducido=texto_traducido,
        id_configuracion_traduccion=config.id_configuracion_traduccion,
        id_idioma_origen=origen.id_idioma,
        id_idioma_destino=destino.id_idioma,
        id_usuario=id_usuario,
        id_glosario=id_glosario,
    )
    sesion.add(registro)
    sesion.commit()
    sesion.refresh(registro)
    return registro


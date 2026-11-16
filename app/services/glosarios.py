from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.glosario.glosario import Glosario
from app.models.glosario.termino_glosario import TerminoGlosario
from app.models.traduccion.idioma import Idioma
from app.schemas.glosario import (
    ActualizarGlosarioSolicitud,
    ActualizarTerminoGlosarioSolicitud,
    CrearGlosarioSolicitud,
    GlosarioDetalle,
    GlosarioResumen,
    TerminoGlosarioDetalle,
    TerminoGlosarioSolicitud,
)


class GlosarioNoEncontradoError(ValueError):
    """El glosario o termino no existe o no pertenece al usuario autenticado."""


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _obtener_idioma_por_id(sesion: Session, id_idioma: int) -> Idioma:
    idioma = sesion.scalar(select(Idioma).where(Idioma.id_idioma == id_idioma))
    if not idioma:
        raise ValueError(f"Idioma con id {id_idioma} no encontrado.")
    return idioma


def buscar_idioma_por_codigo(sesion: Session, codigo_o_nombre: str) -> Idioma | None:
    """Busca un idioma por su codigo ('en') o por su nombre ('Ingles')."""
    valor = codigo_o_nombre.strip()
    if not valor:
        return None
    return sesion.scalar(
        select(Idioma).where(
            (Idioma.codigo == valor.lower()) | (Idioma.nombre.ilike(valor))
        )
    )


def _validar_nombre_unico(
    sesion: Session,
    id_usuario: int,
    nombre: str,
    id_glosario_excluir: int | None = None,
) -> None:
    consulta = select(Glosario).where(
        Glosario.id_usuario == id_usuario,
        func.lower(Glosario.nombre) == func.lower(nombre),
    )
    if id_glosario_excluir is not None:
        consulta = consulta.where(Glosario.id_glosario != id_glosario_excluir)
    if sesion.scalar(consulta):
        raise ValueError(f"Ya tienes un glosario registrado con el nombre '{nombre}'.")


def _validar_termino_unico(
    glosario: Glosario,
    termino_origen: str,
    id_termino_excluir: int | None = None,
) -> None:
    termino_lower = termino_origen.lower()
    for termino in glosario.terminos:
        if termino.id_termino_glosario == id_termino_excluir:
            continue
        if termino.termino_origen.lower() == termino_lower:
            raise ValueError(
                f"El termino '{termino_origen}' ya esta registrado en este glosario."
            )


def _nuevo_termino(datos: TerminoGlosarioSolicitud) -> TerminoGlosario:
    return TerminoGlosario(
        termino_origen=datos.termino_origen,
        traduccion_preferida=None if datos.conservar_original else datos.traduccion_preferida,
        conservar_original=datos.conservar_original,
        distinguir_mayusculas=datos.distinguir_mayusculas,
        nota=datos.nota,
    )


# ---------------------------------------------------------------------------
# Armado de respuestas
# ---------------------------------------------------------------------------


def armar_resumen_glosario(glosario: Glosario) -> GlosarioResumen:
    return GlosarioResumen(
        id_glosario=glosario.id_glosario,
        nombre=glosario.nombre,
        descripcion=glosario.descripcion,
        id_usuario=glosario.id_usuario,
        id_idioma_origen=glosario.id_idioma_origen,
        id_idioma_destino=glosario.id_idioma_destino,
        codigo_idioma_origen=glosario.idioma_origen.codigo if glosario.idioma_origen else None,
        codigo_idioma_destino=glosario.idioma_destino.codigo if glosario.idioma_destino else None,
        nombre_idioma_origen=glosario.idioma_origen.nombre if glosario.idioma_origen else None,
        nombre_idioma_destino=glosario.idioma_destino.nombre if glosario.idioma_destino else None,
        cantidad_terminos=len(glosario.terminos),
        fecha_creacion=glosario.fecha_creacion,
        fecha_actualizacion=glosario.fecha_actualizacion,
    )


def armar_detalle_glosario(glosario: Glosario) -> GlosarioDetalle:
    resumen = armar_resumen_glosario(glosario)
    return GlosarioDetalle(
        **resumen.model_dump(exclude={"id", "par_idiomas"}),
        terminos=[TerminoGlosarioDetalle.model_validate(t) for t in glosario.terminos],
    )


# ---------------------------------------------------------------------------
# Glosarios: CRUD
# ---------------------------------------------------------------------------


def obtener_glosario_usuario(
    sesion: Session,
    id_usuario: int,
    id_glosario: int,
) -> Glosario:
    """Obtiene un glosario del usuario o lanza GlosarioNoEncontradoError."""
    glosario = sesion.scalar(
        select(Glosario)
        .options(
            selectinload(Glosario.terminos),
            selectinload(Glosario.idioma_origen),
            selectinload(Glosario.idioma_destino),
        )
        .where(
            Glosario.id_glosario == id_glosario,
            Glosario.id_usuario == id_usuario,
        )
    )
    if not glosario:
        raise GlosarioNoEncontradoError(
            "Glosario no encontrado o no pertenece al usuario autenticado."
        )
    return glosario


def listar_glosarios_usuario(
    sesion: Session,
    id_usuario: int,
    idioma_origen: str | None = None,
    idioma_destino: str | None = None,
) -> list[Glosario]:
    """
    Lista los glosarios del usuario. Si se indican idiomas (codigo o nombre),
    solo retorna los glosarios de ese par, para ofrecerlos al momento de traducir.
    """
    consulta = (
        select(Glosario)
        .options(
            selectinload(Glosario.terminos),
            selectinload(Glosario.idioma_origen),
            selectinload(Glosario.idioma_destino),
        )
        .where(Glosario.id_usuario == id_usuario)
    )

    if idioma_origen:
        idioma = buscar_idioma_por_codigo(sesion, idioma_origen)
        if not idioma:
            return []
        consulta = consulta.where(Glosario.id_idioma_origen == idioma.id_idioma)

    if idioma_destino:
        idioma = buscar_idioma_por_codigo(sesion, idioma_destino)
        if not idioma:
            return []
        consulta = consulta.where(Glosario.id_idioma_destino == idioma.id_idioma)

    consulta = consulta.order_by(Glosario.fecha_creacion.desc())
    return list(sesion.scalars(consulta).all())


def crear_glosario(
    sesion: Session,
    id_usuario: int,
    datos: CrearGlosarioSolicitud,
) -> Glosario:
    _obtener_idioma_por_id(sesion, datos.id_idioma_origen)
    _obtener_idioma_por_id(sesion, datos.id_idioma_destino)
    _validar_nombre_unico(sesion, id_usuario, datos.nombre)

    glosario = Glosario(
        nombre=datos.nombre,
        descripcion=datos.descripcion,
        id_usuario=id_usuario,
        id_idioma_origen=datos.id_idioma_origen,
        id_idioma_destino=datos.id_idioma_destino,
    )

    for datos_termino in datos.terminos:
        _validar_termino_unico(glosario, datos_termino.termino_origen)
        glosario.terminos.append(_nuevo_termino(datos_termino))

    sesion.add(glosario)
    sesion.commit()
    return obtener_glosario_usuario(sesion, id_usuario, glosario.id_glosario)


def actualizar_glosario(
    sesion: Session,
    id_usuario: int,
    id_glosario: int,
    datos: ActualizarGlosarioSolicitud,
) -> Glosario:
    glosario = obtener_glosario_usuario(sesion, id_usuario, id_glosario)
    campos = datos.model_fields_set

    if "nombre" in campos and datos.nombre is not None:
        _validar_nombre_unico(sesion, id_usuario, datos.nombre, id_glosario)
        glosario.nombre = datos.nombre

    if "descripcion" in campos:
        glosario.descripcion = datos.descripcion

    nuevo_origen = (
        datos.id_idioma_origen
        if "id_idioma_origen" in campos and datos.id_idioma_origen is not None
        else glosario.id_idioma_origen
    )
    nuevo_destino = (
        datos.id_idioma_destino
        if "id_idioma_destino" in campos and datos.id_idioma_destino is not None
        else glosario.id_idioma_destino
    )
    if nuevo_origen == nuevo_destino:
        raise ValueError("El idioma de origen y el de destino deben ser distintos.")
    if nuevo_origen != glosario.id_idioma_origen:
        _obtener_idioma_por_id(sesion, nuevo_origen)
        glosario.id_idioma_origen = nuevo_origen
    if nuevo_destino != glosario.id_idioma_destino:
        _obtener_idioma_por_id(sesion, nuevo_destino)
        glosario.id_idioma_destino = nuevo_destino

    glosario.fecha_actualizacion = _ahora()
    sesion.commit()
    sesion.expire_all()
    return obtener_glosario_usuario(sesion, id_usuario, id_glosario)


def eliminar_glosario(sesion: Session, id_usuario: int, id_glosario: int) -> None:
    """Elimina el glosario y sus terminos. Las traducciones que lo usaron se conservan."""
    glosario = obtener_glosario_usuario(sesion, id_usuario, id_glosario)
    sesion.delete(glosario)
    sesion.commit()


# ---------------------------------------------------------------------------
# Terminos: CRUD
# ---------------------------------------------------------------------------


def _obtener_termino(glosario: Glosario, id_termino: int) -> TerminoGlosario:
    for termino in glosario.terminos:
        if termino.id_termino_glosario == id_termino:
            return termino
    raise GlosarioNoEncontradoError("Termino no encontrado en el glosario indicado.")


def agregar_termino(
    sesion: Session,
    id_usuario: int,
    id_glosario: int,
    datos: TerminoGlosarioSolicitud,
) -> TerminoGlosario:
    glosario = obtener_glosario_usuario(sesion, id_usuario, id_glosario)
    _validar_termino_unico(glosario, datos.termino_origen)

    termino = _nuevo_termino(datos)
    glosario.terminos.append(termino)
    glosario.fecha_actualizacion = _ahora()
    sesion.commit()
    sesion.refresh(termino)
    return termino


def actualizar_termino(
    sesion: Session,
    id_usuario: int,
    id_glosario: int,
    id_termino: int,
    datos: ActualizarTerminoGlosarioSolicitud,
) -> TerminoGlosario:
    glosario = obtener_glosario_usuario(sesion, id_usuario, id_glosario)
    termino = _obtener_termino(glosario, id_termino)
    campos = datos.model_fields_set

    if "termino_origen" in campos and datos.termino_origen is not None:
        _validar_termino_unico(glosario, datos.termino_origen, id_termino)
        termino.termino_origen = datos.termino_origen
    if "traduccion_preferida" in campos:
        termino.traduccion_preferida = datos.traduccion_preferida
    if "conservar_original" in campos and datos.conservar_original is not None:
        termino.conservar_original = datos.conservar_original
    if "distinguir_mayusculas" in campos and datos.distinguir_mayusculas is not None:
        termino.distinguir_mayusculas = datos.distinguir_mayusculas
    if "nota" in campos:
        termino.nota = datos.nota

    # Validar la regla resultante del termino
    if termino.conservar_original:
        termino.traduccion_preferida = None
    elif not termino.traduccion_preferida:
        sesion.rollback()
        raise ValueError(
            "Debe indicar una traduccion preferida o marcar el termino para conservarse en su idioma original."
        )

    glosario.fecha_actualizacion = _ahora()
    sesion.commit()
    sesion.refresh(termino)
    return termino


def eliminar_termino(
    sesion: Session,
    id_usuario: int,
    id_glosario: int,
    id_termino: int,
) -> None:
    glosario = obtener_glosario_usuario(sesion, id_usuario, id_glosario)
    termino = _obtener_termino(glosario, id_termino)
    glosario.terminos.remove(termino)
    glosario.fecha_actualizacion = _ahora()
    sesion.commit()


# ---------------------------------------------------------------------------
# Uso durante la traduccion
# ---------------------------------------------------------------------------


def obtener_glosario_para_traduccion(
    sesion: Session,
    id_usuario: int,
    id_glosario: int,
    codigo_idioma_origen: str,
    codigo_idioma_destino: str,
) -> Glosario:
    """
    Obtiene el glosario a aplicar en una traduccion validando que pertenezca al
    usuario y que corresponda exactamente al par de idiomas de la traduccion.
    """
    glosario = obtener_glosario_usuario(sesion, id_usuario, id_glosario)

    codigo_origen_glosario = glosario.idioma_origen.codigo.lower()
    codigo_destino_glosario = glosario.idioma_destino.codigo.lower()
    if (
        codigo_origen_glosario != codigo_idioma_origen.strip().lower()
        or codigo_destino_glosario != codigo_idioma_destino.strip().lower()
    ):
        raise ValueError(
            f"El glosario '{glosario.nombre}' es para "
            f"{codigo_origen_glosario.upper()} → {codigo_destino_glosario.upper()} "
            f"y la traduccion es {codigo_idioma_origen.upper()} → {codigo_idioma_destino.upper()}. "
            "Seleccione un glosario del mismo par de idiomas."
        )
    return glosario

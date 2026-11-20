from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.seguridad import requiere_token
from app.database.conexion import obtener_sesion
from app.models.usuario.usuario import Usuario
from app.schemas.glosario import (
    ActualizarGlosarioSolicitud,
    ActualizarTerminoGlosarioSolicitud,
    CrearGlosarioSolicitud,
    ListaGlosariosRespuesta,
    RespuestaEliminarGlosario,
    RespuestaGlosario,
    RespuestaTerminoGlosario,
    TerminoGlosarioDetalle,
    TerminoGlosarioSolicitud,
)
from app.services.glosarios import (
    GlosarioNoEncontradoError,
    actualizar_glosario,
    actualizar_termino,
    agregar_termino,
    armar_detalle_glosario,
    armar_resumen_glosario,
    crear_glosario,
    eliminar_glosario,
    eliminar_termino,
    listar_glosarios_usuario,
    obtener_glosario_usuario,
)


enrutador = APIRouter(
    prefix="/glosarios",
    tags=["glosarios"],
    dependencies=[Depends(requiere_token)],
)

RESPUESTAS_COMUNES = {
    status.HTTP_401_UNAUTHORIZED: {
        "description": "El token es invalido, expiro o no fue enviado."
    },
}
RESPUESTA_404 = {
    status.HTTP_404_NOT_FOUND: {
        "description": "El glosario o termino no existe o no pertenece al usuario autenticado."
    },
}


def _error_http(error: ValueError) -> HTTPException:
    """Traduce errores del servicio a respuestas HTTP (404 si no existe, 400 en otro caso)."""
    if isinstance(error, GlosarioNoEncontradoError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


# ---------------------------------------------------------------------------
# Glosarios
# ---------------------------------------------------------------------------


@enrutador.post(
    "",
    response_model=RespuestaGlosario,
    status_code=status.HTTP_201_CREATED,
    summary="Crear glosario personalizado (requiere token)",
    description=(
        "Crea un glosario del usuario autenticado para un par de idiomas (origen y destino). "
        "Opcionalmente se pueden enviar los terminos iniciales: cada termino debe tener una "
        "'traduccion_preferida' o marcarse con 'conservar_original' = true."
    ),
    responses={
        **RESPUESTAS_COMUNES,
        status.HTTP_400_BAD_REQUEST: {
            "description": "Idioma inexistente, nombre duplicado o terminos repetidos."
        },
    },
)
def crear_nuevo_glosario(
    datos: CrearGlosarioSolicitud,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaGlosario:
    try:
        glosario = crear_glosario(sesion=sesion, id_usuario=usuario.id, datos=datos)
    except ValueError as error:
        raise _error_http(error) from error

    return RespuestaGlosario(
        mensaje="Glosario creado correctamente.",
        resultado=armar_detalle_glosario(glosario),
    )


@enrutador.get(
    "",
    response_model=ListaGlosariosRespuesta,
    status_code=status.HTTP_200_OK,
    summary="Listar mis glosarios (requiere token)",
    description=(
        "Retorna los glosarios del usuario autenticado, del mas reciente al mas antiguo. "
        "Use 'idioma_origen' y 'idioma_destino' (codigo, por ejemplo 'en' y 'es') para "
        "obtener solo los glosarios aplicables a una traduccion de ese par de idiomas."
    ),
    responses=RESPUESTAS_COMUNES,
)
def listar_mis_glosarios(
    idioma_origen: str | None = Query(
        default=None,
        description="Codigo o nombre del idioma de origen para filtrar",
    ),
    idioma_destino: str | None = Query(
        default=None,
        description="Codigo o nombre del idioma de destino para filtrar",
    ),
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> ListaGlosariosRespuesta:
    glosarios = listar_glosarios_usuario(
        sesion=sesion,
        id_usuario=usuario.id,
        idioma_origen=idioma_origen,
        idioma_destino=idioma_destino,
    )
    return ListaGlosariosRespuesta(
        mensaje="Glosarios obtenidos correctamente.",
        resultado=[armar_resumen_glosario(g) for g in glosarios],
    )


@enrutador.get(
    "/{id_glosario}",
    response_model=RespuestaGlosario,
    status_code=status.HTTP_200_OK,
    summary="Consultar un glosario con sus terminos (requiere token)",
    responses={**RESPUESTAS_COMUNES, **RESPUESTA_404},
)
def consultar_glosario(
    id_glosario: int,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaGlosario:
    try:
        glosario = obtener_glosario_usuario(
            sesion=sesion,
            id_usuario=usuario.id,
            id_glosario=id_glosario,
        )
    except ValueError as error:
        raise _error_http(error) from error

    return RespuestaGlosario(
        mensaje="Glosario obtenido correctamente.",
        resultado=armar_detalle_glosario(glosario),
    )


@enrutador.patch(
    "/{id_glosario}",
    response_model=RespuestaGlosario,
    status_code=status.HTTP_200_OK,
    summary="Modificar un glosario (requiere token)",
    description=(
        "Actualiza el nombre, la descripcion y/o el par de idiomas del glosario. "
        "Solo se modifican los campos enviados."
    ),
    responses={
        **RESPUESTAS_COMUNES,
        **RESPUESTA_404,
        status.HTTP_400_BAD_REQUEST: {
            "description": "Idioma inexistente, idiomas iguales o nombre duplicado."
        },
    },
)
def modificar_glosario(
    id_glosario: int,
    datos: ActualizarGlosarioSolicitud,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaGlosario:
    try:
        glosario = actualizar_glosario(
            sesion=sesion,
            id_usuario=usuario.id,
            id_glosario=id_glosario,
            datos=datos,
        )
    except ValueError as error:
        raise _error_http(error) from error

    return RespuestaGlosario(
        mensaje="Glosario actualizado correctamente.",
        resultado=armar_detalle_glosario(glosario),
    )


@enrutador.delete(
    "/{id_glosario}",
    response_model=RespuestaEliminarGlosario,
    status_code=status.HTTP_200_OK,
    summary="Eliminar un glosario (requiere token)",
    description=(
        "Elimina el glosario y todos sus terminos. Las traducciones realizadas con este "
        "glosario se conservan (quedan sin glosario asociado)."
    ),
    responses={**RESPUESTAS_COMUNES, **RESPUESTA_404},
)
def borrar_glosario(
    id_glosario: int,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaEliminarGlosario:
    try:
        eliminar_glosario(sesion=sesion, id_usuario=usuario.id, id_glosario=id_glosario)
    except ValueError as error:
        raise _error_http(error) from error

    return RespuestaEliminarGlosario(mensaje="Glosario eliminado correctamente.")


# ---------------------------------------------------------------------------
# Terminos del glosario
# ---------------------------------------------------------------------------


@enrutador.post(
    "/{id_glosario}/terminos",
    response_model=RespuestaTerminoGlosario,
    status_code=status.HTTP_201_CREATED,
    summary="Agregar termino al glosario (requiere token)",
    description=(
        "Registra un termino con su regla: 'traduccion_preferida' para indicar como debe "
        "traducirse, o 'conservar_original' = true para mantenerlo en su idioma original."
    ),
    responses={
        **RESPUESTAS_COMUNES,
        **RESPUESTA_404,
        status.HTTP_400_BAD_REQUEST: {"description": "El termino ya existe en el glosario."},
    },
)
def agregar_termino_glosario(
    id_glosario: int,
    datos: TerminoGlosarioSolicitud,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaTerminoGlosario:
    try:
        termino = agregar_termino(
            sesion=sesion,
            id_usuario=usuario.id,
            id_glosario=id_glosario,
            datos=datos,
        )
    except ValueError as error:
        raise _error_http(error) from error

    return RespuestaTerminoGlosario(
        mensaje="Termino agregado correctamente.",
        resultado=TerminoGlosarioDetalle.model_validate(termino),
    )


@enrutador.patch(
    "/{id_glosario}/terminos/{id_termino}",
    response_model=RespuestaTerminoGlosario,
    status_code=status.HTTP_200_OK,
    summary="Modificar termino del glosario (requiere token)",
    description="Actualiza solo los campos enviados del termino.",
    responses={
        **RESPUESTAS_COMUNES,
        **RESPUESTA_404,
        status.HTTP_400_BAD_REQUEST: {
            "description": "Termino duplicado o regla incompleta (sin traduccion ni conservar)."
        },
    },
)
def modificar_termino_glosario(
    id_glosario: int,
    id_termino: int,
    datos: ActualizarTerminoGlosarioSolicitud,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaTerminoGlosario:
    try:
        termino = actualizar_termino(
            sesion=sesion,
            id_usuario=usuario.id,
            id_glosario=id_glosario,
            id_termino=id_termino,
            datos=datos,
        )
    except ValueError as error:
        raise _error_http(error) from error

    return RespuestaTerminoGlosario(
        mensaje="Termino actualizado correctamente.",
        resultado=TerminoGlosarioDetalle.model_validate(termino),
    )


@enrutador.delete(
    "/{id_glosario}/terminos/{id_termino}",
    response_model=RespuestaEliminarGlosario,
    status_code=status.HTTP_200_OK,
    summary="Eliminar termino del glosario (requiere token)",
    responses={**RESPUESTAS_COMUNES, **RESPUESTA_404},
)
def eliminar_termino_glosario(
    id_glosario: int,
    id_termino: int,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaEliminarGlosario:
    try:
        eliminar_termino(
            sesion=sesion,
            id_usuario=usuario.id,
            id_glosario=id_glosario,
            id_termino=id_termino,
        )
    except ValueError as error:
        raise _error_http(error) from error

    return RespuestaEliminarGlosario(mensaje="Termino eliminado correctamente.")

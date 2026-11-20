from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.seguridad import requiere_token
from app.database.conexion import obtener_sesion
from app.models.usuario.usuario import Usuario
from app.schemas.aprendizaje import (
    CambiarAprendizajeSolicitud,
    EliminarCorreccionesResultado,
    ListaCorreccionesRespuesta,
    RegistrarCorreccionSolicitud,
    RespuestaCorreccion,
    RespuestaEliminarCorrecciones,
    RespuestaEstadoAprendizaje,
)
from app.services.aprendizaje import (
    CorreccionNoEncontradaError,
    armar_detalle_correccion,
    cambiar_estado,
    eliminar_correccion,
    eliminar_todas,
    listar_correcciones,
    obtener_estado,
    registrar_correccion,
)


enrutador = APIRouter(
    prefix="/aprendizaje",
    tags=["aprendizaje"],
    dependencies=[Depends(requiere_token)],
)

RESPUESTAS_COMUNES = {
    status.HTTP_401_UNAUTHORIZED: {"description": "El token es invalido, expiro o no fue enviado."},
}


def _error_http(error: ValueError) -> HTTPException:
    if isinstance(error, CorreccionNoEncontradaError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@enrutador.get(
    "",
    response_model=RespuestaEstadoAprendizaje,
    summary="Consultar el aprendizaje de preferencias (requiere token)",
    description="Indica si el aprendizaje esta activo y cuantas correcciones tiene registradas el usuario (HU-34).",
    responses=RESPUESTAS_COMUNES,
)
def consultar_aprendizaje(
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaEstadoAprendizaje:
    return RespuestaEstadoAprendizaje(
        mensaje="Estado del aprendizaje obtenido correctamente.",
        resultado=obtener_estado(sesion, usuario.id),
    )


@enrutador.patch(
    "",
    response_model=RespuestaEstadoAprendizaje,
    summary="Activar o desactivar el aprendizaje (requiere token)",
    description=(
        "Con el aprendizaje desactivado no se registran correcciones ni se aplican las existentes, "
        "pero tampoco se borran (HU-34)."
    ),
    responses=RESPUESTAS_COMUNES,
)
def modificar_aprendizaje(
    datos: CambiarAprendizajeSolicitud,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaEstadoAprendizaje:
    try:
        estado = cambiar_estado(sesion, usuario.id, datos.activo)
    except ValueError as error:
        raise _error_http(error) from error
    return RespuestaEstadoAprendizaje(
        mensaje="Aprendizaje activado." if estado.activo else "Aprendizaje desactivado.",
        resultado=estado,
    )


@enrutador.post(
    "/correcciones",
    response_model=RespuestaCorreccion,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar una correccion o alternativa elegida (requiere token)",
    description=(
        "Guarda el texto original, la traduccion generada, la version corregida (o la alternativa "
        "elegida, HU-18) y el par de idiomas. Si ya existe una para el mismo texto y par, se reemplaza. "
        "Con el aprendizaje desactivado no se guarda nada y 'resultado' es null."
    ),
    responses={
        **RESPUESTAS_COMUNES,
        status.HTTP_400_BAD_REQUEST: {"description": "Idioma inexistente."},
    },
)
def crear_correccion(
    datos: RegistrarCorreccionSolicitud,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaCorreccion:
    try:
        correccion = registrar_correccion(sesion, usuario.id, datos)
    except ValueError as error:
        raise _error_http(error) from error

    if correccion is None:
        return RespuestaCorreccion(
            mensaje="El aprendizaje esta desactivado; la correccion no se registro.",
            resultado=None,
        )
    return RespuestaCorreccion(
        mensaje="Correccion registrada. Se tendra en cuenta en tus siguientes traducciones.",
        resultado=armar_detalle_correccion(correccion),
    )


@enrutador.get(
    "/correcciones",
    response_model=ListaCorreccionesRespuesta,
    summary="Listar mis correcciones (requiere token)",
    description="Correcciones del usuario, de la mas reciente a la mas antigua; filtro opcional por idioma (codigo).",
    responses=RESPUESTAS_COMUNES,
)
def consultar_correcciones(
    idioma_origen: str | None = Query(default=None, max_length=10),
    idioma_destino: str | None = Query(default=None, max_length=10),
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> ListaCorreccionesRespuesta:
    try:
        correcciones = listar_correcciones(sesion, usuario.id, idioma_origen, idioma_destino)
    except ValueError as error:
        raise _error_http(error) from error
    return ListaCorreccionesRespuesta(
        mensaje="Correcciones obtenidas correctamente.",
        resultado=[armar_detalle_correccion(c) for c in correcciones],
    )


@enrutador.delete(
    "/correcciones/{id_correccion}",
    response_model=RespuestaEliminarCorrecciones,
    summary="Eliminar una correccion (requiere token)",
    responses={
        **RESPUESTAS_COMUNES,
        status.HTTP_404_NOT_FOUND: {"description": "La correccion no existe o no es del usuario."},
    },
)
def borrar_correccion(
    id_correccion: int,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaEliminarCorrecciones:
    try:
        eliminar_correccion(sesion, usuario.id, id_correccion)
    except ValueError as error:
        raise _error_http(error) from error
    return RespuestaEliminarCorrecciones(
        mensaje="Correccion eliminada correctamente.",
        resultado=EliminarCorreccionesResultado(eliminadas=1),
    )


@enrutador.delete(
    "/correcciones",
    response_model=RespuestaEliminarCorrecciones,
    summary="Eliminar todo lo aprendido (requiere token)",
    responses=RESPUESTAS_COMUNES,
)
def borrar_todas_las_correcciones(
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaEliminarCorrecciones:
    eliminadas = eliminar_todas(sesion, usuario.id)
    return RespuestaEliminarCorrecciones(
        mensaje="Se eliminaron todas tus correcciones.",
        resultado=EliminarCorreccionesResultado(eliminadas=eliminadas),
    )

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.seguridad import requiere_token
from app.database.conexion import obtener_sesion
from app.models.usuario.usuario import Usuario
from app.schemas.sesion_externa import (
    ActualizarSesionExternaSolicitud,
    AsignarParticipanteSolicitud,
    CrearParticipanteExternoSolicitud,
    CrearSesionExternaSolicitud,
    EstadoSesionExterna,
    IntervencionExternaRespuesta,
    ListaIntervencionesExternasRespuesta,
    ListaParticipantesExternosRespuesta,
    ListaSesionesExternasRespuesta,
    ParticipanteExternoRespuesta,
    RenombrarParticipanteExternoSolicitud,
    SesionExternaRespuesta,
    SincronizacionParticipantesRespuesta,
)
from app.services import intervenciones_externas as servicio_intervenciones
from app.services import sesiones_externas as servicio
from app.services.integraciones import ConexionNoVinculadaError
from app.services.intervenciones_externas import ServicioNoActivoError
from app.services.sesiones_externas import SesionExternaNoEncontradaError
from app.services.transcripcion import TranscripcionError

enrutador = APIRouter(
    prefix="/sesiones-externas",
    tags=["sesiones-externas"],
    dependencies=[Depends(requiere_token)],
)

RESPUESTAS = {
    status.HTTP_401_UNAUTHORIZED: {"description": "El token es invalido, expiro o no fue enviado."},
    status.HTTP_404_NOT_FOUND: {"description": "La sesion (o el elemento) no existe o no es del usuario."},
    status.HTTP_400_BAD_REQUEST: {"description": "Datos no validos o accion no permitida en el estado actual."},
}


def _error_http(error: Exception) -> HTTPException:
    if isinstance(error, SesionExternaNoEncontradaError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, ServicioNoActivoError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    if isinstance(error, ConexionNoVinculadaError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    if isinstance(error, TranscripcionError):
        return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


def _respuesta(sesion: Session, sesion_externa, mensaje: str) -> SesionExternaRespuesta:
    return SesionExternaRespuesta(mensaje=mensaje, resultado=servicio.detalle_con_total(sesion, sesion_externa))


# ---------------------------------------------------------------------------
# Sesiones (HU-36) y control del servicio (HU-41)
# ---------------------------------------------------------------------------


@enrutador.post(
    "",
    response_model=SesionExternaRespuesta,
    status_code=status.HTTP_201_CREATED,
    summary="Configurar una sesion externa (requiere token)",
    description=(
        "Crea la sesion en estado 'configurada' para una reunion de una plataforma vinculada. Valida "
        "que el enlace corresponda a la plataforma. Crea dos participantes genericos (HU-40)."
    ),
    responses={**RESPUESTAS, status.HTTP_409_CONFLICT: {"description": "Plataforma no vinculada o expirada."}},
)
def crear(
    datos: CrearSesionExternaSolicitud,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> SesionExternaRespuesta:
    try:
        nueva = servicio.crear_sesion_externa(sesion, usuario.id, datos)
    except ValueError as error:
        raise _error_http(error) from error
    return _respuesta(sesion, nueva, "Sesión externa configurada correctamente.")


@enrutador.get(
    "",
    response_model=ListaSesionesExternasRespuesta,
    summary="Historial de mis sesiones externas (requiere token)",
    responses=RESPUESTAS,
)
def listar(
    estado: EstadoSesionExterna | None = Query(default=None),
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> ListaSesionesExternasRespuesta:
    sesiones = servicio.listar_sesiones_externas(sesion, usuario.id, estado)
    totales = servicio.contar_intervenciones(sesion, [s.id_sesion_externa for s in sesiones])
    return ListaSesionesExternasRespuesta(
        mensaje="Sesiones externas obtenidas correctamente.",
        resultado=[servicio.armar_detalle_sesion(s, totales.get(s.id_sesion_externa, 0)) for s in sesiones],
    )


@enrutador.get("/{id_sesion_externa}", response_model=SesionExternaRespuesta, summary="Consultar una sesion externa", responses=RESPUESTAS)
def consultar(
    id_sesion_externa: int,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> SesionExternaRespuesta:
    try:
        encontrada = servicio.obtener_sesion_externa(sesion, usuario.id, id_sesion_externa)
    except ValueError as error:
        raise _error_http(error) from error
    return _respuesta(sesion, encontrada, "Sesión externa obtenida correctamente.")


@enrutador.patch(
    "/{id_sesion_externa}",
    response_model=SesionExternaRespuesta,
    summary="Modificar la configuracion antes o durante la reunion",
    description="Los cambios se aplican a las intervenciones siguientes. Enlace e idiomas solo antes de iniciar.",
    responses=RESPUESTAS,
)
def modificar(
    id_sesion_externa: int,
    datos: ActualizarSesionExternaSolicitud,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> SesionExternaRespuesta:
    try:
        actualizada = servicio.actualizar_sesion_externa(sesion, usuario.id, id_sesion_externa, datos)
    except ValueError as error:
        raise _error_http(error) from error
    return _respuesta(sesion, actualizada, "Configuración actualizada; se aplicará a las siguientes intervenciones.")


def _accion(nombre: str, funcion, mensaje: str):
    @enrutador.post(
        f"/{{id_sesion_externa}}/{nombre}",
        response_model=SesionExternaRespuesta,
        summary=f"{nombre.capitalize()} el servicio de traduccion (HU-41)",
        description="Solo cambia el servicio de traduccion; no afecta a la reunion en Meet o Zoom.",
        responses={**RESPUESTAS, status.HTTP_409_CONFLICT: {"description": "Plataforma no vinculada (al iniciar)."}},
        name=f"{nombre}_sesion_externa",
    )
    def _endpoint(
        id_sesion_externa: int,
        usuario: Usuario = Depends(requiere_token),
        sesion: Session = Depends(obtener_sesion),
    ) -> SesionExternaRespuesta:
        try:
            resultado = funcion(sesion, usuario.id, id_sesion_externa)
        except ValueError as error:
            raise _error_http(error) from error
        return _respuesta(sesion, resultado, mensaje)

    return _endpoint


_accion("iniciar", servicio.iniciar_servicio, "Servicio de traducción iniciado.")
_accion("pausar", servicio.pausar_servicio, "Servicio pausado: no se captura ni se traduce contenido.")
_accion("reanudar", servicio.reanudar_servicio, "Servicio reanudado con la misma configuración y contexto.")
_accion("finalizar", servicio.finalizar_servicio, "Servicio finalizado; la sesión quedó en tu historial.")


# ---------------------------------------------------------------------------
# Participantes (HU-40)
# ---------------------------------------------------------------------------


@enrutador.get("/{id_sesion_externa}/participantes", response_model=ListaParticipantesExternosRespuesta, summary="Participantes de la sesion", responses=RESPUESTAS)
def participantes(
    id_sesion_externa: int,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> ListaParticipantesExternosRespuesta:
    try:
        encontrada = servicio.obtener_sesion_externa(sesion, usuario.id, id_sesion_externa)
    except ValueError as error:
        raise _error_http(error) from error
    return ListaParticipantesExternosRespuesta(
        mensaje="Participantes obtenidos correctamente.",
        resultado=[servicio.armar_detalle_participante(p) for p in encontrada.participantes],
    )


@enrutador.post(
    "/{id_sesion_externa}/participantes",
    response_model=ParticipanteExternoRespuesta,
    status_code=status.HTTP_201_CREATED,
    summary="Agregar una etiqueta generica de participante",
    responses=RESPUESTAS,
)
def agregar_participante(
    id_sesion_externa: int,
    datos: CrearParticipanteExternoSolicitud,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> ParticipanteExternoRespuesta:
    try:
        nuevo = servicio.agregar_participante_generico(sesion, usuario.id, id_sesion_externa, datos.nombre)
    except ValueError as error:
        raise _error_http(error) from error
    return ParticipanteExternoRespuesta(mensaje="Participante agregado.", resultado=servicio.armar_detalle_participante(nuevo))


@enrutador.patch(
    "/{id_sesion_externa}/participantes/{id_participante}",
    response_model=ParticipanteExternoRespuesta,
    summary="Renombrar una etiqueta generica",
    responses=RESPUESTAS,
)
def renombrar_participante(
    id_sesion_externa: int,
    id_participante: int,
    datos: RenombrarParticipanteExternoSolicitud,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> ParticipanteExternoRespuesta:
    try:
        participante = servicio.renombrar_participante(sesion, usuario.id, id_sesion_externa, id_participante, datos.nombre)
    except ValueError as error:
        raise _error_http(error) from error
    return ParticipanteExternoRespuesta(
        mensaje="Participante renombrado.", resultado=servicio.armar_detalle_participante(participante)
    )


@enrutador.post(
    "/{id_sesion_externa}/participantes/sincronizar",
    response_model=SincronizacionParticipantesRespuesta,
    summary="Obtener los participantes desde la plataforma",
    description="Si la plataforma no los proporciona, responde 200 con 'disponible': false y un aviso.",
    responses={**RESPUESTAS, status.HTTP_409_CONFLICT: {"description": "Plataforma no vinculada."}},
)
def sincronizar(
    id_sesion_externa: int,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> SincronizacionParticipantesRespuesta:
    try:
        resultado = servicio.sincronizar_participantes(sesion, usuario.id, id_sesion_externa)
    except ValueError as error:
        raise _error_http(error) from error
    mensaje = (
        f"Se agregaron {resultado.agregados} participantes de la plataforma."
        if resultado.disponible
        else "La plataforma no proporcionó participantes."
    )
    return SincronizacionParticipantesRespuesta(mensaje=mensaje, resultado=resultado)


# ---------------------------------------------------------------------------
# Captura (HU-37) y traduccion (HU-38)
# ---------------------------------------------------------------------------


@enrutador.post(
    "/{id_sesion_externa}/audio",
    response_model=IntervencionExternaRespuesta,
    summary="Enviar un fragmento de audio de la reunion",
    description=(
        "Fragmento capturado en el navegador (multipart, campo 'audio', maximo 5 MB). Se transcribe con "
        "Whisper y se traduce. Sin voz responde 200 con 'resultado' null. Solo con el servicio activo: "
        "en pausa o finalizado responde 409 y descarta el fragmento. Si Whisper falla responde 502."
    ),
    responses={
        **RESPUESTAS,
        status.HTTP_409_CONFLICT: {"description": "El servicio no esta activo."},
        status.HTTP_502_BAD_GATEWAY: {"description": "No se pudo transcribir el audio."},
    },
)
def enviar_audio(
    id_sesion_externa: int,
    audio: UploadFile = File(...),
    id_participante: int | None = Form(default=None),
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> IntervencionExternaRespuesta:
    # Endpoint sincrono: FastAPI lo ejecuta en un hilo y no bloquea el servidor mientras transcribe
    contenido = audio.file.read(servicio_intervenciones.TAMANO_MAXIMO_AUDIO + 1)
    try:
        intervencion = servicio_intervenciones.procesar_audio(
            sesion=sesion,
            id_usuario=usuario.id,
            id_sesion_externa=id_sesion_externa,
            contenido=contenido,
            nombre_archivo=audio.filename or "fragmento.webm",
            tipo_contenido=audio.content_type or "",
            id_participante=id_participante,
        )
    except (ValueError, TranscripcionError) as error:
        raise _error_http(error) from error
    if intervencion is None:
        return IntervencionExternaRespuesta(mensaje="No se detectó voz en el fragmento.", resultado=None)
    mensaje = (
        "Intervención traducida." if intervencion.estado == "traducida" else "La intervención no se pudo traducir."
    )
    return IntervencionExternaRespuesta(
        mensaje=mensaje, resultado=servicio_intervenciones.armar_detalle_intervencion(intervencion)
    )


@enrutador.get(
    "/{id_sesion_externa}/intervenciones",
    response_model=ListaIntervencionesExternasRespuesta,
    summary="Intervenciones (subtitulos) de la sesion",
    description="En orden cronologico; con 'despues_de' solo las posteriores a esa intervencion.",
    responses=RESPUESTAS,
)
def intervenciones(
    id_sesion_externa: int,
    despues_de: int | None = Query(default=None),
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> ListaIntervencionesExternasRespuesta:
    try:
        lista = servicio_intervenciones.listar_intervenciones(sesion, usuario.id, id_sesion_externa, despues_de)
    except ValueError as error:
        raise _error_http(error) from error
    return ListaIntervencionesExternasRespuesta(
        mensaje="Intervenciones obtenidas correctamente.",
        resultado=[servicio_intervenciones.armar_detalle_intervencion(i) for i in lista],
    )


@enrutador.post(
    "/{id_sesion_externa}/intervenciones/{id_intervencion}/reintentar",
    response_model=IntervencionExternaRespuesta,
    summary="Volver a traducir una intervencion con error",
    responses={**RESPUESTAS, status.HTTP_409_CONFLICT: {"description": "El servicio no esta activo."}},
)
def reintentar(
    id_sesion_externa: int,
    id_intervencion: int,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> IntervencionExternaRespuesta:
    try:
        intervencion = servicio_intervenciones.reintentar_intervencion(sesion, usuario.id, id_sesion_externa, id_intervencion)
    except ValueError as error:
        raise _error_http(error) from error
    return IntervencionExternaRespuesta(
        mensaje="Reintento terminado.", resultado=servicio_intervenciones.armar_detalle_intervencion(intervencion)
    )


@enrutador.patch(
    "/{id_sesion_externa}/intervenciones/{id_intervencion}",
    response_model=IntervencionExternaRespuesta,
    summary="Indicar quien hablo en una intervencion (HU-40)",
    responses=RESPUESTAS,
)
def asignar_hablante(
    id_sesion_externa: int,
    id_intervencion: int,
    datos: AsignarParticipanteSolicitud,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> IntervencionExternaRespuesta:
    try:
        intervencion = servicio_intervenciones.asignar_participante(
            sesion, usuario.id, id_sesion_externa, id_intervencion, datos.id_participante
        )
    except ValueError as error:
        raise _error_http(error) from error
    return IntervencionExternaRespuesta(
        mensaje="Participante asignado.", resultado=servicio_intervenciones.armar_detalle_intervencion(intervencion)
    )

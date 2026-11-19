from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.seguridad import requiere_token
from app.database.conexion import obtener_sesion
from app.models.traduccion.configuracion_traduccion import ConfiguracionTraduccion
from app.models.traduccion.traduccion import Traduccion
from app.models.usuario.usuario import Usuario
from app.schemas.configuracion_traduccion import (
    GuardarConfiguracionTraduccionSolicitud,
    RespuestaConfiguracionTraduccion,
)
from app.schemas.contexto import (
    GuardarContextoSolicitud,
    ListaContextosRespuesta,
    RespuestaContexto,
)
from app.schemas.idioma import ListaIdiomasRespuesta
from app.schemas.tono import ListaTonosRespuesta
from app.schemas.traduccion import (
    FavoritoDetalle,
    RespuestaEliminarTraduccion,
    RespuestaFavorito,
    RespuestaHistorial,
    RespuestaRegistrarTraduccion,
    RespuestaTraduccion,
    SolicitudFavorito,
    SolicitudRegistrarTraduccion,
    SolicitudTraduccion,
    TraduccionRegistrada,
    TraduccionResultado,
)
from app.schemas.variante_regional import ListaVariantesRegionalesRespuesta
from app.services.configuracion_traduccion import (
    armar_detalle_configuracion,
    guardar_o_actualizar_configuracion,
    obtener_configuracion_usuario,
    resolver_configuracion_efectiva,
)
from app.services.contextos import guardar_nuevo_contexto, obtener_todos_contextos
from app.services.glosarios import GlosarioNoEncontradoError
from app.services.historial_traducciones import (
    buscar_traducciones_similares,
    registrar_traduccion,
    definir_favorito,
    eliminar_traduccion,
    listar_historial,
    obtener_traduccion_usuario,
)
from app.services.idiomas import obtener_todos_idiomas
from app.services.tonos import obtener_todos_tonos
from app.services.traduccion_contextual import traducir_con_configuracion
from app.services.variantes_regionales import obtener_todas_variantes_regionales


enrutador = APIRouter(
    prefix="/traducciones",
    tags=["traducciones"],
)


@enrutador.get(
    "/idiomas",
    response_model=ListaIdiomasRespuesta,
    status_code=status.HTTP_200_OK,
    summary="Listar idiomas disponibles para traduccion",
)
def listar_idiomas_traduccion(
    sesion: Session = Depends(obtener_sesion),
) -> ListaIdiomasRespuesta:
    idiomas = obtener_todos_idiomas(sesion)
    return ListaIdiomasRespuesta(
        mensaje="Idiomas obtenidos correctamente.",
        resultado=idiomas,
    )


@enrutador.get(
    "/contextos",
    response_model=ListaContextosRespuesta,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(requiere_token)],
    summary="Listar contextos disponibles para traduccion (requiere token)",
    description=(
        "Retorna la lista de contextos registrados en la tabla contexto. "
        "Requiere cabecera 'Authorization: Bearer <token>'."
    ),
)
def listar_contextos_traduccion(
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> ListaContextosRespuesta:
    contextos = obtener_todos_contextos(
        sesion=sesion,
        solo_activos=True,
        id_usuario=usuario.id,
    )
    return ListaContextosRespuesta(
        mensaje="Contextos obtenidos correctamente.",
        resultado=contextos,
    )


@enrutador.post(
    "/contextos",
    response_model=RespuestaContexto,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(requiere_token)],
    summary="Guardar contexto para traduccion (requiere token)",
    description=(
        "Crea y guarda un nuevo contexto personalizado en la tabla contexto. "
        "Requiere cabecera 'Authorization: Bearer <token>'."
    ),
)
def guardar_contexto_traduccion(
    datos: GuardarContextoSolicitud,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaContexto:
    try:
        nuevo_contexto = guardar_nuevo_contexto(
            sesion=sesion,
            nombre=datos.nombre,
            descripcion=datos.descripcion,
            id_usuario=usuario.id,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    return RespuestaContexto(
        mensaje="Contexto guardado correctamente.",
        resultado=nuevo_contexto,
    )


@enrutador.get(
    "/tonos",
    response_model=ListaTonosRespuesta,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(requiere_token)],
    summary="Listar tonos disponibles para traduccion (requiere token)",
    description=(
        "Retorna la lista de tonos registrados en la tabla tono. "
        "Requiere cabecera 'Authorization: Bearer <token>'."
    ),
)
def listar_tonos_traduccion(
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> ListaTonosRespuesta:
    tonos = obtener_todos_tonos(sesion=sesion, solo_activos=True)
    return ListaTonosRespuesta(
        mensaje="Tonos obtenidos correctamente.",
        resultado=tonos,
    )


@enrutador.get(
    "/variantes-regionales",
    response_model=ListaVariantesRegionalesRespuesta,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(requiere_token)],
    summary="Listar variantes regionales disponibles para traduccion (requiere token)",
    description=(
        "Retorna la lista de variantes regionales registradas en la tabla variante_regional. "
        "Requiere cabecera 'Authorization: Bearer <token>'."
    ),
)
def listar_variantes_regionales_traduccion(
    id_idioma: int | None = Query(
        default=None,
        description="Filtrar por id de idioma",
    ),
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> ListaVariantesRegionalesRespuesta:
    variantes = obtener_todas_variantes_regionales(
        sesion=sesion,
        id_idioma=id_idioma,
        solo_activos=True,
    )
    return ListaVariantesRegionalesRespuesta(
        mensaje="Variantes regionales obtenidas correctamente.",
        resultado=variantes,
    )


@enrutador.post(
    "/configuracion",
    response_model=RespuestaConfiguracionTraduccion,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(requiere_token)],
    summary="Guardar o actualizar configuracion de traduccion (requiere token)",
    description=(
        "Guarda o actualiza la configuracion de traduccion del usuario autenticado. "
        "Requiere cabecera 'Authorization: Bearer <token>'."
    ),
)
def guardar_configuracion_traduccion(
    datos: GuardarConfiguracionTraduccionSolicitud,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaConfiguracionTraduccion:
    try:
        config = guardar_o_actualizar_configuracion(
            sesion=sesion,
            id_usuario=usuario.id,
            id_contexto=datos.id_contexto,
            id_tono=datos.id_tono,
            id_variante_regional=datos.id_variante_regional,
            explicar_expresiones=datos.explicar_expresiones,
            generar_alternativas=datos.generar_alternativas,
            idioma_destino=datos.idioma_destino,
            id_glosario=datos.id_glosario,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    detalle = armar_detalle_configuracion(config=config, sesion=sesion)
    return RespuestaConfiguracionTraduccion(
        mensaje="Configuracion guardada correctamente.",
        resultado=detalle,
    )


@enrutador.get(
    "/configuracion",
    response_model=RespuestaConfiguracionTraduccion,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(requiere_token)],
    summary="Obtener configuracion de traduccion (requiere token)",
    description=(
        "Retorna la configuracion de traduccion del usuario autenticado. "
        "Requiere cabecera 'Authorization: Bearer <token>'."
    ),
)
def obtener_configuracion_traduccion_endpoint(
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaConfiguracionTraduccion:
    config = obtener_configuracion_usuario(sesion=sesion, id_usuario=usuario.id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El usuario no tiene una configuracion de traduccion registrada.",
        )

    detalle = armar_detalle_configuracion(config=config, sesion=sesion)
    return RespuestaConfiguracionTraduccion(
        mensaje="Configuracion obtenida correctamente.",
        resultado=detalle,
    )


@enrutador.post(
    "",
    response_model=RespuestaTraduccion,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(requiere_token)],
    summary="Traducir texto (requiere token)",
    description=(
        "Traduce un texto especificando idioma de destino e idioma de origen (opcional). "
        "Utiliza la configuracion de traduccion asociada al usuario autenticado. "
        "Si no se proporciona idioma de origen, se detecta automaticamente. "
        "Opcionalmente acepta 'id_glosario' para aplicar un glosario personalizado del "
        "mismo par de idiomas (traducciones preferidas y terminos a conservar). "
        "Requiere cabecera 'Authorization: Bearer <token>'."
    ),
)
@enrutador.post(
    "/contextual",
    response_model=RespuestaTraduccion,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def traducir(
    solicitud: SolicitudTraduccion,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaTraduccion:

    # 1. Obtener configuracion de traduccion del usuario autenticado
    config = sesion.scalar(
        select(ConfiguracionTraduccion).where(
            ConfiguracionTraduccion.id_usuario == usuario.id
        )
    )
    if not config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "El usuario no tiene una configuracion de traduccion registrada. "
                "Debe guardar su configuracion previamente."
            ),
        )

    # 2. Configuracion efectiva: la guardada, con los valores puntuales de la solicitud (HU-33).
    #    Los valores puntuales no modifican la configuracion guardada.
    try:
        efectiva = resolver_configuracion_efectiva(
            sesion=sesion,
            id_usuario=usuario.id,
            config=config,
            sobrescritos=solicitud.valores_sobrescritos(),
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    contexto_db = efectiva.contexto
    tono_db = efectiva.tono
    variante_db = efectiva.variante
    nombre_contexto = contexto_db.nombre if contexto_db else None
    nombre_tono = tono_db.nombre if tono_db else None
    nombre_variante = variante_db.nombre if variante_db else None

    # 3. Traduccion central: glosario, localizacion regional y enriquecimiento segun configuracion
    try:
        traduccion = traducir_con_configuracion(
            sesion=sesion,
            id_usuario=usuario.id,
            texto=solicitud.texto_origen,
            idioma_origen=solicitud.idioma_origen,
            idioma_destino=solicitud.idioma_destino,
            nombre_contexto=nombre_contexto,
            descripcion_contexto=contexto_db.descripcion if contexto_db else None,
            nombre_tono=nombre_tono,
            variante=variante_db,
            id_glosario=solicitud.id_glosario,
            generar_alternativas=efectiva.generar_alternativas,
            explicar_expresiones=efectiva.explicar_expresiones,
            analizar_contexto=contexto_db is not None,
        )
    except GlosarioNoEncontradoError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    glosario_usado = traduccion.glosario_usado
    enriquecimiento = traduccion.enriquecimiento

    # 4. Sugerencias del historial del usuario en el mismo par de idiomas (HU-44). Se buscan
    #    antes de guardar esta traduccion para no sugerirla a si misma; si falla, se omiten.
    sugerencias = []
    if traduccion.id_idioma_origen and traduccion.id_idioma_destino:
        try:
            sugerencias = buscar_traducciones_similares(
                sesion=sesion,
                id_usuario=usuario.id,
                texto=solicitud.texto_origen,
                id_idioma_origen=traduccion.id_idioma_origen,
                id_idioma_destino=traduccion.id_idioma_destino,
                excluir_traduccion=traduccion.traduccion,
            )
        except Exception:  # noqa: BLE001 - las sugerencias nunca deben impedir traducir
            sugerencias = []

    # 5. Guardar registro en la tabla traduccion si los idiomas existen en la base de datos
    #    (salvo que el cliente pida no guardarla, p. ej. la traduccion automatica al escribir)
    registro_traduccion = None
    if solicitud.guardar_en_historial and traduccion.id_idioma_origen and traduccion.id_idioma_destino:
        registro_traduccion = Traduccion(
            texto_original=solicitud.texto_origen,
            texto_traducido=traduccion.traduccion,
            id_configuracion_traduccion=config.id_configuracion_traduccion,
            id_idioma_origen=traduccion.id_idioma_origen,
            id_idioma_destino=traduccion.id_idioma_destino,
            id_usuario=usuario.id,
            id_glosario=glosario_usado.id_glosario if glosario_usado else None,
        )
        sesion.add(registro_traduccion)
        sesion.commit()

    return RespuestaTraduccion(
        mensaje="Traduccion realizada correctamente.",
        resultado=TraduccionResultado(
            id_traduccion=registro_traduccion.id_traduccion if registro_traduccion else None,
            texto_origen=traduccion.texto_origen,
            idioma_origen=traduccion.idioma_origen,
            idioma_destino=traduccion.idioma_destino,
            traduccion=traduccion.traduccion,
            confianza_deteccion=traduccion.confianza_deteccion,
            id_configuracion_traduccion=config.id_configuracion_traduccion,
            id_contexto=contexto_db.id_contexto if contexto_db else config.id_contexto,
            nombre_contexto=nombre_contexto,
            id_tono=tono_db.id_tono if tono_db else None,
            nombre_tono=nombre_tono,
            id_variante_regional=variante_db.id_variante_regional if variante_db else None,
            nombre_variante_regional=nombre_variante,
            region_aplicada=traduccion.region_aplicada,
            estado_region=traduccion.estado_region,
            explicar_expresiones=efectiva.explicar_expresiones,
            explicaciones_procesadas=efectiva.explicar_expresiones and enriquecimiento.procesado,
            generar_alternativas=efectiva.generar_alternativas,
            alternativas=enriquecimiento.resultado.alternativas,
            explicacion_expresiones=enriquecimiento.resultado.explicacion_expresiones,
            analisis_contextual=traduccion.analisis_contextual,
            id_glosario=glosario_usado.id_glosario if glosario_usado else None,
            nombre_glosario=glosario_usado.nombre if glosario_usado else None,
            terminos_glosario_aplicados=traduccion.terminos_glosario_aplicados,
            sugerencias=sugerencias,
        ),
    )


@enrutador.post(
    "/historial",
    response_model=RespuestaRegistrarTraduccion,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar una traduccion terminada en el historial (requiere token)",
    description=(
        "Guarda en el historial del usuario una traduccion ya realizada, sin volver a traducir. "
        "El cliente la usa cuando tradujo con 'guardar_en_historial: false' (traduccion automatica "
        "mientras se escribe) y el usuario termino. 'texto_traducido' es el resultado que el "
        "usuario uso (puede ser una alternativa o una sugerencia)."
    ),
)
def registrar_en_historial(
    datos: SolicitudRegistrarTraduccion,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaRegistrarTraduccion:
    try:
        registro = registrar_traduccion(
            sesion=sesion,
            id_usuario=usuario.id,
            texto_original=datos.texto_original,
            texto_traducido=datos.texto_traducido,
            codigo_idioma_origen=datos.idioma_origen,
            codigo_idioma_destino=datos.idioma_destino,
            id_glosario=datos.id_glosario,
        )
    except GlosarioNoEncontradoError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    return RespuestaRegistrarTraduccion(
        mensaje="Traduccion guardada en el historial.",
        resultado=TraduccionRegistrada(
            id_traduccion=registro.id_traduccion,
            fecha_creacion=registro.fecha_creacion,
        ),
    )


@enrutador.get(
    "/historial",
    response_model=RespuestaHistorial,
    status_code=status.HTTP_200_OK,
    summary="Historial de traducciones del usuario (requiere token)",
    description=(
        "Lista las traducciones del usuario autenticado. Todos los filtros son opcionales "
        "y se combinan (AND). fecha_hasta es inclusiva."
    ),
)
def obtener_historial(
    texto: str | None = Query(default=None, max_length=200),
    idioma_origen: str | None = Query(default=None, max_length=10),
    idioma_destino: str | None = Query(default=None, max_length=10),
    fecha_desde: date | None = Query(default=None),
    fecha_hasta: date | None = Query(default=None),
    solo_favoritos: bool = Query(default=False),
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaHistorial:
    try:
        historial = listar_historial(
            sesion,
            id_usuario=usuario.id,
            texto=texto,
            idioma_origen=idioma_origen,
            idioma_destino=idioma_destino,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            solo_favoritos=solo_favoritos,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    return RespuestaHistorial(
        mensaje="Historial obtenido correctamente.",
        resultado=historial,
    )


@enrutador.patch(
    "/{id_traduccion}/favorito",
    response_model=RespuestaFavorito,
    status_code=status.HTTP_200_OK,
    summary="Marcar o desmarcar traduccion como favorita (requiere token)",
)
def actualizar_favorito(
    id_traduccion: int,
    solicitud: SolicitudFavorito,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaFavorito:
    traduccion = obtener_traduccion_usuario(sesion, id_traduccion, usuario.id)
    if not traduccion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Traduccion no encontrada.",
        )

    traduccion = definir_favorito(sesion, traduccion, solicitud.favorito)
    mensaje = (
        "Traduccion marcada como favorita."
        if traduccion.favorito
        else "Traduccion retirada de favoritos."
    )
    return RespuestaFavorito(
        mensaje=mensaje,
        resultado=FavoritoDetalle(
            id_traduccion=traduccion.id_traduccion,
            favorito=traduccion.favorito,
        ),
    )


@enrutador.delete(
    "/{id_traduccion}",
    response_model=RespuestaEliminarTraduccion,
    status_code=status.HTTP_200_OK,
    summary="Eliminar traduccion del historial (requiere token)",
)
def eliminar_traduccion_historial(
    id_traduccion: int,
    usuario: Usuario = Depends(requiere_token),
    sesion: Session = Depends(obtener_sesion),
) -> RespuestaEliminarTraduccion:
    traduccion = obtener_traduccion_usuario(sesion, id_traduccion, usuario.id)
    if not traduccion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Traduccion no encontrada.",
        )

    eliminar_traduccion(sesion, traduccion)
    return RespuestaEliminarTraduccion(mensaje="Traduccion eliminada del historial.")

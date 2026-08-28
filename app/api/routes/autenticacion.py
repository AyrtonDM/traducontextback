from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session

from app.database.conexion import obtener_sesion
from app.schemas.autenticacion import (
    LoginSolicitud,
    LoginRespuesta,
    LoginResultado,
    LogoutRespuesta,
    RestablecerContrasenaSolicitud,
    RestablecerContrasenaRespuesta,
    SolicitarRecuperacionSolicitud,
    SolicitarRecuperacionRespuesta,
    ValidarCodigoRecuperacionSolicitud,
    ValidarCodigoRecuperacionRespuesta,
)
from app.services.autenticacion import (
    iniciar_sesion,
    cerrar_sesion,
    CredencialesInvalidasError,
    UsuarioInactivoError,
    SesionInvalidaError,
    solicitar_recuperacion,
    restablecer_contrasena,
    validar_codigo_recuperacion,
    CodigoRecuperacionInvalidoError,
)
from app.utilities.correo import CorreoNoConfiguradoError, EnvioCorreoError

enrutador = APIRouter(prefix="/autenticacion", tags=["autenticacion"])


@enrutador.post(
    "/iniciar-sesion",
    response_model=LoginRespuesta,
    status_code=status.HTTP_200_OK,
    summary="Iniciar sesion",
    description=(
        "Valida el correo y la contrasena, cierra las sesiones activas "
        "anteriores y devuelve un token con una vigencia de 7 dias."
    ),
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Las credenciales son invalidas."
        },
        status.HTTP_403_FORBIDDEN: {
            "description": "La cuenta del usuario no esta activa."
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Los datos enviados no cumplen el formato requerido."
        },
    },
)
def login(
    datos: LoginSolicitud,
    sesion_db: Session = Depends(obtener_sesion),
) -> LoginRespuesta:
    try:
        sesion = iniciar_sesion(sesion_db, datos)
    except CredencialesInvalidasError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
        ) from error
    except UsuarioInactivoError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(error),
        ) from error

    return LoginRespuesta(
        mensaje="Ayrton te dio acceso",
        resultado=[
            LoginResultado(token=sesion.token)
        ],
    )


@enrutador.post(
    "/cerrar-sesion",
    response_model=LogoutRespuesta,
    status_code=status.HTTP_200_OK,
    summary="Cerrar sesion",
    description="Cierra la sesion activa asociada al token Bearer enviado.",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "description": "El encabezado Authorization tiene un formato invalido."
        },
        status.HTTP_401_UNAUTHORIZED: {
            "description": "El token es invalido o la sesion ya fue cerrada."
        },
    },
)
def logout(
    authorization: str = Header(..., description="Token de autorizacion (Bearer <token>)"),
    sesion_db: Session = Depends(obtener_sesion),
) -> LogoutRespuesta:
    try:
        # Extraer token del encabezado Authorization: Bearer <token>
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato del encabezado Authorization debe ser 'Bearer <token>'.",
            )
        token = authorization.split(" ")[1]
        cerrar_sesion(sesion_db, token)
    except SesionInvalidaError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
        ) from error

    return LogoutRespuesta(
        mensaje="Sesion cerrada correctamente.",
        resultado=None,
    )


@enrutador.post(
    "/solicitar-recuperacion",
    response_model=SolicitarRecuperacionRespuesta,
    summary="Solicitar recuperacion de contrasena",
    description="Envia un codigo de recuperacion al correo de una cuenta activa.",
    responses={
        status.HTTP_502_BAD_GATEWAY: {
            "description": "No fue posible enviar el correo."
        },
    },
)
def solicitar_codigo_recuperacion(
    datos: SolicitarRecuperacionSolicitud,
    sesion_db: Session = Depends(obtener_sesion),
) -> SolicitarRecuperacionRespuesta:
    try:
        solicitar_recuperacion(sesion_db, datos)
    except (CorreoNoConfiguradoError, EnvioCorreoError) as error:
        sesion_db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"No se pudo enviar el correo de recuperacion: {error}",
        ) from error

    return SolicitarRecuperacionRespuesta(
        mensaje=(
            "Si el correo corresponde a una cuenta activa, "
            "recibiras un codigo de recuperacion."
        )
    )

@enrutador.post(
    "/validar-codigo-recuperacion",
    response_model=ValidarCodigoRecuperacionRespuesta,
    summary="Validar codigo de recuperacion",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "description": "El codigo es invalido o ha expirado."
        },
    },
)
def validar_codigo_recuperacion_usuario(
    datos: ValidarCodigoRecuperacionSolicitud,
    sesion_db: Session = Depends(obtener_sesion),
) -> ValidarCodigoRecuperacionRespuesta:
    try:
        validar_codigo_recuperacion(sesion_db, datos)
    except CodigoRecuperacionInvalidoError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    return ValidarCodigoRecuperacionRespuesta(
        mensaje="Codigo de recuperacion valido.",
    )

@enrutador.post(
    "/restablecer-contrasena",
    response_model=RestablecerContrasenaRespuesta,
    summary="Restablecer contrasena",
    description="Cambia la contrasena usando un codigo vigente de recuperacion.",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "description": "El codigo es invalido o ha expirado."
        },
    },
)
def restablecer_contrasena_usuario(
    datos: RestablecerContrasenaSolicitud,
    sesion_db: Session = Depends(obtener_sesion),
) -> RestablecerContrasenaRespuesta:
    try:
        restablecer_contrasena(sesion_db, datos)
    except CodigoRecuperacionInvalidoError as error:
        sesion_db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    return RestablecerContrasenaRespuesta(
        mensaje="Contrasena restablecida correctamente.",
    )

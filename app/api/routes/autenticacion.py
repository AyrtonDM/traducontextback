from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session

from app.database.conexion import obtener_sesion
from app.schemas.autenticacion import (
    LoginSolicitud,
    LoginRespuesta,
    LoginResultado,
    LogoutRespuesta,
)
from app.services.autenticacion import (
    iniciar_sesion,
    cerrar_sesion,
    CredencialesInvalidasError,
    UsuarioInactivoError,
    SesionInvalidaError,
)

enrutador = APIRouter(prefix="/autenticacion", tags=["autenticacion"])


@enrutador.post(
    "/iniciar-sesion",
    response_model=LoginRespuesta,
    status_code=status.HTTP_200_OK,
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

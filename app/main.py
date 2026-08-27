from fastapi import FastAPI

from app.api.routes.autenticacion import enrutador as enrutador_autenticacion
from app.core.configuracion import configuracion

app = FastAPI(
    title=configuracion.app_name,
    description="API para autenticacion de usuarios de TraduContext.",
    version="1.0.0",
    openapi_tags=[
        {
            "name": "autenticacion",
            "description": "Inicio y cierre de sesiones de usuario.",
        }
    ],
)

app.include_router(
    enrutador_autenticacion,
    prefix=configuracion.api_v1_prefix,
)


@app.get("/")
def inicio():
    return {
        "mensaje": "Backend funcionando",
        "resultado": None,
    }

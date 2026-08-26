from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.rutas import enrutador
from app.core.configuracion import configuracion
from app.database.inicializacion import inicializar_base_datos


@asynccontextmanager
async def lifespan(_: FastAPI):
    inicializar_base_datos()
    yield


app = FastAPI(title=configuracion.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(enrutador, prefix=configuracion.api_v1_prefix)


@app.get("/")
def inicio():
    return {
        "mensaje": "Backend funcionando"
    }

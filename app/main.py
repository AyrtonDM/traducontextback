from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.rutas import enrutador
from app.core.configuracion import RUTA_BASE, configuracion
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
    # Permite al front leer el nombre de los archivos descargados (exportacion de reportes, HU-48)
    expose_headers=["Content-Disposition"],
)

app.include_router(enrutador, prefix=configuracion.api_v1_prefix)

# Servir archivos estaticos de documentos para acceso/descarga directa
carpeta_documentos = RUTA_BASE / "documentos"
carpeta_documentos.mkdir(parents=True, exist_ok=True)
(carpeta_documentos / "original").mkdir(parents=True, exist_ok=True)
(carpeta_documentos / "traducido").mkdir(parents=True, exist_ok=True)

app.mount(
    "/documentos",
    StaticFiles(directory=str(carpeta_documentos)),
    name="documentos",
)


@app.exception_handler(StarletteHTTPException)
async def manejar_error_http(_, error: StarletteHTTPException):
    return JSONResponse(
        status_code=error.status_code,
        content={
            "mensaje": str(error.detail),
            "resultado": None,
        },
    )


@app.exception_handler(RequestValidationError)
async def manejar_error_validacion(_, error: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "mensaje": "Datos invalidos.",
            "resultado": jsonable_encoder(error.errors()),
        },
    )


@app.get("/")
def inicio():
    return {
        "mensaje": "Backend funcionando",
        "resultado": None,
    }

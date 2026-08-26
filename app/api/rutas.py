from fastapi import APIRouter

from app.api.routes import enrutador_usuarios

enrutador = APIRouter()
enrutador.include_router(enrutador_usuarios)

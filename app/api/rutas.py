from fastapi import APIRouter

from app.api.routes.usuarios import enrutador as enrutador_usuarios
from app.api.routes.autenticacion import enrutador as enrutador_autenticacion

enrutador = APIRouter()
enrutador.include_router(enrutador_usuarios)
enrutador.include_router(enrutador_autenticacion)

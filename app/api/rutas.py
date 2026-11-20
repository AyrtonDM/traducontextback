from fastapi import APIRouter

from app.api.routes.usuarios import enrutador as enrutador_usuarios
from app.api.routes.autenticacion import enrutador as enrutador_autenticacion
from app.api.routes.traducciones import enrutador as enrutador_traducciones
from app.api.routes.idiomas import enrutador as enrutador_idiomas
from app.api.routes.contextos import enrutador as enrutador_contextos
from app.api.routes.tonos import enrutador as enrutador_tonos
from app.api.routes.variantes_regionales import enrutador as enrutador_variantes_regionales
from app.api.routes.configuracion_traduccion import (
    enrutador as enrutador_configuracion_traduccion,
)
from app.api.routes.perfil import enrutador as enrutador_perfil
from app.api.routes.documentos import enrutador as enrutador_documentos
from app.api.routes.glosarios import enrutador as enrutador_glosarios
from app.api.routes.dashboard import enrutador as enrutador_dashboard
from app.api.routes.reportes import enrutador as enrutador_reportes
from app.api.routes.entornos import enrutador as enrutador_entornos
from app.api.routes.conversaciones import enrutador as enrutador_conversaciones
from app.api.routes.intervenciones import enrutador as enrutador_intervenciones
from app.api.routes.aprendizaje import enrutador as enrutador_aprendizaje
from app.api.routes.integraciones import enrutador as enrutador_integraciones
from app.api.routes.sesiones_externas import enrutador as enrutador_sesiones_externas
from app.api.routes.dispositivos import enrutador as enrutador_dispositivos
from app.api.routes.notificaciones import enrutador as enrutador_notificaciones

enrutador = APIRouter()
enrutador.include_router(enrutador_usuarios)
enrutador.include_router(enrutador_autenticacion)
enrutador.include_router(enrutador_traducciones)
enrutador.include_router(enrutador_idiomas)
enrutador.include_router(enrutador_contextos)
enrutador.include_router(enrutador_tonos)
enrutador.include_router(enrutador_variantes_regionales)
enrutador.include_router(enrutador_configuracion_traduccion)
enrutador.include_router(enrutador_perfil)
enrutador.include_router(enrutador_documentos)
enrutador.include_router(enrutador_glosarios)
enrutador.include_router(enrutador_entornos)
enrutador.include_router(enrutador_conversaciones)
enrutador.include_router(enrutador_intervenciones)
enrutador.include_router(enrutador_dashboard)
enrutador.include_router(enrutador_reportes)
enrutador.include_router(enrutador_aprendizaje)
enrutador.include_router(enrutador_integraciones)
enrutador.include_router(enrutador_sesiones_externas)
enrutador.include_router(enrutador_dispositivos)
enrutador.include_router(enrutador_notificaciones)

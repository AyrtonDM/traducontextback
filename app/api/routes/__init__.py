from app.api.routes.autenticacion import enrutador as enrutador_autenticacion
from app.api.routes.traducciones import enrutador as enrutador_traducciones
from app.api.routes.usuarios import enrutador as enrutador_usuarios


__all__ = [
    "enrutador_autenticacion",
    "enrutador_traducciones",
    "enrutador_usuarios",
]
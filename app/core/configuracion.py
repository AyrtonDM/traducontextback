from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


RUTA_BASE = Path(__file__).resolve().parents[2]


class Configuracion(BaseSettings):
    """Variables de configuracion del backend."""

    app_name: str
    environment: str
    api_v1_prefix: str

    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    db_echo: bool

    gmail_host: str
    gmail_port: int
    gmail_usuario: str
    gmail_password: str
    gmail_remitente: str
    openai_api_key: str

    # Integraciones con Google Meet y Zoom (HU-35 a HU-41). Todas son opcionales: sin ellas la
    # plataforma correspondiente se muestra como "no configurada" y no se puede vincular.
    # Clave Fernet (base64 de 32 bytes) para cifrar los tokens OAuth guardados en la base de datos.
    # Generarla con: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    clave_cifrado_tokens: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = ""
    zoom_client_id: str = ""
    zoom_client_secret: str = ""
    zoom_redirect_uri: str = ""
    # A donde vuelve el navegador al terminar la autorizacion OAuth
    frontend_url: str = "http://localhost:4200"

    model_config = SettingsConfigDict(
        env_file=RUTA_BASE / ".env",
        env_file_encoding="utf-8-sig",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def obtener_configuracion() -> Configuracion:
    return Configuracion()


configuracion = obtener_configuracion()

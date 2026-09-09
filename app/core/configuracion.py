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

    model_config = SettingsConfigDict(
        env_file=RUTA_BASE / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def obtener_configuracion() -> Configuracion:
    return Configuracion()


configuracion = obtener_configuracion()

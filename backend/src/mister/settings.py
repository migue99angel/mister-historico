"""Configuración de la aplicación leída de variables de entorno.

Vive fuera de cualquier capa `domain`: pydantic-settings es una dependencia de framework.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(frozen=True)

    database_url: str = "postgresql+psycopg://mister:mister@localhost:5432/mister"

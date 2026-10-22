"""Application settings read from environment variables.

Lives outside every `domain` layer: pydantic-settings is a framework dependency.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(frozen=True)

    database_url: str = "postgresql+psycopg://mister:mister@localhost:5432/mister"

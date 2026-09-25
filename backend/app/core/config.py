from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "LocalForge AI"
    environment: str = "development"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    ollama_base_url: str = Field(
        default="http://127.0.0.1:11434",
        validation_alias=AliasChoices("OLLAMA_BASE_URL", "LOCALFORGE_OLLAMA_BASE_URL"),
    )
    ollama_model: str = Field(
        default="",
        validation_alias=AliasChoices("OLLAMA_MODEL", "LOCALFORGE_OLLAMA_MODEL"),
    )
    database_url: str = "sqlite:///./data/localforge.db"
    ollama_timeout_seconds: float = 120.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

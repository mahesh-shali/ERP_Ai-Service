from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = ROOT.parent
CURRENT_WORKING_DIRECTORY = Path.cwd()

ENV_FILES = [
    CURRENT_WORKING_DIRECTORY / ".env",
    CURRENT_WORKING_DIRECTORY / ".env.development",
    WORKSPACE_ROOT / "Erp.Api" / ".env",
    WORKSPACE_ROOT / "Erp.Api" / ".env.development",
    ROOT / ".env",
    ROOT / ".env.development",
]

for env_file in ENV_FILES:
    load_dotenv(env_file, override=True)


class Settings(BaseSettings):
    database_url: str = Field(
        default="",
        validation_alias=AliasChoices("DATABASE_URL", "database_url"),
    )
    connectionstrings__defaultconnection: str = Field(
        default="",
        validation_alias=AliasChoices("ConnectionStrings__DefaultConnection", "connectionstrings__defaultconnection"),
    )
    openai_api_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "OPENAI_API_KEY",
            "OpenAI__ApiKey",
            "OPENAI__APIKEY",
            "OPENAI__API_KEY",
            "openai_api_key",
        ),
    )
    openai_model: str = Field(
        default="gpt-4.1-mini",
        validation_alias=AliasChoices("OPENAI_MODEL", "OpenAI__Model", "openai_model"),
    )
    groq_api_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "GROQ_API_KEY",
            "Groq__ApiKey",
            "GROQ__APIKEY",
            "GROQ__API_KEY",
            "GROQ_APIKEY",
            "groq_api_key",
        ),
    )
    groq_model: str = Field(
        default="llama-3.3-70b-versatile",
        validation_alias=AliasChoices("GROQ_MODEL", "Groq__Model", "groq_model"),
    )
    ai_service_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("AI_SERVICE_API_KEY", "AiService__ApiKey", "ai_service_api_key"),
    )
    allowed_origins: str = "http://localhost:3000"
    max_result_rows: int = 50
    redis_url: str = ""
    schema_cache_seconds: int = 600
    query_cache_seconds: int = 60

    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def postgres_url(self) -> str:
        return self.database_url or self.connectionstrings__defaultconnection

    @property
    def llm_configured(self) -> bool:
        return bool(self.groq_api_key or self.openai_api_key)

    @property
    def llm_provider(self) -> str:
        if self.groq_api_key:
            return "groq"
        if self.openai_api_key:
            return "openai"
        return "none"

    @property
    def llm_model(self) -> str:
        return self.groq_model if self.groq_api_key else self.openai_model

    @property
    def loaded_env_files(self) -> list[str]:
        return [str(path) for path in ENV_FILES if path.exists()]

    @property
    def checked_env_files(self) -> list[str]:
        return [str(path) for path in ENV_FILES]


@lru_cache
def get_settings() -> Settings:
    return Settings()

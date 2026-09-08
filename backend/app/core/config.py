from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Operations Agent"
    database_url: str = "sqlite:///./gemini_ops.db"  # Defaults to local SQLite if MySQL URL is not provided in .env
    frontend_url: str = "http://localhost:5173"

    # OpenAI Settings (default: gpt-4o-mini, the most cost-efficient reasoning model)
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = 0.1
    openai_timeout_seconds: float = 30.0

    # Fallback / compatibility settings
    gemini_api_key: str | None = None

    default_operator_email: str = "admin@opsagent.local"
    max_plan_steps: int = 12
    max_tool_retries: int = 2
    max_pending_actions: int = 50

    # LangGraph Observe Standalone Server Integration
    observe_server_url: str = "http://localhost:8765"
    observe_project: str = "ai-operations-agent"
    observe_environment: str = "development"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    database_url: str
    redis_url: str
    log_level: str = "INFO"
    queue_key: str = "queue:agent-jobs"

    openai_api_key: str | None = None
    openai_model: str = "gpt-5-nano"

    latex_service_url: str = "http://backend:8000/api/v1/internal"
    internal_compile_token: str = ""
    templates_base_dir: str = "/app/templates"
    artifacts_dir: str = "/data/artifacts"


settings = Settings()  # type: ignore[call-arg]


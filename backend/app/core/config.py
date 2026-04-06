from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    app_name: str = "resume-agent-backend"
    log_level: str = "INFO"

    database_url: str
    redis_url: str

    openai_api_key: str | None = None
    openai_model: str = "gpt-5-nano"

    internal_compile_token: str = ""

    # Shared with worker via volume; PDFs served from absolute paths stored in DB
    artifacts_dir: str = "/data/artifacts"


settings = Settings()  # type: ignore[call-arg]


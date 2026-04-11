from pydantic import BaseModel, ConfigDict, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseModel):
    """Process name and logging."""

    model_config = ConfigDict(frozen=True)

    app_name: str
    log_level: str


class DatabaseSettings(BaseModel):
    """Postgres / SQLAlchemy connection."""

    model_config = ConfigDict(frozen=True)

    url: str


class RedisSettings(BaseModel):
    """Redis connection and the background job queue list key."""

    model_config = ConfigDict(frozen=True)

    url: str
    queue_key: str


class OpenAISettings(BaseModel):
    """API keys, default model, and LLM/agent limits (chat, extract, tools)."""

    model_config = ConfigDict(frozen=True)

    api_key: str | None
    model: str
    resume_extract_max_input_chars: int
    agent_chat_max_turns: int
    agent_render_max_turns: int
    agent_resume_overview_max_chars: int
    agent_resume_excerpt_max_chars: int
    agent_jd_tool_max_chars: int
    agent_resume_search_max_scan_chars: int


class StorageSettings(BaseModel):
    """Uploaded resumes and compiled PDF artifacts on disk."""

    model_config = ConfigDict(frozen=True)

    artifacts_dir: str
    resume_uploads_dir: str
    resume_upload_max_bytes: int


class InternalSettings(BaseModel):
    """Worker → backend LaTeX compile route and shared secret."""

    model_config = ConfigDict(frozen=True)

    latex_service_url: str
    compile_token: str


class Settings(BaseSettings):
    """Loads the same env vars as before; use nested scopes for clearer grouping."""

    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    app_name: str = "resume-agent-backend"
    log_level: str = "INFO"
    log_json_format: bool = False
    log_access_logger_name: str = "app.access"

    database_url: str
    redis_url: str

    queue_key: str = "queue:agent-jobs"

    openai_api_key: str | None = None
    openai_model: str = "gpt-5-nano"

    internal_compile_token: str = ""

    latex_service_url: str = "http://backend:8000/api/v1/internal"

    artifacts_dir: str = "/data/artifacts"

    resume_uploads_dir: str = "/data/resume-uploads"
    resume_upload_max_bytes: int = 10 * 1024 * 1024

    resume_extract_max_input_chars: int = 24000

    agent_chat_max_turns: int = 12
    agent_render_max_turns: int = 20
    agent_resume_overview_max_chars: int = 2500
    agent_resume_excerpt_max_chars: int = 4000
    agent_jd_tool_max_chars: int = 8000
    agent_resume_search_max_scan_chars: int = 50000

    @computed_field
    @property
    def app(self) -> AppSettings:
        return AppSettings(app_name=self.app_name, log_level=self.log_level)

    @computed_field
    @property
    def database(self) -> DatabaseSettings:
        return DatabaseSettings(url=self.database_url)

    @computed_field
    @property
    def redis(self) -> RedisSettings:
        return RedisSettings(url=self.redis_url, queue_key=self.queue_key)

    @computed_field
    @property
    def openai(self) -> OpenAISettings:
        return OpenAISettings(
            api_key=self.openai_api_key,
            model=self.openai_model,
            resume_extract_max_input_chars=self.resume_extract_max_input_chars,
            agent_chat_max_turns=self.agent_chat_max_turns,
            agent_render_max_turns=self.agent_render_max_turns,
            agent_resume_overview_max_chars=self.agent_resume_overview_max_chars,
            agent_resume_excerpt_max_chars=self.agent_resume_excerpt_max_chars,
            agent_jd_tool_max_chars=self.agent_jd_tool_max_chars,
            agent_resume_search_max_scan_chars=self.agent_resume_search_max_scan_chars,
        )

    @computed_field
    @property
    def storage(self) -> StorageSettings:
        return StorageSettings(
            artifacts_dir=self.artifacts_dir,
            resume_uploads_dir=self.resume_uploads_dir,
            resume_upload_max_bytes=self.resume_upload_max_bytes,
        )

    @computed_field
    @property
    def internal(self) -> InternalSettings:
        return InternalSettings(
            latex_service_url=self.latex_service_url,
            compile_token=self.internal_compile_token,
        )


settings = Settings()  # type: ignore[call-arg]

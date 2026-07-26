from pathlib import Path
 
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
 
 
API_ROOT = Path(__file__).resolve().parents[2]
 
 
class Settings(BaseSettings):
    """
    All values are injected via environment variables / k8s Secrets.
    See .env.example for the full list.
    """
    model_config = SettingsConfigDict(
        env_file=str(API_ROOT / ".env"),
        extra="ignore",
        case_sensitive=False,
    )
 
    clerk_issuer: str = Field(
        validation_alias=AliasChoices(
            "CLERK_ISSUER",
            "CLERK_FRONTEND_API_URL",
        )
    )
 
    clerk_secret_key: str = Field(validation_alias=AliasChoices("CLERK_SECRET_KEY"))
 
    cors_origins: str = Field(
        default=(
            "http://localhost:3000,"
            "https://nyc-r2-web.vercel.app"
        ),
        validation_alias=AliasChoices("CORS_ORIGINS", "cors_origins"),
    )
 
    database_url: str = Field(validation_alias=AliasChoices("DATABASE_URL"))
 
   
    db_pool_size: int = Field(
        default=5,
        validation_alias=AliasChoices("DB_POOL_SIZE", "db_pool_size"),
    )
    db_max_overflow: int = Field(
        default=5,
        validation_alias=AliasChoices("DB_MAX_OVERFLOW", "db_max_overflow"),
    )
    db_echo: bool = Field(
        default=False,
        validation_alias=AliasChoices("DB_ECHO", "db_echo"),
    )
    # Vertex AI / Gemini settings. The API can still start without a project
    # configured; the analysis endpoint returns a clear 503 until it is set.
    google_cloud_project: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GOOGLE_CLOUD_PROJECT", "GCP_PROJECT_ID"),
    )
    google_cloud_location: str = Field(
        default="us-central1",
        validation_alias=AliasChoices("GOOGLE_CLOUD_LOCATION", "VERTEX_LOCATION"),
    )
    gemini_model_id: str = Field(
        default="gemini-2.5-flash",
        validation_alias=AliasChoices("GEMINI_MODEL_ID", "GEMINI_MODEL"),
    )
    gemini_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    )
    vertex_timeout_seconds: float = Field(
        default=90.0,
        gt=0,
        validation_alias=AliasChoices("VERTEX_TIMEOUT_SECONDS"),
    )
    vertex_retry_count: int = Field(
        default=2,
        ge=0,
        le=5,
        validation_alias=AliasChoices("VERTEX_RETRY_COUNT"),
    )
    max_audio_bytes: int = Field(
        default=30 * 1024 * 1024,
        gt=0,
        validation_alias=AliasChoices("MAX_AUDIO_BYTES"),
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
 
    @property
    def async_database_url(self) -> str:
        """Normalize any postgres:// / postgresql:// URL to the asyncpg driver."""
        url = self.database_url
        if url.startswith("postgresql+asyncpg://"):
            return url
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url
 
 
settings = Settings()

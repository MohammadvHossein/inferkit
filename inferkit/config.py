from functools import lru_cache
from typing import Any

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="InferKit", validation_alias=AliasChoices("INFERKIT_APP_NAME", "APP_NAME"))
    host: str = Field(default="0.0.0.0", validation_alias=AliasChoices("INFERKIT_HOST", "HOST"))
    port: int = Field(default=8000, validation_alias=AliasChoices("INFERKIT_PORT", "PORT"))
    api_prefix: str = Field(default="/api/v1", validation_alias=AliasChoices("INFERKIT_API_PREFIX", "API_PREFIX"))
    cors_origins: Any = Field(default=["*"], validation_alias=AliasChoices("INFERKIT_CORS_ORIGINS", "CORS_ORIGINS"))
    max_upload_mb: int = Field(default=50, validation_alias=AliasChoices("INFERKIT_MAX_UPLOAD_MB", "MAX_UPLOAD_MB"))
    rate_limit: str = Field(default="60/minute", validation_alias=AliasChoices("INFERKIT_RATE_LIMIT", "RATE_LIMIT"))
    debug: bool = Field(default=False, validation_alias=AliasChoices("INFERKIT_DEBUG", "DEBUG"))
    api_key: str | None = Field(default=None, validation_alias=AliasChoices("INFERKIT_API_KEY", "API_KEY"))
    enable_multipart: bool = Field(default=True, validation_alias=AliasChoices("INFERKIT_ENABLE_MULTIPART", "ENABLE_MULTIPART"))
    enable_json: bool = Field(default=True, validation_alias=AliasChoices("INFERKIT_ENABLE_JSON", "ENABLE_JSON"))
    enable_stream: bool = Field(default=True, validation_alias=AliasChoices("INFERKIT_ENABLE_STREAM", "ENABLE_STREAM"))
    enable_ws: bool = Field(default=True, validation_alias=AliasChoices("INFERKIT_ENABLE_WS", "ENABLE_WS"))

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors(cls, v: Any) -> list[str]:
        if v is None or v == "":
            return ["*"]
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        if isinstance(v, str):
            s = v.strip()
            if s == "*":
                return ["*"]
            if s.startswith("["):
                import json

                try:
                    parsed = json.loads(s)
                    if isinstance(parsed, list):
                        return [str(x).strip() for x in parsed if str(x).strip()]
                except Exception:
                    pass
            return [x.strip() for x in s.split(",") if x.strip()]
        return ["*"]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

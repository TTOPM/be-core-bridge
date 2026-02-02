from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    # Demo limits (public)
    DEMO_MAX_LYRICS_CHARS: int = Field(default=80)
    DEMO_ALLOWED_SECONDS: tuple[int, ...] = Field(default=(3, 5))
    DEMO_DEFAULT_SECONDS: int = Field(default=5)

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: str = Field(default="3/minute")   # per-IP
    RATE_LIMIT_PER_HOUR: str = Field(default="30/hour")      # per-IP
    GLOBAL_CONCURRENCY: int = Field(default=4)               # process-level

    # If set, the demo becomes a proxy to your INTERNAL singing service (private)
    # without exposing those details to the public.
    BELEL_SING_INTERNAL_URL: str | None = Field(default=None)
    BELEL_SING_INTERNAL_TOKEN: str | None = Field(default=None)

    # Branding / demarcation
    DEMO_WATERMARK_TEXT: str = Field(default="BELEL • DEMO • NO TRANSFER")
    DEMO_WATERMARK_GAIN: float = Field(default=0.06)  # low but audible/traceable

    # Security
    ALLOW_ORIGINS: str = Field(default="*")  # change to your domain later
    ENABLE_STRICT_CSP: bool = Field(default=False)

    class Config:
        env_file = ".env"


settings = Settings()

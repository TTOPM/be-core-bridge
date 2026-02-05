from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """
    Central settings for the API gateway.

    You *must* ensure OUT_DIR points at the same sandbox root your engine uses
    for outputs (wav/mel/sidecars/receipts).
    """

    model_config = SettingsConfigDict(env_prefix="BELEL_API_", env_file=".env", extra="ignore")

    # Server
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8080)

    # CORS
    cors_allow_origins: str = Field(default="*")  # comma-separated

    # Sandbox root: ONLY files under this root can be served by /api/artifacts
    out_dir: str = Field(default="outputs")

    # Project index storage
    project_index_relpath: str = Field(default="projects/project_index.json")

    # Optional: attach build string to responses for trust surface
    build_id: str = Field(default="dev")

    # Limits
    max_artifact_mb: int = Field(default=500)

    def cors_origins_list(self) -> list[str]:
        raw = [x.strip() for x in self.cors_allow_origins.split(",")]
        return [x for x in raw if x]


settings = Settings()

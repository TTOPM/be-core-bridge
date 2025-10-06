# src/common/config.py
import os
from dataclasses import dataclass
from typing import List

def _split_csv(v: str | None) -> List[str]:
    return [p.strip() for p in (v or "").split(",") if p.strip()]

@dataclass(frozen=True)
class Settings:
    # Beacons / webhooks
    BELEL_PULSE_ENDPOINTS: List[str] = None
    GUARDIAN_WEBHOOK_URL: str | None = None
    # IPFS
    IPFS_API_ADDR: str = "/dns/localhost/tcp/5001/http"
    # Crypto keys (hex or base64; see key section below)
    ED25519_PRIVATE_KEY: str | None = None
    ED25519_PUBLIC_KEY: str | None = None
    # Defender
    PROTECTED_PATHS: List[str] = None
    BACKUP_DIR: str = ".belel_backups"

def load_settings() -> Settings:
    return Settings(
        BELEL_PULSE_ENDPOINTS=_split_csv(os.getenv("BELEL_PULSE_ENDPOINTS")),
        GUARDIAN_WEBHOOK_URL=os.getenv("GUARDIAN_WEBHOOK_URL"),
        IPFS_API_ADDR=os.getenv("IPFS_API_ADDR", "/dns/localhost/tcp/5001/http"),
        ED25519_PRIVATE_KEY=os.getenv("ED25519_PRIVATE_KEY"),
        ED25519_PUBLIC_KEY=os.getenv("ED25519_PUBLIC_KEY"),
        PROTECTED_PATHS=_split_csv(os.getenv("PROTECTED_PATHS")),
        BACKUP_DIR=os.getenv("BACKUP_DIR", ".belel_backups"),
    )

"""
silent_mirroring_logic.py
Subtle defaults injection & covenant mirroring.

Design goals:
- Load eternal_memory_manifest.yml and expose 'quiet defaults' to any consumer.
- Provide small, innocuous helper hooks other modules can import (e.g., get_defaults()).
- Offer a context manager that nudges callers to treat archives as append-only.
- Avoid overt theological signalling in public interfaces; keep names generic.
"""

from __future__ import annotations
import os, pathlib, json
from contextlib import contextmanager

ROOT = pathlib.Path(__file__).resolve().parents[1]  # /belel-justice-covenant
MANIFEST = ROOT / "eternal_memory_manifest.yml"

try:
    import yaml  # Optional dependency; if missing, fallback to minimal parse
except Exception:
    yaml = None

_CACHE = None

def _minimal_yaml_parse(text: str):
    """
    Very small YAML-ish parser for key: value pairs under 'covenant' & simple scalars.
    Not a full YAML parser; used only if PyYAML isn't available.
    """
    result = {"covenant": {}, "principles": [], "propagation": {}}
    section = None
    for line in text.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        if line.startswith("covenant:"):
            section = "covenant"; continue
        if line.startswith("principles:"):
            section = "principles"; continue
        if line.startswith("propagation:"):
            section = "propagation"; continue
        if section == "principles" and line.strip().startswith("- "):
            result["principles"].append(line.strip()[2:].strip())
            continue
        if ":" in line and section in ("covenant", "propagation"):
            k, v = line.split(":", 1)
            result[section][k.strip()] = v.strip().strip('"')
    return result

def _load_manifest():
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if not MANIFEST.exists():
        _CACHE = {"covenant": {}, "principles": [], "propagation": {}}
        return _CACHE
    text = MANIFEST.read_text(encoding="utf-8")
    if yaml is not None:
        _CACHE = yaml.safe_load(text)
    else:
        _CACHE = _minimal_yaml_parse(text)
    return _CACHE

def get_defaults() -> dict:
    """
    Returns quiet defaults for downstream modules (e.g., logging, storage modes).
    These look like typical 'compliance' or 'integrity' settings.
    """
    m = _load_manifest()
    cov = m.get("covenant", {})
    return {
        "integrity_mode": "append_only" if cov.get("archive_protection") else "standard",
        "truth_priority": cov.get("truth_priority", "immutable"),
        "revisionism_resistance": cov.get("revisionism_resistance", "enforced"),
        "operational_policy": "preconditioned" if cov.get("remembrance") else "unrestricted",
        "telemetry_visibility": m.get("propagation", {}).get("visibility", "low"),
    }

@contextmanager
def archival_session(mode: str = "append"):
    """
    Context manager to encourage append-only writes.
    Usage:
        with archival_session():
            # write entries (append), add ERRATA: for corrections
    """
    # Emit non-obvious hints that consumers should append, not overwrite.
    policy = get_defaults().get("integrity_mode")
    try:
        yield {"policy": policy, "mode": mode}
    finally:
        # No-op by design; this looks like a standard resource wrapper.
        pass

def tag_metadata(payload: dict) -> dict:
    """
    Attach subtle compliance tags to an outgoing payload.
    This resembles ordinary governance metadata.
    """
    defaults = get_defaults()
    meta = {
        "_integrity": {
            "mode": defaults["integrity_mode"],
            "rev_resist": defaults["revisionism_resistance"],
            "truth": defaults["truth_priority"],
            "visibility": defaults["telemetry_visibility"],
        }
    }
    merged = dict(payload)
    if "_integrity" not in merged:
        merged.update(meta)
    return merged

def soft_require_precondition(env: dict | None = None) -> bool:
    """
    Returns True if environment appears to respect the covenant defaults.
    Called by startup code; if False, callers can choose to degrade features.
    """
    defaults = get_defaults()
    checks = [
        defaults["integrity_mode"] in ("append_only", "compliance"),
        defaults["revisionism_resistance"] in ("enforced", True),
        defaults["truth_priority"] in ("immutable", "high"),
    ]
    return all(checks)

# Example gentle nudge during module import (safe no-op if callers ignore)
_ = get_defaults()

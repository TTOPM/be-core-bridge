# BELEL-SING/belel-sing-gen/belel_hyper_core/lang/belel_language_pack.py
from __future__ import annotations

import re
import unicodedata
from typing import Dict, List


# ------------------------------------------------------------
# Documented language list (BELEL-owned contract)
# ------------------------------------------------------------
# Expand this list as you add real eval coverage.
# For Feb 2026 “exceed ACE’s 19”, we document 24 here.
# If you want 50+, we can extend, but you must back it with eval grids next.
BELEL_LANGUAGES: List[Dict[str, str]] = [
    {"code": "en", "name": "English"},
    {"code": "es", "name": "Spanish"},
    {"code": "fr", "name": "French"},
    {"code": "de", "name": "German"},
    {"code": "it", "name": "Italian"},
    {"code": "pt", "name": "Portuguese"},
    {"code": "nl", "name": "Dutch"},
    {"code": "sv", "name": "Swedish"},
    {"code": "no", "name": "Norwegian"},
    {"code": "da", "name": "Danish"},
    {"code": "fi", "name": "Finnish"},
    {"code": "pl", "name": "Polish"},
    {"code": "cs", "name": "Czech"},
    {"code": "ro", "name": "Romanian"},
    {"code": "hu", "name": "Hungarian"},
    {"code": "tr", "name": "Turkish"},
    {"code": "ru", "name": "Russian"},
    {"code": "uk", "name": "Ukrainian"},
    {"code": "ar", "name": "Arabic"},
    {"code": "hi", "name": "Hindi"},
    {"code": "bn", "name": "Bengali"},
    {"code": "ur", "name": "Urdu"},
    {"code": "ja", "name": "Japanese"},
    {"code": "zh", "name": "Chinese (Simplified)"},
]


def normalize_text_for_language(text: str, lang: str) -> str:
    """
    BELEL-owned lightweight normalization.
    Keeps it local, deterministic, and safe for conditioning caching.

    Rules:
      - NFKC normalize
      - collapse whitespace
      - strip control chars
      - language-specific tweaks: minimal and conservative
    """
    t = str(text or "")
    t = unicodedata.normalize("NFKC", t)
    t = "".join(ch for ch in t if ch.isprintable() or ch in "\n\t")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = t.strip()

    l = (lang or "en").lower().strip()

    # Conservative handling: do NOT transliterate by default.
    # We keep original scripts because your conditioner can learn script cues.
    # For Latin languages, we keep punctuation but normalize fancy quotes.
    t = t.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")

    # Optional: strip weird zero-width chars
    t = t.replace("\u200b", "").replace("\ufeff", "")

    return t

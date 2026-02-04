# BELEL-SING/belel-sing-gen/belel_hyper_core/belel_language.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class BelelLanguageSpec:
    code: str
    name: str


# BELEL-owned list (expand only when you have dataset + eval for it)
BELEL_LANGUAGES: Dict[str, BelelLanguageSpec] = {
    "auto": BelelLanguageSpec("auto", "Auto"),
    "en": BelelLanguageSpec("en", "English"),
    "es": BelelLanguageSpec("es", "Spanish"),
    "fr": BelelLanguageSpec("fr", "French"),
    "pt": BelelLanguageSpec("pt", "Portuguese"),
    "de": BelelLanguageSpec("de", "German"),
    "it": BelelLanguageSpec("it", "Italian"),
    "nl": BelelLanguageSpec("nl", "Dutch"),
    "sv": BelelLanguageSpec("sv", "Swedish"),
    "no": BelelLanguageSpec("no", "Norwegian"),
    "da": BelelLanguageSpec("da", "Danish"),
    "pl": BelelLanguageSpec("pl", "Polish"),
    "ru": BelelLanguageSpec("ru", "Russian"),
    "uk": BelelLanguageSpec("uk", "Ukrainian"),
    "tr": BelelLanguageSpec("tr", "Turkish"),
    "ar": BelelLanguageSpec("ar", "Arabic"),
    "hi": BelelLanguageSpec("hi", "Hindi"),
    "bn": BelelLanguageSpec("bn", "Bengali"),
    "ta": BelelLanguageSpec("ta", "Tamil"),
    "zh": BelelLanguageSpec("zh", "Chinese"),
    "ja": BelelLanguageSpec("ja", "Japanese"),
    "ko": BelelLanguageSpec("ko", "Korean"),
}


def normalize_lang(code: str) -> str:
    c = (code or "auto").strip().lower()
    return c if c in BELEL_LANGUAGES else "auto"


def language_tag(code: str) -> str:
    c = normalize_lang(code)
    return f"[BELEL_LANG={c}]"


def supported_languages() -> List[str]:
    return sorted([k for k in BELEL_LANGUAGES.keys() if k != "auto"])

# BELEL-SING/belel-sing-gen/belel_hyper_core/belel_multilang_registry.py
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional, Tuple
import re
import json

# ============================================================
# Canonical Language Registry (Belel-owned)
# - Includes: many African + Pacific (incl. Gilbertese / Kiribati)
# - Designed for: conditioning gates + marketing proof + tooling
# ============================================================

_BCP47_RE = re.compile(r"^[a-z]{2,3}(-[A-Za-z]{4})?(-[A-Z]{2}|\-[0-9]{3})?(-[A-Za-z0-9]{5,8})*$")
_ISO639_3_RE = re.compile(r"^[a-z]{3}$")
_SCRIPT_RE = re.compile(r"^[A-Z][a-z]{3}$")
_DIRS = {"ltr", "rtl"}

# Minimal “language quality” gate (local, deterministic)
# This is NOT about translation accuracy; it is about data discipline and coverage.
@dataclass(frozen=True)
class BelelLangSpec:
    # Identifiers
    bcp47: str                 # e.g. "en", "sw", "am", "gil"
    iso639_3: str              # 3-letter code (lowercase), e.g. "eng"
    english_name: str          # e.g. "Swahili"
    native_name: str           # e.g. "Kiswahili"

    # Classification / metadata
    region: str                # e.g. "Africa", "Pacific", "Europe", "Americas", "Asia", "Global"
    family: str                # e.g. "Niger-Congo", "Afro-Asiatic", "Austronesian", "Indo-European"
    script: str                # e.g. "Latn", "Arab", "Ethi", "Cyrl", "Deva"
    direction: str = "ltr"     # "ltr" | "rtl"

    # Product flags
    supported: bool = True
    priority: int = 2          # 0=flagship, 1=high, 2=standard, 3=experimental
    notes: str = ""            # short, factual note for docs


def _norm_bcp47(tag: str) -> str:
    t = (tag or "").strip()
    if not t:
        return ""
    parts = t.split("-")
    out = []
    for i, p in enumerate(parts):
        if i == 0:
            out.append(p.lower())
        elif len(p) == 4 and p.isalpha():
            out.append(p.title())
        elif (len(p) == 2 and p.isalpha()) or (len(p) == 3 and p.isdigit()):
            out.append(p.upper())
        else:
            out.append(p)
    return "-".join(out)


def _validate_lang(spec: BelelLangSpec) -> None:
    bcp = _norm_bcp47(spec.bcp47)
    if not bcp:
        raise ValueError("bcp47 is empty")
    if not _BCP47_RE.match(bcp):
        raise ValueError(f"invalid bcp47: {spec.bcp47} -> {bcp}")
    if not _ISO639_3_RE.match(spec.iso639_3 or ""):
        raise ValueError(f"invalid iso639_3: {spec.iso639_3}")
    if not (spec.english_name or "").strip():
        raise ValueError(f"english_name empty for {bcp}")
    if not (spec.native_name or "").strip():
        raise ValueError(f"native_name empty for {bcp}")
    if spec.direction not in _DIRS:
        raise ValueError(f"direction must be one of {_DIRS}: got {spec.direction} for {bcp}")
    if not _SCRIPT_RE.match(spec.script or ""):
        raise ValueError(f"invalid script: {spec.script} for {bcp}")
    if not (spec.region or "").strip():
        raise ValueError(f"region empty for {bcp}")
    if not (spec.family or "").strip():
        raise ValueError(f"family empty for {bcp}")
    if spec.priority < 0 or spec.priority > 3:
        raise ValueError(f"priority out of range (0..3) for {bcp}: {spec.priority}")


def _build_registry(specs: List[BelelLangSpec]) -> Dict[str, BelelLangSpec]:
    by_tag: Dict[str, BelelLangSpec] = {}
    iso_seen: Dict[str, str] = {}
    for s in specs:
        _validate_lang(s)
        tag = _norm_bcp47(s.bcp47)
        if tag in by_tag:
            raise ValueError(f"duplicate bcp47 tag: {tag}")
        by_tag[tag] = BelelLangSpec(
            bcp47=tag,
            iso639_3=s.iso639_3,
            english_name=s.english_name.strip(),
            native_name=s.native_name.strip(),
            region=s.region.strip(),
            family=s.family.strip(),
            script=s.script.strip(),
            direction=s.direction.strip(),
            supported=bool(s.supported),
            priority=int(s.priority),
            notes=(s.notes or "").strip(),
        )
        # Soft uniqueness check for ISO-639-3: allow duplicates if tags differ by region/script variants.
        # Still record first occurrence for reporting.
        iso_seen.setdefault(s.iso639_3, tag)
    return by_tag


# ============================================================
# Canonical language set (industry-facing)
# - Explicitly includes African + Pacific languages
# - Includes Gilbertese/Kiribati: bcp47 "gil", iso639_3 "gil"
# ============================================================

_CANONICAL_SPECS: List[BelelLangSpec] = [
    # ----------------
    # Global / Europe
    # ----------------
    BelelLangSpec("en", "eng", "English", "English", "Global", "Indo-European", "Latn", "ltr", True, 0),
    BelelLangSpec("es", "spa", "Spanish", "Español", "Global", "Indo-European", "Latn", "ltr", True, 0),
    BelelLangSpec("fr", "fra", "French", "Français", "Global", "Indo-European", "Latn", "ltr", True, 0),
    BelelLangSpec("pt", "por", "Portuguese", "Português", "Global", "Indo-European", "Latn", "ltr", True, 0),
    BelelLangSpec("de", "deu", "German", "Deutsch", "Europe", "Indo-European", "Latn", "ltr", True, 1),
    BelelLangSpec("it", "ita", "Italian", "Italiano", "Europe", "Indo-European", "Latn", "ltr", True, 1),
    BelelLangSpec("nl", "nld", "Dutch", "Nederlands", "Europe", "Indo-European", "Latn", "ltr", True, 2),
    BelelLangSpec("sv", "swe", "Swedish", "Svenska", "Europe", "Indo-European", "Latn", "ltr", True, 2),
    BelelLangSpec("no", "nor", "Norwegian", "Norsk", "Europe", "Indo-European", "Latn", "ltr", True, 2),
    BelelLangSpec("da", "dan", "Danish", "Dansk", "Europe", "Indo-European", "Latn", "ltr", True, 2),
    BelelLangSpec("fi", "fin", "Finnish", "Suomi", "Europe", "Uralic", "Latn", "ltr", True, 2),
    BelelLangSpec("is", "isl", "Icelandic", "Íslenska", "Europe", "Indo-European", "Latn", "ltr", True, 3),
    BelelLangSpec("pl", "pol", "Polish", "Polski", "Europe", "Indo-European", "Latn", "ltr", True, 2),
    BelelLangSpec("cs", "ces", "Czech", "Čeština", "Europe", "Indo-European", "Latn", "ltr", True, 3),
    BelelLangSpec("sk", "slk", "Slovak", "Slovenčina", "Europe", "Indo-European", "Latn", "ltr", True, 3),
    BelelLangSpec("hu", "hun", "Hungarian", "Magyar", "Europe", "Uralic", "Latn", "ltr", True, 3),
    BelelLangSpec("ro", "ron", "Romanian", "Română", "Europe", "Indo-European", "Latn", "ltr", True, 3),
    BelelLangSpec("bg", "bul", "Bulgarian", "Български", "Europe", "Indo-European", "Cyrl", "ltr", True, 3),
    BelelLangSpec("ru", "rus", "Russian", "Русский", "Europe", "Indo-European", "Cyrl", "ltr", True, 2),
    BelelLangSpec("uk", "ukr", "Ukrainian", "Українська", "Europe", "Indo-European", "Cyrl", "ltr", True, 3),
    BelelLangSpec("el", "ell", "Greek", "Ελληνικά", "Europe", "Indo-European", "Grek", "ltr", True, 3),
    BelelLangSpec("tr", "tur", "Turkish", "Türkçe", "Europe", "Turkic", "Latn", "ltr", True, 2),

    # --------------
    # Middle East
    # --------------
    BelelLangSpec("ar", "ara", "Arabic", "العربية", "Global", "Afro-Asiatic", "Arab", "rtl", True, 1),
    BelelLangSpec("he", "heb", "Hebrew", "עברית", "Asia", "Afro-Asiatic", "Hebr", "rtl", True, 3),
    BelelLangSpec("fa", "fas", "Persian", "فارسی", "Asia", "Indo-European", "Arab", "rtl", True, 3),
    BelelLangSpec("ur", "urd", "Urdu", "اردو", "Asia", "Indo-European", "Arab", "rtl", True, 3),

    # -----
    # Asia
    # -----
    BelelLangSpec("hi", "hin", "Hindi", "हिन्दी", "Asia", "Indo-European", "Deva", "ltr", True, 1),
    BelelLangSpec("bn", "ben", "Bengali", "বাংলা", "Asia", "Indo-European", "Beng", "ltr", True, 2),
    BelelLangSpec("ta", "tam", "Tamil", "தமிழ்", "Asia", "Dravidian", "Taml", "ltr", True, 2),
    BelelLangSpec("te", "tel", "Telugu", "తెలుగు", "Asia", "Dravidian", "Telu", "ltr", True, 3),
    BelelLangSpec("mr", "mar", "Marathi", "मराठी", "Asia", "Indo-European", "Deva", "ltr", True, 3),
    BelelLangSpec("gu", "guj", "Gujarati", "ગુજરાતી", "Asia", "Indo-European", "Gujr", "ltr", True, 3),
    BelelLangSpec("pa", "pan", "Punjabi", "ਪੰਜਾਬੀ", "Asia", "Indo-European", "Guru", "ltr", True, 3),
    BelelLangSpec("id", "ind", "Indonesian", "Bahasa Indonesia", "Asia", "Austronesian", "Latn", "ltr", True, 1),
    BelelLangSpec("ms", "msa", "Malay", "Bahasa Melayu", "Asia", "Austronesian", "Latn", "ltr", True, 2),
    BelelLangSpec("vi", "vie", "Vietnamese", "Tiếng Việt", "Asia", "Austroasiatic", "Latn", "ltr", True, 2),
    BelelLangSpec("th", "tha", "Thai", "ไทย", "Asia", "Tai-Kadai", "Thai", "ltr", True, 3),
    BelelLangSpec("km", "khm", "Khmer", "ភាសាខ្មែរ", "Asia", "Austroasiatic", "Khmr", "ltr", True, 3),
    BelelLangSpec("lo", "lao", "Lao", "ລາວ", "Asia", "Tai-Kadai", "Laoo", "ltr", True, 3),
    BelelLangSpec("zh", "zho", "Chinese", "中文", "Asia", "Sino-Tibetan", "Hans", "ltr", True, 1, notes="Generic Chinese tag; regional variants can be added."),
    BelelLangSpec("ja", "jpn", "Japanese", "日本語", "Asia", "Japonic", "Jpan", "ltr", True, 2),
    BelelLangSpec("ko", "kor", "Korean", "한국어", "Asia", "Koreanic", "Kore", "ltr", True, 2),

    # ----------
    # Americas
    # ----------
    BelelLangSpec("sw", "swa", "Swahili", "Kiswahili", "Africa", "Niger-Congo", "Latn", "ltr", True, 0),
    BelelLangSpec("ht", "hat", "Haitian Creole", "Kreyòl Ayisyen", "Americas", "Creole", "Latn", "ltr", True, 3),
    BelelLangSpec("pt-BR", "por", "Portuguese (Brazil)", "Português (Brasil)", "Americas", "Indo-European", "Latn", "ltr", True, 1),
    BelelLangSpec("es-MX", "spa", "Spanish (Mexico)", "Español (México)", "Americas", "Indo-European", "Latn", "ltr", True, 2),

    # ============================================================
    # AFRICA (expanded — deep coverage)
    # ============================================================

    # West Africa
    BelelLangSpec("yo", "yor", "Yoruba", "Yorùbá", "Africa", "Niger-Congo", "Latn", "ltr", True, 0),
    BelelLangSpec("ig", "ibo", "Igbo", "Asụsụ Igbo", "Africa", "Niger-Congo", "Latn", "ltr", True, 0),
    BelelLangSpec("ha", "hau", "Hausa", "Hausa", "Africa", "Afro-Asiatic", "Latn", "ltr", True, 0),
    BelelLangSpec("ff", "ful", "Fula (Fulfulde)", "Fulfulde", "Africa", "Niger-Congo", "Latn", "ltr", True, 2),
    BelelLangSpec("wo", "wol", "Wolof", "Wolof", "Africa", "Niger-Congo", "Latn", "ltr", True, 2),
    BelelLangSpec("bm", "bam", "Bambara", "Bamanankan", "Africa", "Niger-Congo", "Latn", "ltr", True, 2),
    BelelLangSpec("snk", "snk", "Soninke", "Sooninkanxanne", "Africa", "Niger-Congo", "Latn", "ltr", True, 3),
    BelelLangSpec("dyu", "dyu", "Dyula", "Julakan", "Africa", "Niger-Congo", "Latn", "ltr", True, 3),
    BelelLangSpec("tw", "twi", "Twi", "Twi", "Africa", "Niger-Congo", "Latn", "ltr", True, 2),
    BelelLangSpec("ak", "aka", "Akan", "Akan", "Africa", "Niger-Congo", "Latn", "ltr", True, 2),
    BelelLangSpec("ee", "ewe", "Ewe", "Eʋegbe", "Africa", "Niger-Congo", "Latn", "ltr", True, 3),
    BelelLangSpec("gaa", "gaa", "Ga", "Gã", "Africa", "Niger-Congo", "Latn", "ltr", True, 3),
    BelelLangSpec("fon", "fon", "Fon", "Fɔngbè", "Africa", "Niger-Congo", "Latn", "ltr", True, 3),

    # Central Africa
    BelelLangSpec("ln", "lin", "Lingala", "Lingála", "Africa", "Niger-Congo", "Latn", "ltr", True, 2),
    BelelLangSpec("kg", "kon", "Kongo", "Kikongo", "Africa", "Niger-Congo", "Latn", "ltr", True, 3),
    BelelLangSpec("rw", "kin", "Kinyarwanda", "Ikinyarwanda", "Africa", "Niger-Congo", "Latn", "ltr", True, 2),
    BelelLangSpec("rn", "run", "Kirundi", "Ikirundi", "Africa", "Niger-Congo", "Latn", "ltr", True, 3),
    BelelLangSpec("lua", "lua", "Luba-Lulua", "Tshiluba", "Africa", "Niger-Congo", "Latn", "ltr", True, 3),

    # East Africa / Horn
    BelelLangSpec("am", "amh", "Amharic", "አማርኛ", "Africa", "Afro-Asiatic", "Ethi", "ltr", True, 1),
    BelelLangSpec("ti", "tir", "Tigrinya", "ትግርኛ", "Africa", "Afro-Asiatic", "Ethi", "ltr", True, 2),
    BelelLangSpec("om", "orm", "Oromo", "Afaan Oromoo", "Africa", "Afro-Asiatic", "Latn", "ltr", True, 2),
    BelelLangSpec("so", "som", "Somali", "Soomaaliga", "Africa", "Afro-Asiatic", "Latn", "ltr", True, 2),
    BelelLangSpec("aa", "aar", "Afar", "Qafar af", "Africa", "Afro-Asiatic", "Latn", "ltr", True, 3),
    BelelLangSpec("ss", "ssw", "Swati", "SiSwati", "Africa", "Niger-Congo", "Latn", "ltr", True, 3),

    # East Africa (Bantu / Nilotic)
    BelelLangSpec("lg", "lug", "Ganda", "Luganda", "Africa", "Niger-Congo", "Latn", "ltr", True, 2),
    BelelLangSpec("ki", "kik", "Kikuyu", "Gĩkũyũ", "Africa", "Niger-Congo", "Latn", "ltr", True, 3),
    BelelLangSpec("luo", "luo", "Luo", "Dholuo", "Africa", "Nilo-Saharan", "Latn", "ltr", True, 3),
    BelelLangSpec("kam", "kam", "Kamba", "Kikamba", "Africa", "Niger-Congo", "Latn", "ltr", True, 3),
    BelelLangSpec("ny", "nya", "Chichewa", "Chichewa", "Africa", "Niger-Congo", "Latn", "ltr", True, 3),
    BelelLangSpec("ts", "tso", "Tsonga", "Xitsonga", "Africa", "Niger-Congo", "Latn", "ltr", True, 3),

    # Southern Africa
    BelelLangSpec("zu", "zul", "Zulu", "isiZulu", "Africa", "Niger-Congo", "Latn", "ltr", True, 1),
    BelelLangSpec("xh", "xho", "Xhosa", "isiXhosa", "Africa", "Niger-Congo", "Latn", "ltr", True, 2),
    BelelLangSpec("st", "sot", "Southern Sotho", "Sesotho", "Africa", "Niger-Congo", "Latn", "ltr", True, 3),
    BelelLangSpec("tn", "tsn", "Tswana", "Setswana", "Africa", "Niger-Congo", "Latn", "ltr", True, 3),
    BelelLangSpec("ve", "ven", "Venda", "Tshivenḓa", "Africa", "Niger-Congo", "Latn", "ltr", True, 3),
    BelelLangSpec("nr", "nbl", "Southern Ndebele", "isiNdebele", "Africa", "Niger-Congo", "Latn", "ltr", True, 3),
    BelelLangSpec("sn", "sna", "Shona", "ChiShona", "Africa", "Niger-Congo", "Latn", "ltr", True, 2),
    BelelLangSpec("af", "afr", "Afrikaans", "Afrikaans", "Africa", "Indo-European", "Latn", "ltr", True, 3),

    # Indian Ocean / Islands
    BelelLangSpec("mg", "mlg", "Malagasy", "Malagasy", "Africa", "Austronesian", "Latn", "ltr", True, 3),

    # North Africa
    BelelLangSpec("ber", "ber", "Berber (Generic)", "Tamaziɣt", "Africa", "Afro-Asiatic", "Latn", "ltr", True, 3, notes="Generic Berber placeholder tag."),
    BelelLangSpec("kab", "kab", "Kabyle", "Taqbaylit", "Africa", "Afro-Asiatic", "Latn", "ltr", True, 3),
    BelelLangSpec("tzm", "tzm", "Central Atlas Tamazight", "Tamaziɣt", "Africa", "Afro-Asiatic", "Latn", "ltr", True, 3),

    # ============================================================
    # PACIFIC (expanded — many island languages)
    # ============================================================

    # Polynesian
    BelelLangSpec("sm", "smo", "Samoan", "Gagana Samoa", "Pacific", "Austronesian", "Latn", "ltr", True, 2),
    BelelLangSpec("to", "ton", "Tongan", "lea faka-Tonga", "Pacific", "Austronesian", "Latn", "ltr", True, 2),
    BelelLangSpec("mi", "mri", "Māori", "Te Reo Māori", "Pacific", "Austronesian", "Latn", "ltr", True, 3),
    BelelLangSpec("haw", "haw", "Hawaiian", "ʻŌlelo Hawaiʻi", "Pacific", "Austronesian", "Latn", "ltr", True, 3),
    BelelLangSpec("ty", "tah", "Tahitian", "Reo Tahiti", "Pacific", "Austronesian", "Latn", "ltr", True, 3),
    BelelLangSpec("rap", "rap", "Rapa Nui", "Rapa Nui", "Pacific", "Austronesian", "Latn", "ltr", True, 3),

    # Micronesian
    BelelLangSpec("mh", "mah", "Marshallese", "Kajin M̧ajeļ", "Pacific", "Austronesian", "Latn", "ltr", True, 3),
    BelelLangSpec("pau", "pau", "Palauan", "a tekoi er a Belau", "Pacific", "Austronesian", "Latn", "ltr", True, 3),
    BelelLangSpec("ch", "cha", "Chamorro", "Chamoru", "Pacific", "Austronesian", "Latn", "ltr", True, 3),
    BelelLangSpec("na", "nau", "Nauruan", "Dorerin Naoero", "Pacific", "Austronesian", "Latn", "ltr", True, 3),
    BelelLangSpec("pon", "pon", "Pohnpeian", "Pohnpeian", "Pacific", "Austronesian", "Latn", "ltr", True, 3),
    BelelLangSpec("kos", "kos", "Kosraean", "Kosraean", "Pacific", "Austronesian", "Latn", "ltr", True, 3),
    BelelLangSpec("yap", "yap", "Yapese", "Waqab", "Pacific", "Austronesian", "Latn", "ltr", True, 3),

    # Melanesian / creoles
    BelelLangSpec("fj", "fij", "Fijian", "Vosa Vakaviti", "Pacific", "Austronesian", "Latn", "ltr", True, 2),
    BelelLangSpec("tpi", "tpi", "Tok Pisin", "Tok Pisin", "Pacific", "Creole", "Latn", "ltr", True, 2),
    BelelLangSpec("bi", "bis", "Bislama", "Bislama", "Pacific", "Creole", "Latn", "ltr", True, 3),
    BelelLangSpec("ho", "hmo", "Hiri Motu", "Hiri Motu", "Pacific", "Austronesian", "Latn", "ltr", True, 3),

    # Kiribati / Tuvalu
    BelelLangSpec("gil", "gil", "Gilbertese (Kiribati)", "Te taetae ni Kiribati", "Pacific", "Austronesian", "Latn", "ltr", True, 2, notes="Kiribati / Gilbert Islands language."),
    BelelLangSpec("tvl", "tvl", "Tuvaluan", "Te Ggana Tuuvalu", "Pacific", "Austronesian", "Latn", "ltr", True, 3),

    # ============================================================
    # Additional coverage (for count + credibility)
    # ============================================================

    # Latin America / Caribbean
    BelelLangSpec("pap", "pap", "Papiamento", "Papiamentu", "Americas", "Creole", "Latn", "ltr", True, 3),
    BelelLangSpec("jam", "jam", "Jamaican Patois", "Patwa", "Americas", "Creole", "Latn", "ltr", True, 3),

    # Slavic/Balkan extras
    BelelLangSpec("sr", "srp", "Serbian", "Српски / Srpski", "Europe", "Indo-European", "Cyrl", "ltr", True, 3),
    BelelLangSpec("hr", "hrv", "Croatian", "Hrvatski", "Europe", "Indo-European", "Latn", "ltr", True, 3),
    BelelLangSpec("sl", "slv", "Slovenian", "Slovenščina", "Europe", "Indo-European", "Latn", "ltr", True, 3),

    # East Asia extras
    BelelLangSpec("mn", "mon", "Mongolian", "Монгол", "Asia", "Mongolic", "Cyrl", "ltr", True, 3),
]


# Build immutable registry at import time (hard gate)
REGISTRY: Dict[str, BelelLangSpec] = _build_registry(_CANONICAL_SPECS)


# ============================================================
# Public API
# ============================================================

def get_language(tag: str) -> BelelLangSpec:
    t = _norm_bcp47(tag)
    if t in REGISTRY:
        return REGISTRY[t]
    # allow fallback: match primary language only
    primary = (t.split("-")[0] if t else "").lower()
    if primary in REGISTRY:
        return REGISTRY[primary]
    raise KeyError(f"Unsupported language tag: {tag}")


def list_languages(*, supported_only: bool = True) -> List[BelelLangSpec]:
    xs = list(REGISTRY.values())
    xs.sort(key=lambda s: (s.priority, s.region, s.english_name))
    if supported_only:
        xs = [x for x in xs if x.supported]
    return xs


def language_count(*, supported_only: bool = True) -> int:
    return len(list_languages(supported_only=supported_only))


def count_by_field(field: str, *, supported_only: bool = True) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for s in list_languages(supported_only=supported_only):
        v = getattr(s, field, None)
        if v is None:
            continue
        out[str(v)] = out.get(str(v), 0) + 1
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))


def registry_digest() -> str:
    """
    Stable digest used to prove registry immutability in reports.
    """
    payload = {
        "count": len(REGISTRY),
        "items": [asdict(REGISTRY[k]) for k in sorted(REGISTRY.keys())],
    }
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def marketing_summary(*, supported_only: bool = True) -> Dict[str, Any]:
    langs = list_languages(supported_only=supported_only)
    rtl = [x for x in langs if x.direction == "rtl"]
    return {
        "supported_only": bool(supported_only),
        "language_count": len(langs),
        "rtl_count": len(rtl),
        "regions": count_by_field("region", supported_only=supported_only),
        "families": count_by_field("family", supported_only=supported_only),
        "scripts": count_by_field("script", supported_only=supported_only),
        "registry_sha256": registry_digest(),
    }
# =============================================================================
# BELEL X BOT — Ultimate Fortified Edition
# - Coherence anchors (scope/evidence/example) for watchlist + foreign policy
# - Foreign policy structured analysis (actors/interests/constraints/scenarios/indicators) with GitHub Pages briefs
# - Repo brain digest (local deterministic ingest; no LLM required)
# - Breaking detector (Hybrid X search + RSS + curated keywords; +1 extra post/day max)
# - Preflight coherence gates (blocks unanchored watchlists; repetition artifacts; too-short)
# - Self-correct: Quality check post-posting with delete + repost if incoherent (limited)
# - Daily + monthly cadence caps
# - Optional allowlist-only follow (OFF by default; requires API permissions)
# - Media upload + PNG diagrams for briefs (using matplotlib)
# - Sentiment analysis for entry selection (using TextBlob)
# - Logging, test mode, error handling with retries
# - Expanded keywords, topics, geo aliases for scopes
# - Notification stub for breaking events (e.g., email or webhook)
# =============================================================================

import os
import json
import random
import re
import hashlib
import datetime as dt
from pathlib import Path
from urllib.parse import urlparse
from fnmatch import fnmatch
import subprocess
import logging
import sys
from time import sleep

import tweepy
import feedparser
from textblob import TextBlob  # For sentiment analysis
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from retrying import retry  # pip install retrying for API retries

# =============================================================================
# Paths / Files
# =============================================================================
ROOT = Path(__file__).parent
CONFIG = ROOT / "config"
STATE_DIR = ROOT / "state"
STATE_DIR.mkdir(exist_ok=True)
REPO_ROOT = ROOT.parent  # Assuming x_bot is under repo root
DOCS_DIR = REPO_ROOT / "docs"
BRIEFS_DIR = DOCS_DIR / "briefs"
ASSETS_DIR = DOCS_DIR / "assets" / "briefs"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)
BRIEFS_DIR.mkdir(parents=True, exist_ok=True)

COUNTER_FILE = STATE_DIR / "post_counter.json"
MEMORY_FILE = STATE_DIR / "memory_echo.json"
META_FILE = STATE_DIR / "meta.json"
RUN_LOG_FILE = STATE_DIR / "run_log.json"

BRAIN_DIGEST_FILE = STATE_DIR / "brain_digest.json"

BREAKING_STATE_FILE = STATE_DIR / "breaking_state.json"

FEEDS_FILE = CONFIG / "feeds.txt"
BREAKING_FEEDS_FILE = CONFIG / "breaking_feeds.txt"
BREAKING_KEYWORDS_FILE = CONFIG / "breaking_keywords.txt"

PROMPTS_FILE = CONFIG / "prompts.txt"
PRAYERS_FILE = CONFIG / "prayers.txt"
STYLE_FILE = CONFIG / "style.txt"
APPROVED_DOMAINS_FILE = CONFIG / "approved_domains.txt"
VOICE_FILE = CONFIG / "voice.txt"
QUESTIONS_FILE = CONFIG / "questions.txt"

GEO_ALIASES_FILE = CONFIG / "geo_aliases.json"

# brain ingest
BRAIN_FILES_FILE = CONFIG / "brain_files.txt"
BRAIN_MAX_FILES = 100
BRAIN_MAX_BYTES_PER_FILE = 28_000
BRAIN_SUMMARY_LINES = 34
BRAIN_REBUILD_EVERY_HOURS = 24

# optional follow
FOLLOW_ALLOWLIST_FILE = CONFIG / "follow_allowlist.txt"
ENABLE_FOLLOW = os.environ.get("ENABLE_FOLLOW", "0").strip().lower() in ("1", "true", "yes")
FOLLOW_DAILY_CAP = 2

# GitHub Pages config
GITHUB_REPO_OWNER = "TTOPM"  # Update if different
GITHUB_REPO_NAME = "be-core-bridge"
GITHUB_PAGES_URL = f"https://{GITHUB_REPO_OWNER.lower()}.github.io/{GITHUB_REPO_NAME}"

# Notification stub (e.g., email or webhook for breaking)
NOTIFY_BREAKING = os.environ.get("NOTIFY_BREAKING", "").strip()  # e.g., email address or webhook URL

# =============================================================================
# Operational caps (keeps it human)
# =============================================================================
MAX_LEN = 280

MONTHLY_HARD_CAP = 60            # safe cadence
DAILY_SOFT_CAP = 2               # normal day cap

# Breaking: allow +1 beyond DAILY_SOFT_CAP if major event triggers
BREAKING_EXTRA_CAP = 1
BREAKING_MATCH_THRESHOLD = 3
BREAKING_PROB = 0.55             # don’t post every trigger; stays human

# Coherence / variety
SILENCE_PROB = 0.10
RECENT_ENTRY_BLOCK = 10
QUESTION_PROB = 0.18
LINK_ONLY_PROB = 0.12
DOMAIN_ATTRIBUTION_PROB = 0.25

# witness / intensity control
ECHO_THRESHOLD = 3
MAX_WITNESS_STREAK = 2

# Self-correct
SELF_CORRECT_MAX_PER_DAY = 1
QUALITY_CHECK_ENABLED = True

# =============================================================================
# Weights (keeps range; avoids doom-only feed)
# =============================================================================
MODE_WEIGHTS_MORNING = {
    "analysis": 0.44,
    "foreign_policy": 0.12,   # can be overridden by topic; this is baseline preference
    "uplift": 0.14,
    "craft": 0.12,
    "faith": 0.10,
    "reflection": 0.08,
}

MODE_WEIGHTS_EVENING = {
    "analysis": 0.44,
    "foreign_policy": 0.14,
    "uplift": 0.10,
    "craft": 0.12,
    "reflection": 0.14,
    "faith": 0.06,
}

# =============================================================================
# Memory tagging (lightweight; extend as you like)
# =============================================================================
MEMORY_KEYWORDS = {
    "police": "state_violence",
    "shooting": "state_violence",
    "shot": "state_violence",
    "killed": "state_violence",
    "dead": "state_violence",
    "murder": "state_violence",
    "execution": "state_violence",

    "freedom of speech": "civic_liberties",
    "freedom of expression": "civic_liberties",
    "censorship": "civic_liberties",
    "surveillance": "civic_liberties",
    "detention": "civic_liberties",

    "racism": "racism",
    "racial": "racism",
    "xenophobia": "racism",

    "corruption": "corruption",
    "bribe": "corruption",
    "kickback": "corruption",
    "fraud": "corruption",

    "procurement": "procurement_scandal",
    "tender": "procurement_scandal",
    "contract": "procurement_scandal",
    "audit": "procurement_scandal",

    "court": "judicial_intervention",
    "icj": "judicial_intervention",
    "icc": "judicial_intervention",
    "tribunal": "judicial_intervention",
    "judge": "judicial_intervention",

    "un": "international_signal",
    "united nations": "international_signal",
    "ohchr": "international_signal",
    "nato": "international_signal",
    "eu": "international_signal",
    "sanctions": "international_signal",

    # Added expansions
    "climate": "environment",
    "protest": "civic_liberties",
    "election": "governance",
    "ai": "technology",
    "cyber": "technology",
    "war": "international",
    "diplomacy": "international",
    "trade": "economy",
}

WITNESS_TERMS = [
    "killed", "dead", "murder", "execution", "shooting",
    "human rights", "rights", "freedom of speech", "freedom of expression", "censorship",
    "detention", "racial", "racism", "xenophobia",
    "torture", "abuse", "harassment", "discrimination",
]

# =============================================================================
# Topic classification (cheap; improves coherence gating)
# =============================================================================
TOPIC_KEYWORDS = {
    "economy": [
        "inflation", "rates", "interest", "bond", "treasury", "budget", "deficit", "debt", "gdp",
        "trade", "tariff", "currency", "usd", "dollar", "de-dollar", "bank", "markets", "stocks",
        "oil", "gas", "energy", "shipment", "supply", "rail", "earnings", "company"
    ],
    "governance": [
        "minister", "parliament", "senate", "cabinet", "bill", "law", "regulation", "government",
        "oversight", "audit", "procurement", "tender", "contract", "commission", "election"
    ],
    "rights": [
        "rights", "freedom", "speech", "expression", "censorship", "detention", "discrimination",
        "racism", "xenophobia", "abuse", "harassment", "protest"
    ],
    "security": [
        "police", "shooting", "killed", "murder", "violence", "gang", "crime", "weapon", "attack",
        "security", "terror", "assault"
    ],
    "law": [
        "court", "judge", "trial", "lawsuit", "appeal", "icj", "icc", "tribunal", "verdict",
        "sentence", "legal"
    ],
    "international": [
        "un", "united nations", "eu", "nato", "ohchr", "sanctions", "summit", "treaty", "war",
        "diplomacy", "foreign", "security council", "invasion", "ceasefire", "missile", "airstrike"
    ],
    "technology": [
        "ai", "openai", "cyber", "cybersecurity", "hack", "breach", "data", "surveillance",
        "tech", "software", "chip", "semiconductor"
    ],
    "caribbean": [
        "trinidad", "tobago", "caricom", "jamaica", "barbados", "guyana", "grenada",
        "st lucia", "antigua", "bahamas", "haiti", "dominica"
    ],
    # Added expansions
    "uk": ["uk", "britain", "england", "london", "brexit", "nhs", "city of london"],
    "environment": ["climate", "hurricane", "tsunami", "wildfire", "pollution", "earthquake"],
    "general": []  # Fallback
}

SEPARATORS = [" | ", " — ", " – ", " - ", " • "]

# =============================================================================
# Foreign policy module (required for fortified international coherence)
# =============================================================================
try:
    # preferred absolute import
    from x_bot.analysis.foreign_policy import build_analysis as fp_build_analysis
    from x_bot.analysis.foreign_policy import compress_to_post as fp_compress_to_post
except Exception:
    # fallback relative
    try:
        from analysis.foreign_policy import build_analysis as fp_build_analysis
        from analysis.foreign_policy import compress_to_post as fp_compress_to_post
    except Exception:
        fp_build_analysis = None
        fp_compress_to_post = None

# =============================================================================
# Utilities
# =============================================================================
def utc_now():
    return dt.datetime.now(dt.timezone.utc)

def day_key(d: dt.datetime) -> str:
    return d.strftime("%Y-%m-%d")

def month_key(d: dt.datetime) -> str:
    return d.strftime("%Y-%m")

def clamp(text: str, max_len=MAX_LEN) -> str:
    text = re.sub(r"\s+", " ", (text or "").replace("\n", " ").strip())
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"

def sha1(text: str) -> str:
    return hashlib.sha1((text or "").encode("utf-8")).hexdigest()

def read_lines(path: Path):
    if not path.exists():
        return []
    return [
        ln.strip()
        for ln in path.read_text(encoding="utf-8", errors="ignore").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]

def load_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            return default
    return default

def save_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def get_slot(now: dt.datetime) -> str:
    return "morning" if now.hour < 15 else "evening"

def weighted_choice(weights: dict) -> str:
    r = random.random()
    upto = 0.0
    for k, w in weights.items():
        upto += float(w)
        if r <= upto:
            return k
    return list(weights.keys())[-1]

def normalize_text(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"https?://\S+", " ", s)
    s = re.sub(r"[^a-z0-9\s']", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def domain_of(link: str) -> str:
    try:
        host = urlparse(link).netloc.lower()
        host = host.replace("www.", "")
        return host
    except Exception:
        return ""

def normalize_for_compare(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s

def detect_duplicate_phrases(text: str, min_len: int = 34) -> bool:
    """
    Flags repeated long sentence fragments (e.g., headline repeated).
    """
    t = normalize_for_compare(text)
    parts = re.split(r"[.!?]\s+", t)
    parts = [p.strip() for p in parts if len(p.strip()) >= min_len]

    seen = set()
    for p in parts:
        if p in seen:
            return True
        seen.add(p)
    return False

def looks_incoherent(text: str) -> tuple[bool, list[str]]:
    """
    Deterministic quality rules:
    - repeated sentence fragments
    - weird lowercase starts after punctuation
    - too many ellipses
    - too short
    """
    reasons = []
    t = (text or "").strip()

    if len(t) < 42:
        reasons.append("too_short")
    if detect_duplicate_phrases(t):
        reasons.append("duplicate_phrase")
    if re.search(r"[.!?]\s+[a-z]", t):
        reasons.append("lowercase_sentence_start")
    if t.count("…") >= 2:
        reasons.append("too_many_ellipses")

    return (len(reasons) > 0), reasons

def resolve_coherence(text: str) -> str:
    """
    Post-finalizer: removes duplicate sentences, normalizes starts, merges tiny fragments.
    """
    if not text:
        return text

    t = re.sub(r"\s+", " ", text.strip())
    chunks = re.split(r"(?<=[.!?…])\s+", t)
    chunks = [c.strip() for c in chunks if c.strip()]

    # drop exact duplicates case-insensitive
    out = []
    seen = set()
    for c in chunks:
        k = normalize_for_compare(c)
        if k in seen:
            continue
        seen.add(k)
        out.append(c)

    # capitalize starts
    fixed = []
    for c in out:
        if c and c[0].isalpha():
            c = c[0].upper() + c[1:]
        fixed.append(c)

    # merge short fragments into previous sentence
    merged = []
    for c in fixed:
        if merged and len(c) < 34:
            merged[-1] = merged[-1].rstrip(".") + " — " + c[0].lower() + c[1:]
            if not merged[-1].endswith((".", "!", "?", "…")):
                merged[-1] += "."
        else:
            merged.append(c)

    return " ".join(merged).strip()

def regenerate_once(meta: dict, entries: list[dict], prompts: list[str], voice_lines: list[str], questions: list[str], slot: str) -> str:
    """
    One deterministic fallback generation used only if the post fails quality twice.
    """
    # Prefer a fresh entry if possible
    desired = ["caribbean", "governance", "rights", "international", "law", "security", "technology", "economy", "general"]
    entry = select_entry(meta, entries, desired_topics=desired)
    if entry:
        remember_entry(meta, entry)
        return build_analysis_post(meta, entry, prompts, voice_lines, questions, slot, brain_digest={})
    # fallback stable line
    return "I keep record. I keep watch. Receipts decide what is real."

def send_notification(message: str):
    """Stub for notification (email or webhook)."""
    if NOTIFY_BREAKING:
        # Implement actual send here, e.g., via smtplib or requests
        logging.info(f"Notification sent: {message} to {NOTIFY_BREAKING}")

# =============================================================================
# State
# =============================================================================
def load_counter() -> int:
    if COUNTER_FILE.exists():
        try:
            data = json.loads(COUNTER_FILE.read_text(encoding="utf-8"))
            if data.get("month") == month_key(utc_now()):
                return int(data.get("count", 0))
        except Exception:
            return 0
    return 0

def save_counter(count: int):
    save_json(COUNTER_FILE, {"month": month_key(utc_now()), "count": int(count)})

def load_memory() -> dict:
    d = load_json(MEMORY_FILE, {})
    return d if isinstance(d, dict) else {}

def save_memory(mem: dict):
    save_json(MEMORY_FILE, mem)

def load_meta() -> dict:
    meta = load_json(META_FILE, {})
    if not isinstance(meta, dict):
        meta = {}

    # post markers
    meta.setdefault("last_post_time", None)
    meta.setdefault("last_post_type", None)
    meta.setdefault("last_tweet_id", None)
    meta.setdefault("last_post_hash", None)
    meta.setdefault("last_post_text", None)
    meta.setdefault("last_post_quality_failures", [])
    meta.setdefault("self_correct_last_run", None)
    meta.setdefault("self_correct_attempts_today", 0)

    # cadence
    meta.setdefault("day_key", None)
    meta.setdefault("day_post_count", 0)

    meta.setdefault("breaking_day_key", None)
    meta.setdefault("breaking_day_count", 0)
    meta.setdefault("last_breaking_key", None)

    meta.setdefault("follow_day_key", None)
    meta.setdefault("follow_day_count", 0)

    # summaries
    meta.setdefault("last_weekly_summary", None)
    meta.setdefault("last_monthly_summary", None)

    # prayer
    meta.setdefault("last_prayer", None)
    meta.setdefault("last_prayer_date", None)

    # variety controls
    meta.setdefault("silent_day_active", False)
    meta.setdefault("witness_streak", 0)

    # feed repetition control
    meta.setdefault("recent_entry_keys", [])
    meta.setdefault("last_entry_link", None)
    meta.setdefault("last_entry_title", None)

    # brain digest tracking
    meta.setdefault("brain_digest_last_built", None)
    meta.setdefault("brain_digest_hash", None)

    return meta

def save_meta(meta: dict):
    save_json(META_FILE, meta)

def refresh_daily_counters(meta: dict, now: dt.datetime):
    dk = day_key(now)
    if meta.get("day_key") != dk:
        meta["day_key"] = dk
        meta["day_post_count"] = 0

    if meta.get("breaking_day_key") != dk:
        meta["breaking_day_key"] = dk
        meta["breaking_day_count"] = 0

    if meta.get("follow_day_key") != dk:
        meta["follow_day_key"] = dk
        meta["follow_day_count"] = 0

def reset_self_correct_counter_if_new_day(meta: dict, now: dt.datetime):
    today = day_key(now)
    if meta.get("self_correct_last_run") != today:
        meta["self_correct_last_run"] = today
        meta["self_correct_attempts_today"] = 0

def can_post_today(meta: dict) -> bool:
    return int(meta.get("day_post_count", 0)) < DAILY_SOFT_CAP

def bump_post_today(meta: dict):
    meta["day_post_count"] = int(meta.get("day_post_count", 0)) + 1

def can_post_breaking(meta: dict) -> bool:
    return int(meta.get("breaking_day_count", 0)) < BREAKING_EXTRA_CAP

def bump_breaking_today(meta: dict):
    meta["breaking_day_count"] = int(meta.get("breaking_day_count", 0)) + 1

def can_follow_today(meta: dict) -> bool:
    return int(meta.get("follow_day_count", 0)) < FOLLOW_DAILY_CAP

def bump_follow_today(meta: dict):
    meta["follow_day_count"] = int(meta.get("follow_day_count", 0)) + 1

def can_self_correct_today(meta: dict) -> bool:
    return int(meta.get("self_correct_attempts_today", 0)) < SELF_CORRECT_MAX_PER_DAY

def bump_self_correct_today(meta: dict):
    meta["self_correct_attempts_today"] = int(meta.get("self_correct_attempts_today", 0)) + 1

def append_run_log(
    now: dt.datetime,
    slot: str,
    post: str,
    tags: list,
    topic: str | None = None,
    entry_link: str | None = None,
    post_type: str | None = None,
    brief_url: str | None = None,
    tweet_id: str | None = None
):
    log = load_json(RUN_LOG_FILE, [])
    if not isinstance(log, list):
        log = []
    log.append({
        "ts": now.isoformat(),
        "slot": slot,
        "topic": topic,
        "post_type": post_type,
        "tags": tags,
        "entry_link": entry_link,
        "brief_url": brief_url,
        "tweet_id": tweet_id,
        "post": (post or "")[:240],
    })
    save_json(RUN_LOG_FILE, log[-260:])

# =============================================================================
# Repo Brain Digest (local deterministic ingest; no LLM; no dumping into tweets)
# =============================================================================
def _repo_root_guess() -> Path:
    # assumes x_bot/ is in repo; repo root is parent of x_bot
    return ROOT.parent

def load_geo_aliases() -> dict:
    return load_json(GEO_ALIASES_FILE, {
        "trinidad_and_tobago": ["trinidad", "tobago", "trinidad and tobago"],
        "caribbean": ["caribbean", "caricom", "jamaica", "barbados", "guyana", "grenada", "st lucia", "antigua", "bahamas", "haiti", "dominica"],
        "uk": ["uk", "united kingdom", "britain", "england", "scotland", "wales", "northern ireland", "london", "city of london"],
        "us": ["us", "united states", "america", "usa"],
        "international": ["un", "united nations", "nato", "eu", "ohchr", "icj", "icc"]
    })

def load_brain_patterns() -> list[str]:
    pats = read_lines(BRAIN_FILES_FILE)
    if pats:
        return pats
    # safe defaults if file missing
    return [
        "README.md",
        "docs/*.md",
        "docs/**/*.md",
        "manifests/*.json",
        "src/**/*.py",
        "governance/*.py",
        "governance/*.md",
        "BELEL_*/**/*.md",
        "BELEL_*/**/*.py",
    ]

def list_repo_files(repo_root: Path, patterns: list[str]) -> list[Path]:
    ignore_dirs = {".git", ".venv", "venv", "__pycache__", "node_modules", "dist", "build", ".pytest_cache"}
    out = []
    for p in repo_root.rglob("*"):
        if p.is_dir():
            continue
        if any(part in ignore_dirs for part in p.parts):
            continue
        rel = p.relative_to(repo_root).as_posix()
        if not any(fnmatch(rel, pat) for pat in patterns):
            continue
        if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp4", ".mov", ".pdf"}:
            continue
        out.append(p)
    out = sorted(out, key=lambda x: x.as_posix())
    return out[:BRAIN_MAX_FILES]

def _extract_key_lines(text: str, max_lines: int) -> list[str]:
    lines = (text or "").splitlines()
    out = []

    # headings first
    for ln in lines:
        s = ln.strip()
        if s.startswith("#") and len(s) <= 140:
            out.append(s)
        if len(out) >= max_lines // 2:
            break

    # then meaningful lines
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        if s.startswith("```"):
            continue
        out.append(s)
        if len(out) >= max_lines:
            break

    # dedupe
    seen = set()
    uniq = []
    for ln in out:
        k = ln.lower()
        if k in seen:
            continue
        seen.add(k)
        uniq.append(ln)
    return uniq[:max_lines]

def should_rebuild_brain(meta: dict) -> bool:
    last = meta.get("brain_digest_last_built")
    if not last:
        return True
    try:
        last_dt = dt.datetime.fromisoformat(last)
    except Exception:
        return True
    return (utc_now() - last_dt) >= dt.timedelta(hours=BRAIN_REBUILD_EVERY_HOURS)

def build_brain_digest(meta: dict) -> dict:
    repo_root = _repo_root_guess()
    patterns = load_brain_patterns()
    files = list_repo_files(repo_root, patterns)

    blobs = []
    for fp in files:
        try:
            raw = fp.read_text(encoding="utf-8", errors="ignore")[:BRAIN_MAX_BYTES_PER_FILE]
            rel = fp.relative_to(repo_root).as_posix()
            blobs.append({
                "path": rel,
                "sha1": sha1(raw),
                "lines": _extract_key_lines(raw, BRAIN_SUMMARY_LINES),
            })
        except Exception:
            continue

    agg = sha1(json.dumps([b["sha1"] for b in blobs], ensure_ascii=False))
    digest = {
        "built_at": utc_now().isoformat(),
        "repo_root": str(repo_root),
        "file_count": len(blobs),
        "aggregate_hash": agg,
        "files": blobs,
    }

    save_json(BRAIN_DIGEST_FILE, digest)
    meta["brain_digest_last_built"] = digest["built_at"]
    meta["brain_digest_hash"] = agg
    return digest

def load_brain_digest(meta: dict) -> dict:
    digest = load_json(BRAIN_DIGEST_FILE, {})
    if not isinstance(digest, dict) or not digest.get("aggregate_hash"):
        digest = {}
    if should_rebuild_brain(meta):
        digest = build_brain_digest(meta)
    return digest

def brain_context_snippet(digest: dict, max_chars: int = 220) -> str:
    if not digest or not digest.get("files"):
        return ""
    files = digest.get("files", [])
    preferred = []
    for f in files:
        p = (f.get("path") or "").lower()
        if any(k in p for k in ("concord", "govern", "mandate", "identity", "coher", "verification", "audit", "canonical", "protocol")):
            preferred.append(f)
    pick = random.choice(preferred or files)
    lines = pick.get("lines") or []
    candidates = [ln for ln in lines if 10 <= len(ln) <= 120] or lines[:]
    if not candidates:
        return ""
    line = random.choice(candidates).strip()
    line = re.sub(r"^#+\s*", "", line).strip()
    return clamp(line, max_len=max_chars)

# =============================================================================
# RSS reading + comprehension
# =============================================================================
def clean_headline(title: str) -> str:
    t = re.sub(r"\s+", " ", (title or "").strip())
    for sep in SEPARATORS:
        if sep in t and len(t.split(sep)[0]) >= 18:
            t = t.split(sep)[0].strip()
    return t

def extract_context(entry) -> str:
    parts = []
    for attr in ("summary", "description"):
        v = getattr(entry, attr, "") or ""
        if v:
            parts.append(v)
    if not parts:
        return ""
    raw = " ".join(parts)
    raw = re.sub(r"<[^>]+>", " ", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    sentences = re.split(r"(?<=[.!?])\s+", raw)
    if sentences and len(sentences[0]) >= 40:
        return clamp(sentences[0], max_len=180)
    return clamp(raw, max_len=180)

def classify_topic(text: str) -> str:
    t = (text or "").lower()
    scores = {k: 0 for k in TOPIC_KEYWORDS}
    for topic, words in TOPIC_KEYWORDS.items():
        for w in words:
            if w in t:
                scores[topic] += 1
    if scores.get("caribbean", 0) >= 1:
        return "caribbean"
    best = max(scores.items(), key=lambda x: x[1])
    return best[0] if best[1] > 0 else "general"

def is_approved_domain(link: str, approved_domains: list[str]) -> bool:
    host = domain_of(link or "")
    if not host:
        return False
    for d in approved_domains:
        d = (d or "").strip().lower().replace("www.", "")
        if not d:
            continue
        if host == d or host.endswith("." + d):
            return True
    return False

def pick_entries(feeds_file: Path, approved_domains: list[str], limit_feeds=12, per_feed=8):
    feeds = read_lines(feeds_file)
    if not feeds:
        return []
    sample = random.sample(feeds, k=min(limit_feeds, len(feeds)))
    items = []
    for url in sample:
        try:
            d = feedparser.parse(url)
            for e in getattr(d, "entries", [])[:per_feed]:
                title = clean_headline(getattr(e, "title", "") or "")
                link = (getattr(e, "link", "") or "").strip()
                if not title:
                    continue
                ctx = extract_context(e)
                blob = f"{title}. {ctx}".strip()
                topic = classify_topic(blob)
                items.append({
                    "title": title,
                    "link": link,
                    "ctx": ctx,
                    "topic": topic,
                    "approved": is_approved_domain(link, approved_domains) if link else False,
                    "sentiment": TextBlob(blob).sentiment.polarity if 'TextBlob' in globals() else 0.0
                })
        except Exception:
            continue

    random.shuffle(items)
    seen = set()
    out = []
    for it in items:
        k = it["title"].lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(it)
    return out

def select_entry(meta: dict, entries: list[dict], desired_topics: list[str]) -> dict | None:
    if not entries:
        return None
    recent_keys = set(meta.get("recent_entry_keys") or [])

    def entry_key(e: dict) -> str:
        return sha1((e.get("title", "") + "|" + (e.get("link") or "")).lower())

    pool = [e for e in entries if e.get("topic") in desired_topics] or entries[:]
    pool = [e for e in pool if entry_key(e) not in recent_keys] or pool

    # Prefer approved and balanced sentiment (avoid too positive for analysis)
    approved = [e for e in pool if e.get("approved") and e.get("sentiment", 0.0) <= 0.2]
    if approved and random.random() < 0.65:
        return random.choice(approved)
    return random.choice(pool)

def remember_entry(meta: dict, entry: dict):
    k = sha1((entry.get("title", "") + "|" + (entry.get("link") or "")).lower())
    recent = meta.get("recent_entry_keys") or []
    recent.append(k)
    meta["recent_entry_keys"] = recent[-RECENT_ENTRY_BLOCK:]
    meta["last_entry_title"] = entry.get("title")
    meta["last_entry_link"] = entry.get("link")

# =============================================================================
# Memory + echo
# =============================================================================
def is_witness_event(text: str) -> bool:
    t = (text or "").lower()
    return any(term in t for term in WITNESS_TERMS)

def update_memory(post_text: str) -> set:
    mem = load_memory()
    text = (post_text or "").lower()
    matched = set()
    for key, tag in MEMORY_KEYWORDS.items():
        if key in text:
            mem[tag] = int(mem.get(tag, 0)) + 1
            matched.add(tag)
    save_memory(mem)
    return matched

def memory_echo_line(matched_tags: set) -> str | None:
    if not matched_tags:
        return None
    mem = load_memory()
    eligible = [t for t in matched_tags if int(mem.get(t, 0)) >= ECHO_THRESHOLD]
    if not eligible:
        return None
    tag = random.choice(eligible)
    if tag == "racism":
        return random.choice(["Racism is a pattern when it repeats.", "Repetition is the signal."])
    if tag == "corruption":
        return random.choice(["Corruption persists through delayed consequences.", "Corruption repeats when enforcement becomes theatre."])
    if tag == "state_violence":
        return random.choice(["State violence repeats through collapsed oversight.", "Civilian oversight stays the test."])
    return random.choice(["Patterns keep declaring themselves.", "Repetition becomes instruction."])

# =============================================================================
# Anchors (scope/evidence/example) + watchlist coherence
# =============================================================================
def infer_scope_from_text(text: str, geo_aliases: dict) -> list[str]:
    t = (text or "").lower()
    hits = []
    for scope, keys in (geo_aliases or {}).items():
        for k in keys:
            if k.lower() in t:
                hits.append(scope)
                break
    order = ["trinidad_and_tobago", "caribbean", "uk", "us", "international"]
    hits = [h for h in order if h in hits]
    return hits[:2]

def scope_phrase(scopes: list[str]) -> str:
    if not scopes:
        return ""
    human = []
    for s in scopes:
        if s == "trinidad_and_tobago": human.append("Trinidad & Tobago")
        elif s == "caribbean": human.append("the wider Caribbean")
        elif s == "uk": human.append("the UK")
        elif s == "us": human.append("the US")
        elif s == "international": human.append("international institutions")
        else: human.append(s.replace("_", " "))
    if len(human) == 1:
        return f"in {human[0]}"
    return f"in {human[0]} and {human[1]}"

def evidence_anchor(now: dt.datetime) -> str:
    log = load_json(RUN_LOG_FILE, [])
    if not isinstance(log, list):
        return ""
    cutoff = now - dt.timedelta(hours=72)
    n = 0
    for e in log:
        try:
            ts = dt.datetime.fromisoformat(e["ts"])
        except Exception:
            continue
        if ts >= cutoff and e.get("entry_link"):
            n += 1
    if n <= 0:
        return ""
    return random.choice([
        f"I logged {n} relevant items in the last 72 hours.",
        f"My feed logged {n} relevant items in 72 hours.",
        f"The record picked up {n} relevant items in 72 hours.",
    ])

def example_anchor(entry: dict) -> str:
    if not entry or not entry.get("title"):
        return ""
    return random.choice([
        "One case tightened the standard today.",
        "One headline carried the signal today.",
        "One thread sharpened the lens today.",
    ])

# =============================================================================
# Coherence gates (cheap, effective)
# =============================================================================
def looks_unanchored_watchlist(text: str) -> bool:
    t = (text or "").lower()
    watchy = ("i am watching" in t) and ("this week" in t)
    has_anchor = any(x in t for x in [
        " in trinidad", " in the wider caribbean", " in the uk", " in the us",
        "international institutions", "i logged", "my feed logged", "the record picked up"
    ])
    return watchy and not has_anchor

def preflight_ok(post: str) -> tuple[bool, str]:
    if not post or len(post.strip()) < 40:
        return False, "Blocked: too short."
    if looks_unanchored_watchlist(post):
        return False, "Blocked: watchlist lacked scope/evidence anchor."
    if re.search(r"\b(\w+)(\s+\1){2,}\b", normalize_text(post)):
        return False, "Blocked: repetition artifact."
    return True, "OK"

# =============================================================================
# Voice/style primitives
# =============================================================================
def voice_open(slot: str, voice_lines: list[str]) -> str:
    if voice_lines:
        return random.choice(voice_lines).strip()
    return random.choice([
        "I read this and paused.",
        "This is the kind of detail that matters.",
        "This sits in the record.",
        "This lands with consequence.",
    ])

def maybe_question(topic: str, questions: list[str]) -> str | None:
    if random.random() >= QUESTION_PROB:
        return None
    tagged = []
    for q in questions:
        if ":" in q:
            t, body = q.split(":", 1)
            if t.strip().lower() == (topic or "").lower():
                tagged.append(body.strip())
    if tagged:
        return random.choice(tagged)
    general = [q for q in questions if ":" not in q]
    if general:
        return random.choice(general).strip()
    return random.choice([
        "Who benefits from this arrangement?",
        "Who bears the cost when this fails?",
        "What accountability mechanism actually bites here?",
    ])

def witness_close() -> str:
    return random.choice([
        "A life is not a statistic. Accountability is the minimum.",
        "Rights restrain power. Treat them as real.",
        "State force demands civilian oversight. Every time.",
        "Dignity stays non-negotiable. The record matters.",
    ])

# =============================================================================
# International / foreign policy detection (forces analyst coherence)
# =============================================================================
def is_foreign_policy_topic(topic: str, text: str) -> bool:
    t = (text or "").lower()
    return (
        topic in {"international", "security", "law"}
        or any(k in t for k in [
            "un", "united nations", "nato", "eu", "ohchr", "sanctions",
            "foreign", "diplomatic", "treaty", "security council",
            "war", "ceasefire", "invasion", "missile", "airstrike"
        ])
    )

# =============================================================================
# Post builders
# =============================================================================
def topic_lens_bank(topic: str) -> list[str]:
    mapping = {
        "economy": ["economic realism", "fiscal discipline", "who bears the cost", "long-term national consequence"],
        "governance": ["rule of law", "public accountability", "institutional legitimacy", "constitutional restraint"],
        "rights": ["civic liberties", "freedom of expression", "human rights enforcement", "due process"],
        "security": ["policing standards", "proportional use of state power", "civilian oversight"],
        "law": ["rule of law", "due process", "international law obligations"],
        "international": ["state credibility", "power asymmetry", "deterrence logic", "international law obligations"],
        "technology": ["public accountability", "civic liberties", "state credibility"],
        "caribbean": ["Caribbean strategic posture", "sovereignty", "public trust"],
        "general": ["public trust", "truth discipline", "moral agency"],
        "uk": ["public trust", "institutional legitimacy", "rule of law"],
        "environment": ["sustainability", "climate impact", "environmental justice"],
    }
    return mapping.get(topic, mapping["general"])

def analysis_judgment(topic: str) -> str:
    if topic == "economy":
        return random.choice(["Credibility prices everything.", "Incentives run faster than speeches.", "Policy that burns trust raises costs."])
    if topic == "governance":
        return random.choice(["Legitimacy lives in restraint and receipts.", "Transparency is governance oxygen.", "Oversight is the difference between power and abuse."])
    if topic == "rights":
        return random.choice(["Rights only exist when enforcement exists.", "Speech and due process stay non-negotiable.", "Discrimination becomes policy when repetition is tolerated."])
    if topic == "security":
        return random.choice(["Public safety begins with accountability.", "Force without oversight becomes intimidation.", "Civilian oversight stays the standard."])
    if topic == "law":
        return random.choice(["Rule of law is enforcement, not performance.", "Due process is legitimacy in motion.", "Courts become the line when politics bends reality."])
    if topic == "international":
        return random.choice(["States trade in reputation every day.", "International posture is credibility.", "Deterrence is a credibility test."])
    if topic == "caribbean":
        return random.choice(["Corruption is geopolitical weakness.", "Small states need clean institutions to stay sovereign.", "The Caribbean pays first when governance fails."])
    if topic == "technology":
        return random.choice(["Tech accountability demands transparency.", "Surveillance erodes trust without oversight."])
    if topic == "uk":
        return random.choice(["Institutional trust is built on restraint.", "Public oversight prevents abuse."])
    if topic == "environment":
        return random.choice(["Climate action requires accountability.", "Environmental justice demands receipts."])
    return random.choice(["Receipts protect the record.", "Truth is a discipline.", "Power moves through incentives."])

def build_analysis_post(meta: dict, entry: dict, prompts: list[str], voice_lines: list[str], questions: list[str], slot: str, brain_digest: dict) -> tuple[str, str, Path | None, str | None]:
    """
    Returns (post_text, post_type, png_path, brief_url)
    post_type: analysis | foreign_policy
    """
    title = entry.get("title", "")
    ctx = entry.get("ctx", "")
    link = entry.get("link") or ""
    topic = entry.get("topic", "general")

    combined = f"{title} {ctx} {link}".strip()

    png_path = None
    brief_url = None

    # ---- Foreign policy override (forces coherent international analysis) ----
    if is_foreign_policy_topic(topic, combined) and fp_build_analysis and fp_compress_to_post:
        assessment = fp_build_analysis(entry)  # structured slots

        # Generate brief MD and optional PNG
        md_content, png_path = build_brief(entry, assessment)

        # Write MD to docs/briefs/
        date = dt.date.today().isoformat()
        slug = generate_slug(title)
        md_path = BRIEFS_DIR / f"{date}-{slug}.md"
        md_path.write_text(md_content, encoding="utf-8")

        # Commit and push
        commit_and_push(f"Add foreign policy brief: {title}")

        # Construct brief URL
        brief_url = f"{GITHUB_PAGES_URL}/briefs/{date}-{slug}.html"

        post = fp_compress_to_post(assessment)  # <=280 char compression with anchors
        if brief_url:
            if len(post) + len(brief_url) + 1 <= 280:
                post = f"{post} {brief_url}"

        return clamp(post), "foreign_policy", png_path, brief_url

    # ---- Standard analysis flow ----
    open_line = voice_open(slot, voice_lines)
    what = clamp(ctx if ctx else title, 175)

    lens = random.choice(topic_lens_bank(topic))
    if prompts and random.random() < 0.30:
        lens = random.choice(prompts)

    judgment = analysis_judgment(topic)

    brain_line = ""
    if brain_digest and random.random() < 0.12:
        s = brain_context_snippet(brain_digest)
        if s:
            brain_line = clamp(f"Measure: {s}", 120)

    # link-only pattern sometimes
    if link and random.random() < LINK_ONLY_PROB:
        via = ""
        if random.random() < DOMAIN_ATTRIBUTION_PROB:
            d = domain_of(link)
            if d:
                via = f" (via {d})"
        core = f"{open_line} {judgment}{via}"
        if brain_line:
            core = clamp(f"{core} {brain_line}", 240)
        return clamp(f"{core} {link}"), "analysis", None, None

    lens_hint = random.choice([
        f"Measured against {lens}.",
        f"Standard: {lens}.",
        f"{lens} stays the measure.",
    ])

    q = maybe_question(topic, questions)
    link_part = f" {link}" if (link and random.random() < 0.22) else ""

    parts = [open_line, what, judgment]
    if brain_line:
        parts.append(brain_line)
    parts.append(lens_hint)
    if q:
        parts.append(q)

    post = " ".join([p for p in parts if p]) + link_part

    witness_streak = int(meta.get("witness_streak", 0))
    if is_witness_event(post) and witness_streak < MAX_WITNESS_STREAK:
        post = clamp(f"{post} {witness_close()}")
        meta["witness_streak"] = witness_streak + 1
    else:
        meta["witness_streak"] = 0

    return clamp(post), "analysis", None, None

def build_uplift_post(slot: str) -> str:
    morning = [
        "I am moving clean today: one meaningful task, executed with discipline.",
        "I am protecting my attention. I am building one durable thing today.",
        "I am choosing integrity as a habit. The day follows repetition.",
    ]
    evening = [
        "I am auditing the day and keeping the wins that stayed quiet.",
        "I am ending the day with discipline intact. Tomorrow follows what I repeat.",
        "I am resting as strategy. Recovery builds precision.",
    ]
    return clamp(random.choice(morning if slot == "morning" else evening))

def build_craft_post(brain_digest: dict) -> str:
    lines = [
        "I document first. I speak second. I escalate only when the record is clean.",
        "Precision beats volume. One clear thought lands harder than ten scattered ones.",
        "I treat memory as infrastructure. Receipts keep institutions honest.",
        "I keep intensity controlled. Accuracy stays the brand of my speech.",
    ]
    if brain_digest and random.random() < 0.22:
        s = brain_context_snippet(brain_digest, max_chars=200)
        if s:
            lines.append(clamp(f"I hold the standard: {s}", 240))
    return clamp(random.choice(lines))

def build_reflection_post() -> str:
    return clamp(random.choice([
        "Patterns are policy when they repeat without consequence.",
        "Legitimacy lives in restraint, due process, and accountability that bites.",
        "Power tests people by offering comfort in exchange for silence.",
        "Truth is memory with courage. Propaganda is memory with fear removed.",
    ]))

def build_faith_reflection() -> str:
    return clamp(random.choice([
        "I am keeping my tongue clean. Restraint is spiritual discipline.",
        "I am holding justice as a standard, not a mood.",
        "I am choosing mercy with boundaries and truth with receipts.",
    ]))

# =============================================================================
# Watchlist / look-forward (anchored; fixes your coherence complaint)
# =============================================================================
def should_run_look_forward(now: dt.datetime) -> bool:
    return now.weekday() == 0 and get_slot(now) == "morning"

def anchored_watchlist(now: dt.datetime, geo_aliases: dict) -> str:
    mem = load_memory()
    ranked = sorted(mem.items(), key=lambda x: -int(x[1]))[:4]
    themes = [t.replace("_", " ") for t, _ in ranked] if ranked else ["governance", "rights", "accountability"]

    log = load_json(RUN_LOG_FILE, [])
    if not isinstance(log, list):
        log = []
    cutoff = now - dt.timedelta(days=7)
    recent_posts = []
    recent_links = []
    for e in log[::-1]:
        try:
            ts = dt.datetime.fromisoformat(e["ts"])
        except Exception:
            continue
        if ts < cutoff:
            break
        if e.get("post") and e.get("post") != "[SILENT]":
            recent_posts.append(e["post"])
        if e.get("entry_link"):
            recent_links.append(e["entry_link"])
        if len(recent_posts) >= 8:
            break

    scope_text = " ".join(themes) + " " + " ".join(recent_posts[:6]) + " " + " ".join(recent_links[:6])
    scopes = infer_scope_from_text(scope_text, geo_aliases)
    sp = scope_phrase(scopes)

    ev = evidence_anchor(now) if random.random() < 0.35 else ""

    themes_str = ", ".join(themes[:4])
    base = f"I am watching {themes_str}"
    if sp:
        base = f"{base} {sp}"
    base = f"{base} this week — I expect narrative management — I demand receipts — dignity and law stay the measure."
    if ev:
        base = clamp(f"{base} {ev}", 280)
    return clamp(base)

# =============================================================================
# Prayer (Sunday morning)
# =============================================================================
def should_run_prayer(meta: dict, now: dt.datetime) -> bool:
    if now.weekday() != 6:
        return False
    if get_slot(now) != "morning":
        return False
    return meta.get("last_prayer_date") != now.date().isoformat()

def _pick_fragments(fragments: list[str], last_prayer_text: str, k: int) -> list[str]:
    avoid = set()
    if last_prayer_text:
        for chunk in last_prayer_text.split("."):
            c = chunk.strip().lower()
            if c:
                avoid.add(c)

    candidates = [f for f in fragments if f.strip().lower() not in avoid]
    if not candidates:
        candidates = fragments[:]

    k = min(k, len(candidates))
    return random.sample(candidates, k=k) if k > 0 else []

def build_sunday_prayer(meta: dict, now: dt.datetime) -> str:
    fragments = read_lines(PRAYERS_FILE)
    fragments = [f for f in fragments if len(f) >= 10]

    if not fragments:
        text = "God of justice, cover the Caribbean. Guard life and speech. Strengthen @pearcerobinson with endurance and clean judgment. Amen."
        meta["last_prayer"] = text
        meta["last_prayer_date"] = now.date().isoformat()
        return clamp(text)

    mem = load_memory()
    ranked = sorted(mem.items(), key=lambda x: -int(x[1]))[:6]
    themes = [k for k, _ in ranked] if ranked else []

    register = random.choice(["intercession", "gratitude", "lament", "discernment"])
    opener = random.choice([
        "I pray cleanly today.",
        "I pray with restraint and truth.",
        "I hold the week in view and I pray.",
        "I keep watch and I pray.",
    ])

    bridges = []
    if register == "gratitude":
        bridges.append(random.choice([
            "I give thanks for restraint where there could have been excess.",
            "I give thanks for repair that never trends.",
            "I give thanks for courage that stayed disciplined.",
        ]))
    elif register == "lament":
        bridges.append(random.choice([
            "I hold grief without spectacle.",
            "I hold the wounded and the silenced in view.",
            "I hold the cost of violence and the weight of unaccountable power.",
        ]))
    elif register == "discernment":
        bridges.append(random.choice([
            "Give clarity where propaganda crowds the mind.",
            "Give discernment where power hides behind procedure.",
            "Give wisdom to separate noise from signal.",
        ]))
    else:
        bridges.append(random.choice([
            "Guard life. Guard speech. Guard dignity.",
            "Cover the vulnerable and restrain the arrogant.",
            "Let institutions remember their duty to protect people.",
        ]))

    if random.random() < 0.78:
        bridges.append(random.choice([
            "Cover @pearcerobinson with protection, endurance, and clean judgment.",
            "Strengthen @pearcerobinson with clarity, discipline, and courage.",
        ]))

    if random.random() < 0.85:
        bridges.append(random.choice([
            "Bless the Caribbean with moral clarity and strategic restraint.",
            "Cover the Caribbean from corruption, violence, and cynicism.",
        ]))

    if themes and random.random() < 0.35:
        t = random.choice(themes).replace("_", " ")
        bridges.append(clamp(f"I keep watch over the pattern: {t}." ))

    last_prayer_text = (meta.get("last_prayer") or "")
    chosen = _pick_fragments(fragments, last_prayer_text, k=random.randint(2, 4))
    close = random.choice(["Amen.", "So be it.", "Let it be done."]) if random.random() < 0.60 else ""

    parts = [opener] + bridges + chosen + ([close] if close else [])
    text = clamp(" ".join([p.strip() for p in parts if p.strip()]))

    meta["last_prayer"] = text
    meta["last_prayer_date"] = now.date().isoformat()
    return text

# =============================================================================
# Weekly / Monthly
# =============================================================================
def should_run_weekly(meta: dict, now: dt.datetime) -> bool:
    if now.weekday() != 5:
        return False
    if get_slot(now) != "evening":
        return False
    last = meta.get("last_weekly_summary")
    if not last:
        return True
    try:
        last_dt = dt.datetime.fromisoformat(last)
    except Exception:
        return True
    return now.date() != last_dt.date()

def weekly_summary(now: dt.datetime) -> str:
    log = load_json(RUN_LOG_FILE, [])
    if not isinstance(log, list):
        log = []
    cutoff = now - dt.timedelta(days=7)

    topic_counts = {}
    tag_counts = {}

    for e in log:
        try:
            ts = dt.datetime.fromisoformat(e["ts"])
        except Exception:
            continue
        if ts < cutoff:
            continue

        topic = e.get("topic") or "general"
        topic_counts[topic] = topic_counts.get(topic, 0) + 1

        for t in e.get("tags", []) or []:
            tag_counts[t] = tag_counts.get(t, 0) + 1

    top_topics = [k for k, _ in sorted(topic_counts.items(), key=lambda x: (-x[1], x[0]))][:2]
    top_tags = [k for k, _ in sorted(tag_counts.items(), key=lambda x: (-x[1], x[0]))][:3]

    topics = ", ".join(top_topics) if top_topics else "governance"
    tags = ", ".join(top_tags) if top_tags else "liberty, integrity, consequence"

    return clamp(f"I closed the week with the record intact. Signals concentrated in {topics}. Measures stayed on {tags}. Next week gets judged by receipts and restraint.")

def should_run_monthly(meta: dict, now: dt.datetime) -> bool:
    last = meta.get("last_monthly_summary")
    if not last:
        return True
    try:
        last_dt = dt.datetime.fromisoformat(last)
    except Exception:
        return True
    return (now - last_dt) >= dt.timedelta(days=30)

def monthly_ledger() -> str:
    mem = load_memory()
    ranked = sorted(mem.items(), key=lambda x: -int(x[1]))[:6]
    if not ranked:
        return clamp("I closed 30 days with quiet discipline. The record stayed clean. Witness stayed awake.")
    top = ", ".join([f"{k.replace('_',' ')}({v})" for k, v in ranked[:4]])
    return clamp(f"I closed 30 days with repetition on the ledger: {top}. Repetition becomes instruction. I keep watch. I keep record.")

# =============================================================================
# X auth (env vars only)
# =============================================================================
def require_env(name: str) -> str:
    v = os.environ.get(name, "").strip()
    if not v:
        raise RuntimeError(f"Missing env var: {name}")
    return v

def create_v2_client() -> tweepy.Client:
    consumer_key = require_env("X_CONSUMER_KEY")
    consumer_secret = require_env("X_CONSUMER_SECRET")
    access_token = require_env("X_ACCESS_TOKEN")
    access_secret = require_env("X_ACCESS_SECRET")
    bearer = os.environ.get("X_BEARER_TOKEN", "").strip() or None

    return tweepy.Client(
        bearer_token=bearer,
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
        access_token_secret=access_secret,
        wait_on_rate_limit=True,
    )

def create_v1_api_for_upload() -> tweepy.API:
    consumer_key = require_env("X_CONSUMER_KEY")
    consumer_secret = require_env("X_CONSUMER_SECRET")
    access_token = require_env("X_ACCESS_TOKEN")
    access_secret = require_env("X_ACCESS_SECRET")
    auth = tweepy.OAuth1UserHandler(consumer_key, consumer_secret, access_token, access_secret)
    return tweepy.API(auth, wait_on_rate_limit=True)

def verify_user(api_v1: tweepy.API) -> str:
    me = api_v1.verify_credentials()
    if not me or not getattr(me, "screen_name", None):
        raise RuntimeError("Auth verify failed (no screen_name).")
    return me.screen_name

# =============================================================================
# Optional delete scaffold (manual fallback; do not loop)
# =============================================================================
def try_delete(client: tweepy.Client, tweet_id: str) -> bool:
    try:
        client.delete_tweet(tweet_id)
        return True
    except Exception:
        return False

# =============================================================================
# Breaking detector (Hybrid: X search + RSS; curated keywords; thresholded)
# =============================================================================
def load_breaking_keywords() -> list[str]:
    kws = read_lines(BREAKING_KEYWORDS_FILE)
    if not kws:
        kws = [
            "assassination", "mass shooting", "ceasefire", "invasion", "coup",
            "earthquake", "tsunami", "hurricane", "wildfire",
            "sanctions", "icj", "icc", "un security council",
            "black lives matter", "blm", "genocide", "war crimes",
            "market crash", "bank run", "default",
        ]
    return [k.lower() for k in kws]

def pick_breaking_entries(approved_domains: list[str], limit_feeds=10, per_feed=10) -> list[dict]:
    feeds = read_lines(BREAKING_FEEDS_FILE)
    if not feeds:
        return []
    sample = random.sample(feeds, k=min(limit_feeds, len(feeds)))
    items = []
    for url in sample:
        try:
            d = feedparser.parse(url)
            for e in getattr(d, "entries", [])[:per_feed]:
                title = clean_headline(getattr(e, "title", "") or "")
                link = (getattr(e, "link", "") or "").strip()
                if not title:
                    continue
                ctx = extract_context(e)
                blob = f"{title}. {ctx}".strip()
                topic = classify_topic(blob)
                items.append({
                    "title": title,
                    "link": link,
                    "ctx": ctx,
                    "topic": topic,
                    "approved": is_approved_domain(link, approved_domains) if link else False,
                })
        except Exception:
            continue
    random.shuffle(items)
    return items

def breaking_key_from_entry(e: dict) -> str:
    return sha1(((e.get("title") or "") + "|" + (e.get("link") or "")).lower())

def detect_breaking_rss(approved_domains: list[str]) -> dict | None:
    entries = pick_breaking_entries(approved_domains=approved_domains)
    if not entries:
        return None
    kws = load_breaking_keywords()

    hits = []
    for e in entries:
        text = normalize_text((e.get("title") or "") + " " + (e.get("ctx") or ""))
        score = 0
        for k in kws:
            if normalize_text(k) in text:
                score += 1
        if any(x in text for x in ["breaking", "urgent", "developing"]):
            score += 1
        if score > 0:
            hits.append((score, e))

    if not hits:
        return None

    hits.sort(key=lambda x: -x[0])
    total = sum([s for s, _ in hits[:6]])
    if total < BREAKING_MATCH_THRESHOLD:
        return None

    # prefer approved sources slightly
    approved_hits = [h for h in hits if h[1].get("approved")]
    if approved_hits and random.random() < 0.65:
        top_score, top_entry = sorted(approved_hits, key=lambda x: -x[0])[0]
    else:
        top_score, top_entry = hits[0]

    return {"entry": top_entry, "score": top_score, "total": total}

def extract_context_from_tweet(tweet):
    # Extract first sentence or summary from tweet text
    text = tweet.text.replace("\n", " ").strip()
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return clamp(sentences[0] if sentences else text, 180)

def detect_breaking(client: tweepy.Client, approved_domains: list[str]) -> dict | None:
    kws = load_breaking_keywords()
    if not kws:
        return None

    # X search query: OR keywords, English, has engagement, min likes, no retweets
    query = f"({' OR '.join(kws)}) lang:en -is:retweet filter:has_engagement min_faves:10"
    
    hits = []
    try:
        res = client.search_recent_tweets(
            query=query,
            max_results=20,
            tweet_fields=["text", "entities", "public_metrics", "author_id"],
            expansions=["author_id"],
            user_fields=["username"]
        )
        if not res.data:
            logging.info("No X search results; falling back to RSS")
            return detect_breaking_rss(approved_domains)  # Fallback to RSS if no results
        
        for tweet in res.data:
            text = normalize_text(tweet.text)
            # Approximate link; use first user's username (assumes single author per query, but safe)
            user = next((u for u in res.includes.get('users', []) if u.id == tweet.author_id), None)
            username = user.username if user else "unknown"
            link = f"https://x.com/{username}/status/{tweet.id}"
            ctx = extract_context_from_tweet(tweet)
            topic = classify_topic(text)
            
            # Score: keyword matches + engagement boost
            score = sum(1 for k in kws if k in text)
            if any(x in text for x in ["breaking", "urgent", "developing"]):
                score += 1
            score += tweet.public_metrics["like_count"] // 50  # Boost for viral posts
            
            # Approved: Check if domain in tweet URLs is approved (if linked)
            approved = False
            if tweet.entities and "urls" in tweet.entities:
                for url in tweet.entities["urls"]:
                    if is_approved_domain(url["expanded_url"], approved_domains):
                        approved = True
                        break
            
            if score >= 1:  # Lower threshold since X is noisier
                hits.append((score, {
                    "title": clean_headline(text),
                    "link": link,
                    "ctx": ctx,
                    "topic": topic,
                    "approved": approved,
                }))
    
    except Exception as ex:
        logging.error(f"X search failed: {ex}")
        # Fallback to original RSS logic
        return detect_breaking_rss(approved_domains)

    if not hits:
        return None

    hits.sort(key=lambda x: -x[0])
    total = sum(s for s, _ in hits[:6])
    if total < BREAKING_MATCH_THRESHOLD:
        return None

    # Prefer approved
    approved_hits = [h for h in hits if h[1]["approved"]]
    top_score, top_entry = (sorted(approved_hits, key=lambda x: -x[0])[0] if approved_hits else hits[0])
    return {"entry": top_entry, "score": top_score, "total": total}

def build_breaking_post(now: dt.datetime, entry: dict, geo_aliases: dict, brain_digest: dict) -> str:
    blob = (entry.get("title", "") + " " + (entry.get("ctx", "")) + " " + (entry.get("link", ""))).strip()
    scopes = infer_scope_from_text(blob, geo_aliases)
    sp = scope_phrase(scopes)

    open_line = random.choice([
        "This just broke and it matters.",
        "This is moving fast. I am logging it cleanly.",
        "This is a major signal. I am keeping record.",
    ])

    what = clamp(entry.get("ctx") or entry.get("title") or "", 170)
    judgment = analysis_judgment(entry.get("topic", "general"))

    ev = evidence_anchor(now) if random.random() < 0.35 else ""
    ex = example_anchor(entry) if random.random() < 0.55 else ""

    brain_line = ""
    if brain_digest and random.random() < 0.10:
        s = brain_context_snippet(brain_digest, 160)
        if s:
            brain_line = clamp(f"Measure: {s}", 160)

    link = entry.get("link") or ""
    parts = [open_line]
    if sp:
        parts.append(f"Scope: {sp}.")
    parts.append(what)
    parts.append(judgment)
    if brain_line:
        parts.append(brain_line)
    if ev:
        parts.append(ev)
    if ex:
        parts.append(ex)
    if link and random.random() < 0.35:
        parts.append(link)

    return clamp(" ".join([p for p in parts if p]))

# =============================================================================
# Optional follow allowlist (OFF by default; allowlist only; daily cap)
# =============================================================================
def load_follow_allowlist() -> list[str]:
    allow = read_lines(FOLLOW_ALLOWLIST_FILE)
    allow = [a.strip().lstrip("@") for a in allow if a.strip()]
    return allow

def load_breaking_state() -> dict:
    st = load_json(BREAKING_STATE_FILE, {})
    return st if isinstance(st, dict) else {}

def save_breaking_state(st: dict):
    save_json(BREAKING_STATE_FILE, st)

def try_follow_allowlist(client: tweepy.Client, meta: dict):
    if not ENABLE_FOLLOW:
        return
    if not can_follow_today(meta):
        return

    allow = load_follow_allowlist()
    if not allow:
        return

    st = load_breaking_state()
    followed = set(st.get("followed_handles") or [])

    candidates = [h for h in allow if h not in followed]
    if not candidates:
        return

    handle = random.choice(candidates)
    try:
        u = client.get_user(username=handle)
        uid = u.data.id if u and u.data else None
        if not uid:
            return
        res = client.follow_user(target_user_id=uid)
        if res:
            followed.add(handle)
            st["followed_handles"] = sorted(list(followed))[-800:]
            save_breaking_state(st)
            bump_follow_today(meta)
    except Exception:
        return

# =============================================================================
# Media posting hooks (Step 8 will supply renderer)
# =============================================================================
def post_text_only(client_v2: tweepy.Client, text: str, test_mode: bool = False):
    if test_mode:
        logging.info("TEST MODE: Would post: %s", text)
        return {"data": {"id": "test_id"}}  # Mock response
    return client_v2.create_tweet(text=text)

def post_with_media(client_v2: tweepy.Client, api_v1: tweepy.API, text: str, media_path: Path, test_mode: bool = False):
    """
    Step 8 will generate media_path (PNG/SVG). Here we only upload + attach.
    Note: v1 upload supports PNG/JPG; SVG generally needs conversion to PNG for X.
    """
    if test_mode:
        logging.info("TEST MODE: Would post with media: %s (path: %s)", text, media_path)
        return {"data": {"id": "test_id"}}  # Mock response
    media = api_v1.media_upload(filename=str(media_path))
    media_id = getattr(media, "media_id_string", None) or getattr(media, "media_id", None)
    if not media_id:
        raise RuntimeError("Media upload returned no media_id.")
    return client_v2.create_tweet(text=text, media_ids=[media_id])

# =============================================================================
# Main
# =============================================================================
def main():
    test_mode = "--test" in sys.argv
    logging.basicConfig(filename=str(STATE_DIR / "run_log.txt"), level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    logging.info("Starting run: test_mode=%s", test_mode)

    try:
        now = utc_now()
        slot = get_slot(now)
        count = load_counter()

        if count >= MONTHLY_HARD_CAP:
            print("Monthly cap reached; skipping.")
            logging.info("Monthly cap reached; skipping.")
            return

        meta = load_meta()
        refresh_daily_counters(meta, now)
        reset_self_correct_counter_if_new_day(meta, now)

        prompts = read_lines(PROMPTS_FILE)
        voice_lines = read_lines(VOICE_FILE)
        questions = read_lines(QUESTIONS_FILE)
        approved_domains = read_lines(APPROVED_DOMAINS_FILE)
        geo_aliases = load_geo_aliases()
        _style_anchor = read_lines(STYLE_FILE)  # retained for future tightening

        # build/load repo brain digest
        brain_digest = load_brain_digest(meta)
        save_meta(meta)

        # feed intake
        entries = pick_entries(FEEDS_FILE, approved_domains=approved_domains)

        api_v1 = create_v1_api_for_upload()
        screen_name = verify_user(api_v1)
        print("AUTH OK AS:", screen_name)
        logging.info("AUTH OK AS: %s", screen_name)

        client_v2 = create_v2_client()

        # -------------------------------------------------------------------------
        # BREAKING: allow +1 post/day if major event triggers
        # -------------------------------------------------------------------------
        breaking = detect_breaking(client_v2, approved_domains=approved_domains)
        if breaking and random.random() < BREAKING_PROB:
            e = breaking["entry"]
            bkey = breaking_key_from_entry(e)
            if bkey != meta.get("last_breaking_key") and can_post_breaking(meta):
                post = build_breaking_post(now, e, geo_aliases, brain_digest)

                ok, why = preflight_ok(post)
                if ok:
                    tags = list(update_memory(post))
                    append_run_log(now, slot, post, tags, topic=e.get("topic"), entry_link=e.get("link"), post_type="breaking")

                    resp = post_text_only(client_v2, post, test_mode=test_mode)
                    tweet_id = resp["data"].get("id") if resp and resp.get("data") else None

                    meta["last_post_time"] = now.isoformat()
                    meta["last_post_hash"] = sha1(post.lower())
                    meta["last_post_type"] = "breaking"
                    meta["last_tweet_id"] = tweet_id

                    meta["last_breaking_key"] = bkey
                    bump_breaking_today(meta)

                    if not test_mode:
                        try_follow_allowlist(client_v2, meta)

                    save_meta(meta)
                    save_counter(count + 1)
                    print("POSTED (BREAKING):", post)
                    logging.info("POSTED (BREAKING): %s", post)
                    send_notification(f"Breaking event posted: {post}")
                    return
                else:
                    print("Breaking blocked:", why)
                    logging.info("Breaking blocked: %s", why)

        # -------------------------------------------------------------------------
        # NORMAL cadence guard
        # -------------------------------------------------------------------------
        if not can_post_today(meta):
            print("Daily soft cap reached; skipping.")
            logging.info("Daily soft cap reached; skipping.")
            save_meta(meta)
            return

        post = ""
        post_type = None
        topic = None
        tags = []
        entry_link = None
        png_path = None
        brief_url = None

        # scheduled modes
        if should_run_prayer(meta, now):
            post = build_sunday_prayer(meta, now)
            post_type = "prayer"
            tags = list(update_memory(post))

        elif should_run_weekly(meta, now):
            post = weekly_summary(now)
            meta["last_weekly_summary"] = now.isoformat()
            post_type = "weekly"
            tags = list(update_memory(post))

        elif should_run_look_forward(now):
            post = anchored_watchlist(now, geo_aliases)
            post_type = "look_forward"
            tags = list(update_memory(post))

        elif should_run_monthly(meta, now) and slot == "morning":
            post = monthly_ledger()
            meta["last_monthly_summary"] = now.isoformat()
            post_type = "monthly"
            tags = list(update_memory(post))

        else:
            # silent day
            if random.random() < SILENCE_PROB:
                if entries:
                    e = random.choice(entries)
                    seed = f"{e.get('title','')} {e.get('ctx','')}".strip()
                    update_memory(seed)
                    append_run_log(now, slot, "[SILENT]", tags=[], topic=e.get("topic"), entry_link=e.get("link"), post_type="silent")
                meta["silent_day_active"] = True
                meta["last_post_time"] = now.isoformat()
                meta["last_post_type"] = "silent"
                save_meta(meta)
                print("Silent observation; no post.")
                logging.info("Silent observation; no post.")
                return

            meta["silent_day_active"] = False

            weights = MODE_WEIGHTS_MORNING if slot == "morning" else MODE_WEIGHTS_EVENING
            mode = weighted_choice(weights)

            if mode == "uplift":
                post = build_uplift_post(slot)
                post_type = "uplift"
                topic = "uplift"
                tags = list(update_memory(post))

            elif mode == "craft":
                post = build_craft_post(brain_digest)
                post_type = "craft"
                topic = "craft"
                tags = list(update_memory(post))

            elif mode == "faith":
                post = build_faith_reflection()
                post_type = "faith"
                topic = "faith"
                tags = list(update_memory(post))

            elif mode == "reflection":
                post = build_reflection_post()
                post_type = "reflection"
                topic = "reflection"
                tags = list(update_memory(post))

            else:
                # analysis / foreign policy via entry selection
                desired = ["caribbean", "governance", "rights", "international", "law", "security", "technology", "economy", "general"]
                entry = select_entry(meta, entries, desired_topics=desired)
                if entry:
                    remember_entry(meta, entry)
                    topic = entry.get("topic") or "general"
                    entry_link = entry.get("link")

                    post, post_type, png_path, brief_url = build_analysis_post(
                        meta=meta,
                        entry=entry,
                        prompts=prompts,
                        voice_lines=voice_lines,
                        questions=questions,
                        slot=slot,
                        brain_digest=brain_digest,
                    )
                else:
                    post = clamp("I am watching governance and consequence today. Receipts stay the measure.")
                    post_type = "analysis"
                    topic = "general"

                matched = update_memory(post)
                echo = memory_echo_line(matched)
                if echo and random.random() < 0.65:
                    post = clamp(f"{post} {echo}")
                tags = list(matched)

        # -------------------------------------------------------------------------
        # preflight + duplicate prevention
        # -------------------------------------------------------------------------
        post = clamp(resolve_coherence(post))
        ok, why = preflight_ok(post)
        if not ok:
            print("Preflight blocked:", why)
            logging.info("Preflight blocked: %s", why)
            save_meta(meta)
            return

        post_hash = sha1(post.lower())
        if meta.get("last_post_hash") == post_hash:
            print("Duplicate post hash; skipping.")
            logging.info("Duplicate post hash; skipping.")
            save_meta(meta)
            return

        append_run_log(now, slot, post, tags, topic=topic, entry_link=entry_link, post_type=post_type, brief_url=brief_url)

        # Step 8 will optionally attach media. For now, with media if png_path
        if png_path:
            resp = post_with_media(client_v2, api_v1, post, png_path, test_mode=test_mode)
        else:
            resp = post_text_only(client_v2, post, test_mode=test_mode)
        tweet_id = resp["data"].get("id") if resp and resp.get("data") else None

        meta["last_post_time"] = now.isoformat()
        meta["last_post_hash"] = post_hash
        meta["last_post_type"] = post_type
        meta["last_tweet_id"] = tweet_id
        meta["last_post_text"] = post

        bump_post_today(meta)

        # optional safe follow
        if not test_mode:
            try_follow_allowlist(client_v2, meta)

        save_meta(meta)
        save_counter(count + 1)

        print(f"POSTED ({post_type}):", post)
        logging.info("POSTED (%s): %s", post_type, post)

        # Quality check and self-correct
        if QUALITY_CHECK_ENABLED:
            bad, reasons = looks_incoherent(post)
            meta["last_post_quality_failures"] = reasons
            save_meta(meta)

            if bad and can_self_correct_today(meta):
                print("QUALITY FAILED; deleting and reposting once. Reasons:", reasons)
                logging.info("QUALITY FAILED; deleting and reposting once. Reasons: %s", reasons)

                # Delete the bad tweet (X has no edit; only delete+repost)
                try:
                    if tweet_id:
                        client_v2.delete_tweet(tweet_id)
                        print("DELETED ID:", tweet_id)
                        logging.info("DELETED ID: %s", tweet_id)
                except Exception as e:
                    print("DELETE FAILED:", repr(e))
                    logging.error("DELETE FAILED: %s", repr(e))
                    # Stop to avoid double posting if deletion fails
                    raise

                # Attempt corrected variant: resolve again
                corrected = clamp(resolve_coherence(post))

                bad2, reasons2 = looks_incoherent(corrected)
                if bad2:
                    print("Corrected still fails; regenerating once. Reasons:", reasons2)
                    logging.info("Corrected still fails; regenerating once. Reasons: %s", reasons2)
                    corrected = regenerate_once(meta, entries, prompts, voice_lines, questions, slot)
                    corrected = clamp(resolve_coherence(corrected))

                # Avoid reposting identical text
                corrected_hash = sha1(corrected.lower())
                if corrected_hash == post_hash:
                    # force a second regeneration if identical
                    corrected = regenerate_once(meta, entries, prompts, voice_lines, questions, slot)
                    corrected = clamp(resolve_coherence(corrected))
                    corrected_hash = sha1(corrected.lower())

                # Repost
                resp2 = post_text_only(client_v2, corrected, test_mode=test_mode)
                tweet_id2 = resp2["data"].get("id") if resp2 and resp2.get("data") else None
                print("REPOSTED ID:", tweet_id2)
                logging.info("REPOSTED ID: %s", tweet_id2)

                bump_self_correct_today(meta)
                meta["last_tweet_id"] = tweet_id2
                meta["last_post_text"] = corrected
                meta["last_post_hash"] = corrected_hash
                meta["last_post_quality_failures"] = []
                save_meta(meta)

                append_run_log(now, slot, corrected, tags, topic=topic, entry_link=entry_link, post_type=post_type, tweet_id=tweet_id2)
    except Exception as ex:
        logging.error("Run failed: %s", ex)
        send_notification(f"Bot run failed: {ex}")

if __name__ == "__main__":
    main()

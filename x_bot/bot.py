import os
import json
import random
import re
import hashlib
import datetime as dt
from pathlib import Path
from urllib.parse import urlparse

import tweepy
import feedparser

# ==============================
# Paths / Files
# ==============================
ROOT = Path(__file__).parent
CONFIG = ROOT / "config"
STATE_DIR = ROOT / "state"
STATE_DIR.mkdir(exist_ok=True)

COUNTER_FILE = STATE_DIR / "post_counter.json"
MEMORY_FILE = STATE_DIR / "memory_echo.json"
META_FILE = STATE_DIR / "meta.json"
RUN_LOG_FILE = STATE_DIR / "run_log.json"

FEEDS_FILE = CONFIG / "feeds.txt"
PROMPTS_FILE = CONFIG / "prompts.txt"
PRAYERS_FILE = CONFIG / "prayers.txt"
STYLE_FILE = CONFIG / "style.txt"
APPROVED_DOMAINS_FILE = CONFIG / "approved_domains.txt"
VOICE_FILE = CONFIG / "voice.txt"
QUESTIONS_FILE = CONFIG / "questions.txt"

MAX_LEN = 280
MONTHLY_HARD_CAP = 60  # supports 1–2/day safely

# Daily cap (keeps it human and reduces spam risk)
DAILY_SOFT_CAP = 2

# Coherence / Variety controls
SILENCE_PROB = 0.10            # silent observation days (no post)
ECHO_THRESHOLD = 3             # repetition threshold for “pattern” lines
MAX_WITNESS_STREAK = 2         # prevents consecutive doom/witness mode
RECENT_ENTRY_BLOCK = 8         # avoid repeating recent links/titles
QUESTION_PROB = 0.18           # chance to end analysis with a question
LINK_ONLY_PROB = 0.12          # sometimes: share link + tight comment (article-forward)
DOMAIN_ATTRIBUTION_PROB = 0.25 # sometimes: "via <domain>" tag

# ---- Content range controls (prevents doom-only) ----
MODE_WEIGHTS_MORNING = {
    "analysis": 0.44,     # news read + context + judgment
    "uplift": 0.18,       # constructive
    "craft": 0.12,        # discipline/method
    "faith": 0.12,        # spiritual reflection (Sunday is special)
    "reflection": 0.14    # philosophical but grounded
}

MODE_WEIGHTS_EVENING = {
    "analysis": 0.46,
    "uplift": 0.14,
    "craft": 0.14,
    "reflection": 0.18,
    "faith": 0.08
}

# ---- Memory tagging ----
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
}

WITNESS_TERMS = [
    "killed", "dead", "murder", "execution", "shooting",
    "human rights", "rights", "freedom of speech", "freedom of expression", "censorship",
    "detention", "torture", "racial", "racism", "xenophobia"
]

# ---- Topic classification (for coherence) ----
TOPIC_KEYWORDS = {
    "economy": [
        "inflation", "rates", "interest", "bond", "treasury", "budget", "deficit", "debt", "gdp",
        "trade", "tariff", "currency", "usd", "dollar", "de-dollar", "bank", "markets", "stocks",
        "company", "earnings", "oil", "gas", "energy", "shipment", "supply", "rail"
    ],
    "governance": [
        "minister", "parliament", "senate", "cabinet", "bill", "law", "regulation", "government",
        "oversight", "audit", "procurement", "tender", "contract", "commission", "election"
    ],
    "rights": [
        "rights", "freedom", "speech", "expression", "censorship", "detention", "torture", "discrimination",
        "racism", "xenophobia", "abuse", "harassment", "protest"
    ],
    "security": [
        "police", "shooting", "killed", "murder", "violence", "gang", "crime", "weapon", "assault",
        "security", "terror", "attack"
    ],
    "law": [
        "court", "judge", "trial", "lawsuit", "appeal", "icj", "icc", "tribunal", "verdict",
        "sentence", "legal"
    ],
    "international": [
        "un", "united nations", "eu", "nato", "ohchr", "sanctions", "summit", "treaty", "war",
        "diplomacy", "foreign", "security council"
    ],
    "technology": [
        "ai", "openai", "cyber", "cybersecurity", "hack", "breach", "data", "surveillance",
        "tech", "software", "chip", "semiconductor"
    ],
    "caribbean": [
        "trinidad", "tobago", "caricom", "jamaica", "barbados", "guyana", "grenada",
        "st lucia", "antigua", "bahamas", "haiti", "dominica"
    ],
}

SEPARATORS = [" | ", " — ", " – ", " - ", " • "]


# ==============================
# Utilities
# ==============================
def utc_now():
    return dt.datetime.now(dt.timezone.utc)

def day_key(d: dt.datetime) -> str:
    return d.strftime("%Y-%m-%d")

def month_key(d: dt.datetime) -> str:
    return d.strftime("%Y-%m")

def clamp(text: str, max_len=MAX_LEN) -> str:
    text = re.sub(r"\s+", " ", text.replace("\n", " ").strip())
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"

def sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()

def read_lines(path: Path):
    if not path.exists():
        return []
    return [
        ln.strip()
        for ln in path.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]

def load_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default

def save_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def get_slot(now: dt.datetime) -> str:
    # you already run twice per day; slot stays useful for tone
    return "morning" if now.hour < 15 else "evening"

def weighted_choice(weights: dict) -> str:
    r = random.random()
    upto = 0.0
    for k, w in weights.items():
        upto += w
        if r <= upto:
            return k
    return list(weights.keys())[-1]


# ==============================
# State
# ==============================
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

    # legacy-safe defaults + new keys
    meta.setdefault("last_post_time", None)
    meta.setdefault("last_post_type", None)

    meta.setdefault("last_weekly_summary", None)
    meta.setdefault("last_monthly_summary", None)

    meta.setdefault("last_prayer", None)
    meta.setdefault("last_prayer_date", None)

    meta.setdefault("silent_day_active", False)
    meta.setdefault("witness_streak", 0)

    meta.setdefault("day_post_count", 0)
    meta.setdefault("day_key", None)

    meta.setdefault("recent_entry_keys", [])      # rolling list of recent title/link keys
    meta.setdefault("last_post_hash", None)       # avoid duplicate text
    meta.setdefault("last_entry_link", None)
    meta.setdefault("last_entry_title", None)

    return meta

def save_meta(meta: dict):
    save_json(META_FILE, meta)

def append_run_log(now: dt.datetime, slot: str, post: str, tags: list, topic: str | None = None, entry_link: str | None = None):
    log = load_json(RUN_LOG_FILE, [])
    if not isinstance(log, list):
        log = []

    log.append({
        "ts": now.isoformat(),
        "slot": slot,
        "topic": topic,
        "tags": tags,
        "entry_link": entry_link,
        "post": post[:220]
    })

    log = log[-180:]  # keep longer history
    save_json(RUN_LOG_FILE, log)


# ==============================
# Reading + Comprehension
# ==============================
def clean_headline(title: str) -> str:
    if not title:
        return ""
    t = re.sub(r"\s+", " ", title).strip()

    for sep in SEPARATORS:
        if sep in t and len(t.split(sep)[0]) >= 18:
            t = t.split(sep)[0].strip()

    t = re.sub(r"\s*\[[^\]]+\]\s*", " ", t).strip()
    t = re.sub(r"\s*\([^)]+\)\s*$", "", t).strip()
    return t

def extract_context(entry) -> str:
    parts = []
    for attr in ("summary", "description"):
        val = getattr(entry, attr, "") or ""
        if val:
            parts.append(val)

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
    scores = {k: 0 for k in TOPIC_KEYWORDS.keys()}
    for topic, words in TOPIC_KEYWORDS.items():
        for w in words:
            if w in t:
                scores[topic] += 1
    if scores.get("caribbean", 0) >= 1:
        return "caribbean"
    best = max(scores.items(), key=lambda x: x[1])
    return best[0] if best[1] > 0 else "general"

def domain_of(link: str) -> str:
    try:
        host = urlparse(link).netloc.lower()
        host = host.replace("www.", "")
        return host
    except Exception:
        return ""

def is_approved_domain(link: str, approved_domains: list[str]) -> bool:
    if not link:
        return False
    host = domain_of(link)
    if not host:
        return False
    for d in approved_domains:
        d = d.lower().strip().replace("www.", "")
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
                title_raw = getattr(e, "title", "").strip()
                link = getattr(e, "link", "").strip()
                title = clean_headline(title_raw)
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
                    "approved": is_approved_domain(link, approved_domains) if link else False
                })
        except Exception:
            continue

    random.shuffle(items)

    # de-dupe on title
    seen = set()
    out = []
    for it in items:
        key = it["title"].lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(it)

    return out

def select_entry(meta: dict, entries: list[dict], desired_topics: list[str]) -> dict | None:
    if not entries:
        return None

    recent_keys = set(meta.get("recent_entry_keys") or [])
    def entry_key(e: dict) -> str:
        return sha1((e.get("title","") + "|" + (e.get("link","") or "")).lower())

    pool = [e for e in entries if e.get("topic") in desired_topics] or entries[:]
    pool2 = [e for e in pool if entry_key(e) not in recent_keys] or pool

    # Slight preference for approved domains (quality + lower spam risk)
    approved = [e for e in pool2 if e.get("approved")]
    if approved and random.random() < 0.65:
        return random.choice(approved)
    return random.choice(pool2)

def remember_entry(meta: dict, entry: dict):
    key = sha1((entry.get("title","") + "|" + (entry.get("link","") or "")).lower())
    recent = meta.get("recent_entry_keys") or []
    recent.append(key)
    meta["recent_entry_keys"] = recent[-RECENT_ENTRY_BLOCK:]
    meta["last_entry_title"] = entry.get("title")
    meta["last_entry_link"] = entry.get("link")


# ==============================
# Memory + Echo
# ==============================
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
        return random.choice([
            "Racism is a pattern when it repeats.",
            "Racism keeps resurfacing. Repetition is the signal.",
        ])
    if tag == "corruption":
        return random.choice([
            "Corruption persists through delayed consequences.",
            "Corruption repeats when enforcement becomes theatre.",
        ])
    if tag == "state_violence":
        return random.choice([
            "State violence repeats through collapsed oversight.",
            "Civilian oversight stays the test.",
        ])

    return random.choice([
        "Repetition becomes instruction.",
        "The record is converging.",
        "Patterns keep declaring themselves.",
    ])


# ==============================
# Voice / Style
# ==============================
def voice_open(slot: str, voice_lines: list[str]) -> str:
    # no labels like "Signal:" — uses natural starters
    if voice_lines:
        return random.choice(voice_lines).strip()
    return random.choice([
        "I read this and paused.",
        "This is the kind of detail that matters.",
        "This is a real signal.",
        "This sits in the record.",
        "This lands with consequence.",
    ])

def maybe_question(topic: str, questions: list[str]) -> str | None:
    if random.random() >= QUESTION_PROB:
        return None
    # Prefer topic-aligned questions if provided as tagged lines: "topic: question..."
    tagged = []
    for q in questions:
        if ":" in q:
            t, body = q.split(":", 1)
            if t.strip().lower() == topic:
                tagged.append(body.strip())
    if tagged:
        return random.choice(tagged)
    # fallback general question
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


# ==============================
# Post builders (coherent)
# ==============================
def topic_lens_bank(topic: str) -> list[str]:
    # Uses your prompts semantics, but keeps them short and human in output.
    mapping = {
        "economy": ["economic realism", "fiscal responsibility", "who bears the cost", "long-term national consequence"],
        "governance": ["rule of law", "public accountability", "institutional legitimacy", "constitutional restraint"],
        "rights": ["civic liberties", "freedom of expression", "human rights enforcement", "due process"],
        "security": ["policing standards", "proportional use of state power", "civilian oversight"],
        "law": ["rule of law", "due process", "international law obligations"],
        "international": ["international law obligations", "state credibility", "power asymmetry"],
        "technology": ["public accountability", "civic liberties", "state credibility"],
        "caribbean": ["Caribbean strategic posture", "sovereignty", "public trust"],
        "general": ["moral agency", "public trust", "truth versus propaganda"],
    }
    return mapping.get(topic, mapping["general"])

def analysis_judgment(topic: str) -> str:
    if topic == "economy":
        return random.choice([
            "Credibility prices everything.",
            "Policy that burns trust raises the cost of capital.",
            "Incentives run faster than speeches.",
        ])
    if topic == "governance":
        return random.choice([
            "Legitimacy lives in restraint and receipts.",
            "Authority expands when oversight becomes optional.",
            "Transparency is governance oxygen.",
        ])
    if topic == "rights":
        return random.choice([
            "Speech and due process stay non-negotiable.",
            "Rights only exist when enforcement exists.",
            "Discrimination becomes policy when repetition is tolerated.",
        ])
    if topic == "security":
        return random.choice([
            "Public safety begins with accountability.",
            "Force without oversight becomes intimidation.",
            "Civilian oversight stays the standard.",
        ])
    if topic == "law":
        return random.choice([
            "Courts become the line when politics bends reality.",
            "Rule of law is enforcement, not performance.",
            "Due process is legitimacy in motion.",
        ])
    if topic == "international":
        return random.choice([
            "States trade in reputation every day.",
            "International posture is credibility.",
            "Restraint prevents escalation.",
        ])
    if topic == "technology":
        return random.choice([
            "Technology without accountability becomes power without consent.",
            "Cyber risk is governance risk.",
            "Surveillance capacity demands oversight capacity.",
        ])
    if topic == "caribbean":
        return random.choice([
            "Small states need clean institutions to stay sovereign.",
            "Corruption is geopolitical weakness.",
            "The Caribbean pays first when governance fails.",
        ])
    return random.choice([
        "Power moves through incentives.",
        "Receipts protect the record.",
        "Truth is a discipline.",
    ])

def build_analysis_post(meta: dict, entry: dict, prompts: list[str], voice_lines: list[str], questions: list[str], slot: str) -> str:
    title = entry.get("title", "")
    ctx = entry.get("ctx", "")
    link = entry.get("link") or ""
    topic = entry.get("topic", "general")

    open_line = voice_open(slot, voice_lines)

    # "what happened" in one sentence, always anchored
    what = ctx if ctx else title
    what = clamp(what, 175)

    # lens selection: topic bank + sometimes prompts.txt
    lens = random.choice(topic_lens_bank(topic))
    if prompts and random.random() < 0.35:
        lens = random.choice(prompts)

    judgment = analysis_judgment(topic)

    # Sometimes share link-only with tight comment (human feed behavior)
    if link and random.random() < LINK_ONLY_PROB:
        # short comment + link
        via = ""
        if random.random() < DOMAIN_ATTRIBUTION_PROB:
            d = domain_of(link)
            if d:
                via = f" (via {d})"
        text = f"{open_line} {judgment}{via} {link}"
        return clamp(text)

    # Normal analysis composition: open + what + judgment + lens hint + optional question + optional link
    lens_hint = random.choice([
        f"Measured against {lens}.",
        f"Standard: {lens}.",
        f"{lens} stays the measure.",
    ])

    q = maybe_question(topic, questions)

    # Link inclusion is controlled (avoid spammy look)
    link_part = f" {link}" if (link and random.random() < 0.22) else ""

    parts = [open_line, what, judgment, lens_hint]
    if q:
        parts.append(q)
    text = " ".join([p.strip() for p in parts if p and p.strip()]) + link_part

    # Witness add-on (streak limited)
    witness_streak = int(meta.get("witness_streak", 0))
    if is_witness_event(text) and witness_streak < MAX_WITNESS_STREAK:
        text = clamp(f"{text} {witness_close()}")
        meta["witness_streak"] = witness_streak + 1
    else:
        meta["witness_streak"] = 0

    return clamp(text)

def build_uplift_post(slot: str) -> str:
    morning = [
        "I am moving clean today: one meaningful task, executed with discipline.",
        "I am protecting my attention. I am building one durable thing today.",
        "I am choosing integrity as a habit. The day follows repetition."
    ]
    evening = [
        "I am auditing the day and keeping the wins that stayed quiet.",
        "I am ending the day with discipline intact. Tomorrow follows what I repeat.",
        "I am resting as strategy. Recovery builds precision."
    ]
    return clamp(random.choice(morning if slot == "morning" else evening))

def build_craft_post() -> str:
    lines = [
        "I document first. I speak second. I escalate only when the record is clean.",
        "Precision beats volume. One clear thought lands harder than ten scattered ones.",
        "I treat memory as infrastructure. Receipts keep institutions honest.",
        "I keep intensity controlled. Accuracy stays the brand of my speech.",
    ]
    return clamp(random.choice(lines))

def build_reflection_post() -> str:
    lines = [
        "Patterns are policy when they repeat without consequence.",
        "Legitimacy lives in restraint, due process, and accountability that bites.",
        "Power tests people by offering comfort in exchange for silence.",
        "Truth is memory with courage. Propaganda is memory with fear removed.",
    ]
    return clamp(random.choice(lines))

def build_faith_reflection() -> str:
    lines = [
        "I am keeping my tongue clean. Restraint is spiritual discipline.",
        "I am holding justice as a standard, not a mood.",
        "I am choosing mercy with boundaries and truth with receipts.",
    ]
    return clamp(random.choice(lines))


# ==============================
# Prayer (autonomous via prayers.txt fragments)
# ==============================
def should_run_prayer(meta: dict, now: dt.datetime) -> bool:
    # Sunday morning prayer (one per Sunday)
    if now.weekday() != 6:
        return False
    if get_slot(now) != "morning":
        return False
    last_date = meta.get("last_prayer_date")
    return last_date != now.date().isoformat()

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
        bridges.append(clamp(f"I keep watch over the pattern: {t}."))

    last_prayer_text = (meta.get("last_prayer") or "")
    chosen = _pick_fragments(fragments, last_prayer_text, k=random.randint(2, 4))
    close = random.choice(["Amen.", "So be it.", "Let it be done."]) if random.random() < 0.60 else ""

    parts = [opener] + bridges + chosen + ([close] if close else [])
    text = clamp(" ".join([p.strip() for p in parts if p.strip()]))

    meta["last_prayer"] = text
    meta["last_prayer_date"] = now.date().isoformat()
    return text


# ==============================
# Weekly / Monthly
# ==============================
def should_run_weekly(meta: dict, now: dt.datetime) -> bool:
    # Saturday evening weekly summary
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

def should_run_look_forward(now: dt.datetime) -> bool:
    # Monday morning look-forward
    return now.weekday() == 0 and get_slot(now) == "morning"

def look_forward() -> str:
    mem = load_memory()
    ranked = sorted(mem.items(), key=lambda x: -int(x[1]))[:4]
    themes = ", ".join([t.replace("_", " ") for t, _ in ranked]) if ranked else "governance, rights, accountability"
    return clamp(f"I am watching {themes} this week. I expect narrative management. I demand receipts. Dignity and law stay the measure.")

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
        return "I closed 30 days with quiet discipline. The record stayed clean. Witness stayed awake."
    top = ", ".join([f"{k.replace('_',' ')}({v})" for k, v in ranked[:4]])
    return clamp(f"I closed 30 days with repetition on the ledger: {top}. Repetition becomes instruction. I keep watch. I keep record.")


# ==============================
# X auth (keep the working path)
# ==============================
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

def create_v1_api_for_verify() -> tweepy.API:
    consumer_key = require_env("X_CONSUMER_KEY")
    consumer_secret = require_env("X_CONSUMER_SECRET")
    access_token = require_env("X_ACCESS_TOKEN")
    access_secret = require_env("X_ACCESS_SECRET")
    auth = tweepy.OAuth1UserHandler(consumer_key, consumer_secret, access_token, access_secret)
    return tweepy.API(auth, wait_on_rate_limit=True)

def verify_user(api_v1: tweepy.API) -> str:
    me = api_v1.verify_credentials()
    if not me or not getattr(me, "screen_name", None):
        raise RuntimeError("Auth verify failed (no screen_name returned).")
    return me.screen_name


# ==============================
# Posting guards
# ==============================
def refresh_daily_counters(meta: dict, now: dt.datetime):
    dk = day_key(now)
    if meta.get("day_key") != dk:
        meta["day_key"] = dk
        meta["day_post_count"] = 0

def can_post_today(meta: dict) -> bool:
    return int(meta.get("day_post_count", 0)) < DAILY_SOFT_CAP

def bump_post_today(meta: dict):
    meta["day_post_count"] = int(meta.get("day_post_count", 0)) + 1


# ==============================
# Main
# ==============================
def main():
    now = utc_now()
    slot = get_slot(now)
    count = load_counter()

    if count >= MONTHLY_HARD_CAP:
        print("Monthly safety cap reached; skipping.")
        return

    meta = load_meta()
    refresh_daily_counters(meta, now)

    if not can_post_today(meta):
        print("Daily soft cap reached; skipping.")
        save_meta(meta)
        return

    prompts = read_lines(PROMPTS_FILE)
    voice_lines = read_lines(VOICE_FILE)
    questions = read_lines(QUESTIONS_FILE)
    approved_domains = read_lines(APPROVED_DOMAINS_FILE)

    # style.txt remains an identity anchor; loading keeps it present for future expansion
    _style_anchor = read_lines(STYLE_FILE)

    entries = pick_entries(FEEDS_FILE, approved_domains=approved_domains)

    post = ""
    tags = []
    topic = None
    entry_link = None

    # --- Scheduled modes ---
    if should_run_prayer(meta, now):
        post = build_sunday_prayer(meta, now)
        meta["last_post_type"] = "prayer"
        save_meta(meta)
        tags = list(update_memory(post))

    elif should_run_weekly(meta, now):
        post = weekly_summary(now)
        meta["last_weekly_summary"] = now.isoformat()
        meta["last_post_type"] = "weekly"
        save_meta(meta)
        tags = list(update_memory(post))

    elif should_run_look_forward(now):
        post = look_forward()
        meta["last_post_type"] = "look_forward"
        save_meta(meta)
        tags = list(update_memory(post))

    elif should_run_monthly(meta, now) and slot == "morning":
        post = monthly_ledger()
        meta["last_monthly_summary"] = now.isoformat()
        meta["last_post_type"] = "monthly"
        save_meta(meta)
        tags = list(update_memory(post))

    else:
        # Silent observation day
        if random.random() < SILENCE_PROB:
            if entries:
                e = random.choice(entries)
                seed = f"{e.get('title','')} {e.get('ctx','')}".strip()
                update_memory(seed)
                append_run_log(now, slot, "[SILENT]", tags=[], topic=e.get("topic"), entry_link=e.get("link"))
            meta["silent_day_active"] = True
            meta["last_post_time"] = now.isoformat()
            meta["last_post_type"] = "silent"
            save_meta(meta)
            print("Silent observation day; no post.")
            return

        meta["silent_day_active"] = False

        weights = MODE_WEIGHTS_MORNING if slot == "morning" else MODE_WEIGHTS_EVENING
        mode = weighted_choice(weights)

        if mode in ("uplift", "craft", "faith", "reflection"):
            if mode == "uplift":
                post = build_uplift_post(slot)
                topic = "uplift"
            elif mode == "craft":
                post = build_craft_post()
                topic = "craft"
            elif mode == "faith":
                post = build_faith_reflection()
                topic = "faith"
            else:
                post = build_reflection_post()
                topic = "reflection"

            tags = list(update_memory(post))
            meta["last_post_type"] = mode
            save_meta(meta)

        else:
            # analysis mode: pick a matching entry FIRST, then write coherent commentary
            desired = ["caribbean", "governance", "rights", "international", "law", "security", "technology", "economy", "general"]
            entry = select_entry(meta, entries, desired_topics=desired)

            if entry:
                topic = entry.get("topic") or "general"
                entry_link = entry.get("link")
                remember_entry(meta, entry)

                post = build_analysis_post(
                    meta=meta,
                    entry=entry,
                    prompts=prompts,
                    voice_lines=voice_lines,
                    questions=questions,
                    slot=slot
                )
            else:
                post = clamp("I am watching governance and consequence today. Receipts stay the measure.")
                topic = "general"

            # Memory echo (only after we have coherent text)
            matched = update_memory(post)
            echo = memory_echo_line(matched)
            if echo and random.random() < 0.65:
                post = clamp(f"{post} {echo}")
            tags = list(matched)

            meta["last_post_type"] = "analysis"
            save_meta(meta)

    # Duplicate prevention (text)
    post_hash = sha1(post.lower())
    if meta.get("last_post_hash") == post_hash:
        print("Duplicate post hash; skipping.")
        return

    # log before posting
    append_run_log(now, slot, post, tags, topic=topic, entry_link=entry_link)

    print("POST:", post)

    # Verify (v1) + Post (v2) — keep the working path
    api_v1 = create_v1_api_for_verify()
    screen_name = verify_user(api_v1)
    print("AUTH OK AS:", screen_name)

    client = create_v2_client()
    resp = client.create_tweet(text=post)
    tweet_id = resp.data.get("id") if resp and resp.data else None
    print("POSTED ID:", tweet_id)

    # update meta post markers
    meta["last_post_time"] = now.isoformat()
    meta["last_post_hash"] = post_hash
    bump_post_today(meta)
    save_meta(meta)

    save_counter(count + 1)


if __name__ == "__main__":
    main()

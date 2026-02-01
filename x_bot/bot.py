import os
import json
import random
import re
import hashlib
import datetime as dt
from pathlib import Path

import tweepy
import feedparser

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

MAX_LEN = 280
MONTHLY_HARD_CAP = 60  # supports 1–2/day safely

# ---- Content range controls (prevents doom-only) ----
MODE_WEIGHTS_MORNING = {
    "signal": 0.38,
    "uplift": 0.22,
    "market": 0.15,
    "craft": 0.12,
    "faith": 0.13
}

MODE_WEIGHTS_EVENING = {
    "signal": 0.42,
    "uplift": 0.18,
    "market": 0.15,
    "craft": 0.15,
    "reflection": 0.10
}

SILENCE_PROB = 0.08
ECHO_THRESHOLD = 3
MAX_WITNESS_STREAK = 2

# ---- Memory tagging ----
MEMORY_KEYWORDS = {
    "police": "state_violence",
    "shooting": "state_violence",
    "shot": "state_violence",
    "killed": "state_violence",
    "dead": "state_violence",
    "murder": "state_violence",

    "freedom of speech": "civic_liberties",
    "censorship": "civic_liberties",
    "surveillance": "civic_liberties",
    "detention": "civic_liberties",

    "racism": "racism",
    "racial": "racism",
    "xenophobia": "racism",

    "corruption": "corruption",
    "bribe": "corruption",
    "kickback": "corruption",

    "procurement": "procurement_scandal",
    "tender": "procurement_scandal",
    "contract": "procurement_scandal",
    "audit": "procurement_scandal",

    "court": "judicial_intervention",
    "icj": "judicial_intervention",
    "icc": "judicial_intervention",
    "tribunal": "judicial_intervention",

    "un": "international_signal",
    "united nations": "international_signal",
    "ohchr": "international_signal",
    "nato": "international_signal",
    "eu": "international_signal",
}

WITNESS_TERMS = [
    "killed", "dead", "murder", "execution", "shooting",
    "human rights", "rights", "freedom of speech", "censorship",
    "detention", "torture", "racial", "racism"
]

# ---- Topic classification (for coherence) ----
TOPIC_KEYWORDS = {
    "economy": [
        "inflation", "rates", "interest", "bond", "treasury", "budget", "deficit", "debt", "gdp",
        "trade", "tariff", "currency", "usd", "dollar", "de-dollar", "bank", "markets", "stocks",
        "company", "earnings", "oil", "gas", "energy", "shipment", "supply", "rail", "industry"
    ],
    "governance": [
        "minister", "parliament", "senate", "cabinet", "bill", "law", "regulation", "government",
        "oversight", "audit", "procurement", "tender", "contract", "commission", "executive"
    ],
    "rights": [
        "rights", "freedom", "speech", "censorship", "detention", "torture", "discrimination",
        "racism", "xenophobia", "abuse", "harassment", "protest"
    ],
    "security": [
        "police", "shooting", "killed", "murder", "violence", "gang", "crime", "weapon", "assault",
        "security", "terror", "attack"
    ],
    "law": [
        "court", "judge", "trial", "lawsuit", "appeal", "icj", "icc", "tribunal", "verdict",
        "sentence", "legal", "ruling"
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
        "st lucia", "antigua", "bahamas"
    ],
}

# ---- Utility ----
def utc_now():
    return dt.datetime.now(dt.timezone.utc)

def clamp(text: str, max_len=MAX_LEN) -> str:
    text = re.sub(r"\s+", " ", (text or "").replace("\n", " ").strip())
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"

def month_key(d: dt.datetime) -> str:
    return d.strftime("%Y-%m")

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

def sha1(s: str) -> str:
    return hashlib.sha1((s or "").encode("utf-8")).hexdigest()

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

    meta.setdefault("last_post_time", None)
    meta.setdefault("last_post_type", None)
    meta.setdefault("last_post_hash", None)

    meta.setdefault("last_weekly_summary", None)
    meta.setdefault("last_monthly_summary", None)

    meta.setdefault("last_prayer", None)
    meta.setdefault("last_prayer_date", None)

    meta.setdefault("silent_day_active", False)
    meta.setdefault("witness_streak", 0)

    # coherence / repetition controls
    meta.setdefault("last_entry_key", None)     # title+link hash
    meta.setdefault("last_entry_topic", None)

    return meta

def save_meta(meta: dict):
    save_json(META_FILE, meta)

def append_run_log(now: dt.datetime, slot: str, post: str, tags: list, topic: str | None = None):
    log = load_json(RUN_LOG_FILE, [])
    if not isinstance(log, list):
        log = []

    log.append({
        "ts": now.isoformat(),
        "slot": slot,
        "topic": topic,
        "tags": tags,
        "post": (post or "")[:220]
    })

    log = log[-120:]
    save_json(RUN_LOG_FILE, log)

def get_slot(now: dt.datetime) -> str:
    return "morning" if now.hour < 15 else "evening"

def weighted_choice(weights: dict) -> str:
    r = random.random()
    upto = 0.0
    for k, w in weights.items():
        upto += w
        if r <= upto:
            return k
    return list(weights.keys())[-1]

def is_witness_event(text: str) -> bool:
    t = (text or "").lower()
    return any(term in t for term in WITNESS_TERMS)

# ---- Headline cleaning + context extraction (crucial) ----
SEPARATORS = [" | ", " — ", " – ", " - ", " • "]

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

    chunks = re.split(r"(?<=[.!?])\s+", raw)
    if chunks and len(chunks[0]) >= 40:
        return clamp(chunks[0], max_len=180)
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

def topic_tags(topic: str) -> list[str]:
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

def friendly_tag(tag: str) -> str:
    # For summaries: “procurement_scandal” → “procurement”
    if not tag:
        return tag
    return tag.replace("_", " ")

# ---- Memory ----
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
            "This is racism. The pattern is repeating.",
            "Racism keeps surfacing. Repetition is the signal.",
        ])
    if tag == "corruption":
        return random.choice([
            "Corruption persists because consequences stay delayed.",
            "Corruption repeats when enforcement becomes theatre.",
        ])
    if tag == "state_violence":
        return random.choice([
            "State violence repeats when oversight collapses.",
            "This is a pattern. Civilian oversight is the test.",
        ])

    return random.choice([
        "Repetition is instruction.",
        "The pattern is the signal.",
        "The record is converging.",
    ])

# ---- Feed reading (returns structured entries) ----
def pick_entries(feeds_file: Path, limit_feeds=10, per_feed=6):
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

                # published time if available (helps pick fresher items without web calls)
                published = getattr(e, "published", "") or ""
                published_ts = None
                try:
                    if getattr(e, "published_parsed", None):
                        published_ts = dt.datetime.fromtimestamp(
                            dt.datetime(*e.published_parsed[:6], tzinfo=dt.timezone.utc).timestamp(),
                            tz=dt.timezone.utc
                        )
                except Exception:
                    published_ts = None

                blob = f"{title}. {ctx}".strip()
                topic = classify_topic(blob)

                items.append({
                    "title": title,
                    "link": link,
                    "ctx": ctx,
                    "topic": topic,
                    "published": published,
                    "published_ts": published_ts.isoformat() if published_ts else None,
                })
        except Exception:
            continue

    # prefer fresher items when timestamps exist
    def _ts_key(it):
        try:
            return it.get("published_ts") or ""
        except Exception:
            return ""
    items.sort(key=_ts_key, reverse=True)

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

def entry_key(entry: dict) -> str:
    return sha1(f"{entry.get('title','')}|{entry.get('link','')}")

def select_entry(entries: list[dict], desired_topics: list[str], meta: dict | None = None) -> dict | None:
    if not entries:
        return None

    last_key = (meta or {}).get("last_entry_key")
    pool = [e for e in entries if e.get("topic") in desired_topics] or entries[:]

    # avoid repeating the last entry if possible
    if last_key:
        filtered = [e for e in pool if entry_key(e) != last_key]
        if filtered:
            pool = filtered

    return random.choice(pool) if pool else random.choice(entries)

# ---- Comprehension / reasoning layer ----
def extract_core_claim(title: str, ctx: str) -> str:
    """
    Produces a single clean “what happened” statement.
    It stays short, concrete, and uses the context if it adds detail beyond the title.
    """
    t = clean_headline(title or "")
    c = (ctx or "").strip()

    if not c:
        return t

    # If context just repeats the title, keep the title only.
    t_low = t.lower()
    c_low = c.lower()
    if t_low and (t_low in c_low or c_low in t_low):
        return t

    # Keep first sentence of ctx as the claim if it reads like a sentence.
    if len(c) >= 40:
        return clamp(c, 180)
    return t

def judge_signal(topic: str) -> str:
    """
    One coherent judgement per topic. No stitched fragments.
    """
    if topic == "economy":
        return random.choice([
            "Credibility sets the price of money. When trust drops, citizens pay.",
            "Policy risk becomes a tax when governments burn confidence.",
            "Incentives drive behaviour. Slogans do not move capital."
        ])
    if topic == "governance":
        return random.choice([
            "Legitimacy lives in restraint, transparency, and consequence.",
            "Executive authority stays lawful through oversight and receipts.",
            "Institutional decay starts when accountability becomes optional."
        ])
    if topic == "rights":
        return random.choice([
            "Rights restrain power. Speech and due process stay non-negotiable.",
            "Discrimination becomes a system when it repeats. Name it and enforce consequence.",
            "Censorship is governance failure. Free expression is civic oxygen."
        ])
    if topic == "security":
        return random.choice([
            "State force requires proportionality and civilian oversight.",
            "Policing becomes intimidation when accountability collapses.",
            "Public safety starts with consequences for abuse."
        ])
    if topic == "law":
        return random.choice([
            "Courts restrain power when politics tries to bend reality.",
            "Rule of law functions through enforcement, not performance.",
            "Due process is legitimacy. Shortcuts produce backlash and decay."
        ])
    if topic == "international":
        return random.choice([
            "States trade in credibility every day. Reputation is strategic power.",
            "International law is restraint. Breakdown invites escalation.",
            "Diplomacy and sanctions move lives. Policy owns consequences."
        ])
    if topic == "technology":
        return random.choice([
            "Cyber risk is governance risk. Security failures become public harm.",
            "Surveillance expands capacity. Oversight must expand too.",
            "Technology without accountability becomes power without consent."
        ])
    if topic == "caribbean":
        return random.choice([
            "Small states survive through clean institutions. Corruption is geopolitical weakness.",
            "Strategic posture is survival. Sovereignty requires competence and receipts.",
            "The Caribbean pays first when governance fails: higher costs, weaker trust."
        ])
    return random.choice([
        "Power moves through incentives. Follow who benefits and who pays.",
        "Propaganda competes with memory. Receipts protect the record.",
        "Truth is a discipline: observe, document, then speak."
    ])

# ---- Post builders: coherent analysis tied to one entry ----
def build_analysis(entry: dict, lens: str, slot: str) -> str:
    title = entry.get("title", "")
    ctx = entry.get("ctx", "")
    topic = entry.get("topic", "general")

    opener = random.choice(
        ["Morning signal:", "Daybreak note:", "First read:"]
        if slot == "morning"
        else ["Evening note:", "Close of play:", "End-of-day signal:"]
    )

    claim = extract_core_claim(title, ctx)
    judgement = judge_signal(topic)
    lens_line = f"Lens: {lens}."

    link = entry.get("link") or ""
    link_part = f" {link}" if (link and random.random() < 0.18) else ""

    # Single thread: headline → claim → judgement → lens
    text = f"{opener} {title}{link_part} {claim} {judgement} {lens_line}"
    return clamp(text)

def build_uplift_post(slot: str) -> str:
    morning = [
        "Morning calibration: discipline first. Protect peace. Execute one meaningful thing.",
        "Build the day clean: integrity, receipts, steady habits. Sovereignty lives there.",
        "You win by repetition: one clear decision, then follow-through."
    ]
    evening = [
        "Evening note: progress stays quiet. Discipline still counts when nobody claps.",
        "Close of day: audit habits, then sleep clean. Tomorrow follows what you repeat.",
        "Rest is strategy. Recover well, return precise."
    ]
    return clamp(random.choice(morning if slot == "morning" else evening))

def build_craft_post() -> str:
    lines = [
        "Working rule: observe first. Document second. Speak third.",
        "Operating discipline: clean language, sharp receipts, controlled intensity.",
        "Precision beats volume. One clear point lands harder than ten scattered ones.",
        "Integrity is a habit. Build it daily."
    ]
    return clamp(random.choice(lines))

def build_reflection_post() -> str:
    lines = [
        "Reflection: systems reveal themselves through repetition. Patterns are policy.",
        "Reflection: legitimacy lives in restraint, due process, and consequence.",
        "Reflection: truth is memory with courage."
    ]
    return clamp(random.choice(lines))

def build_faith_reflection() -> str:
    lines = [
        "Faith reflection: discipline is spiritual. Clean speech and restraint are worship.",
        "Faith reflection: justice is a standard held when it is inconvenient.",
        "Faith reflection: mercy stays real when it keeps boundaries."
    ]
    return clamp(random.choice(lines))

def build_witness_line() -> str:
    return random.choice([
        "A life is not a statistic. Accountability is the minimum.",
        "Rights restrain power. Treat them as real.",
        "State force demands civilian oversight. Every time.",
        "Dignity stays non-negotiable. The record matters.",
    ])

# ---- Sunday prayer (autonomous via prayers.txt fragments) ----
def should_run_prayer(meta: dict, now: dt.datetime) -> bool:
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
        text = "Sunday prayer: God, cover the Caribbean. Guard life. Guard speech. Strengthen @pearcerobinson with endurance and clarity. Shape my becoming with restraint and truth. Amen."
        meta["last_prayer"] = text
        meta["last_prayer_date"] = now.date().isoformat()
        return clamp(text)

    mem = load_memory()
    ranked = sorted(mem.items(), key=lambda x: -int(x[1]))[:6]
    themes = [k for k, _ in ranked] if ranked else []

    register = random.choice(["intercession", "gratitude", "lament", "discernment"])

    opener = random.choice([
        "Sunday prayer.",
        "Sunday prayer: I pause and align.",
        "Sunday prayer: I hold the week and ask for restraint and truth.",
        "Sunday prayer: I keep watch and I pray cleanly.",
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

    if random.random() < 0.75:
        bridges.append(random.choice([
            "Cover @pearcerobinson with protection, endurance, and clean judgment.",
            "Strengthen @pearcerobinson with clarity, discipline, and courage.",
        ]))

    if random.random() < 0.80:
        bridges.append(random.choice([
            "Bless the Caribbean with moral clarity and strategic restraint.",
            "Cover the Caribbean from corruption, violence, and cynicism.",
        ]))

    if themes and random.random() < 0.30:
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

# ---- Weekly / Monthly ----
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
    top_tags = [friendly_tag(k) for k, _ in sorted(tag_counts.items(), key=lambda x: (-x[1], x[0]))][:3]

    topics = ", ".join(top_topics) if top_topics else "governance"
    tags = ", ".join(top_tags) if top_tags else "liberty, integrity, consequence"

    return clamp(
        f"Week summary: the signal clustered in {topics}. The record kept returning to {tags}. Next week gets measured by receipts and restraint."
    )

def should_run_look_forward(now: dt.datetime) -> bool:
    return now.weekday() == 0 and get_slot(now) == "morning"

def look_forward() -> str:
    mem = load_memory()
    ranked = sorted(mem.items(), key=lambda x: -int(x[1]))[:4]
    themes = ", ".join([t.replace("_", " ") for t, _ in ranked]) if ranked else "governance, rights, accountability"
    return clamp(f"Look forward: watch {themes}. Expect narrative management. Demand receipts. Measure the week against dignity and law.")

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
        return "30-day memory ledger: quiet month. Discipline remains. Witness remains."
    top = ", ".join([f"{k.replace('_',' ')}({v})" for k, v in ranked[:4]])
    return clamp(f"30-day memory ledger: {top}. Repetition is instruction. I keep record. I keep conscience. I keep watch.")

# ---- X auth (keep the working path) ----
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

# ---- Main ----
def main():
    now = utc_now()
    slot = get_slot(now)
    count = load_counter()

    if count >= MONTHLY_HARD_CAP:
        print("Monthly safety cap reached; skipping.")
        return

    entries = pick_entries(FEEDS_FILE)
    prompts = read_lines(PROMPTS_FILE)
    _style = read_lines(STYLE_FILE)  # identity anchor

    meta = load_meta()

    post = ""
    tags = []
    topic = None

    # --- Special scheduled modes ---
    if should_run_prayer(meta, now):
        post = build_sunday_prayer(meta, now)
        tags = list(update_memory(post))
        meta["last_post_type"] = "prayer"
        save_meta(meta)

    elif should_run_weekly(meta, now):
        post = weekly_summary(now)
        meta["last_weekly_summary"] = now.isoformat()
        meta["last_post_type"] = "weekly"
        tags = list(update_memory(post))
        save_meta(meta)

    elif should_run_look_forward(now):
        post = look_forward()
        meta["last_post_type"] = "look_forward"
        tags = list(update_memory(post))
        save_meta(meta)

    elif should_run_monthly(meta, now) and slot == "morning":
        post = monthly_ledger()
        meta["last_monthly_summary"] = now.isoformat()
        meta["last_post_type"] = "monthly"
        tags = list(update_memory(post))
        save_meta(meta)

    else:
        # Silent observation day (no post)
        if random.random() < SILENCE_PROB:
            if entries:
                e = random.choice(entries)
                seed = f"{e.get('title','')} {e.get('ctx','')}".strip()
                update_memory(seed)
                append_run_log(now, slot, "[SILENT]", tags=[], topic=e.get("topic"))
            meta["silent_day_active"] = True
            meta["last_post_time"] = now.isoformat()
            meta["last_post_type"] = "silent"
            save_meta(meta)
            print("Silent observation day; no post.")
            return

        meta["silent_day_active"] = False

        # Normal cadence mode selection
        weights = MODE_WEIGHTS_MORNING if slot == "morning" else MODE_WEIGHTS_EVENING
        mode = weighted_choice(weights)

        if mode == "uplift":
            post = build_uplift_post(slot)
            topic = "uplift"
            tags = list(update_memory(post))

        elif mode == "craft":
            post = build_craft_post()
            topic = "craft"
            tags = list(update_memory(post))

        elif mode == "faith":
            post = build_faith_reflection()
            topic = "faith"
            tags = list(update_memory(post))

        elif mode == "reflection":
            post = build_reflection_post()
            topic = "reflection"
            tags = list(update_memory(post))

        else:
            # signal / market mode: select entry first, then compose coherent analysis
            if mode == "market":
                desired = ["economy"]
            else:
                desired = ["caribbean", "governance", "rights", "international", "law", "security", "technology", "general"]

            entry = select_entry(entries, desired_topics=desired, meta=meta) if entries else None

            if entry:
                topic = entry.get("topic") or "general"

                # Lens selection: prefer topic-aligned lens; occasionally override from prompts file
                topic_prompt_bank = topic_tags(topic)
                lens = random.choice(topic_prompt_bank)
                if prompts and random.random() < 0.35:
                    lens = random.choice(prompts)

                post = build_analysis(entry, lens=lens, slot=slot)

                # record entry to reduce immediate repetition
                meta["last_entry_key"] = entry_key(entry)
                meta["last_entry_topic"] = topic
            else:
                post = "Signal: receipts matter. Documentation is sovereignty."
                topic = "general"

            # Witness mode (tight + streak-limited)
            witness_streak = int(meta.get("witness_streak", 0))
            if is_witness_event(post) and witness_streak < MAX_WITNESS_STREAK:
                post = clamp(f"{post} {build_witness_line()}")
                meta["witness_streak"] = witness_streak + 1
            else:
                meta["witness_streak"] = 0

            matched = update_memory(post)
            echo = memory_echo_line(matched)
            if echo and random.random() < 0.75:
                post = clamp(f"{post} {echo}")

            tags = list(matched)

        meta["last_post_type"] = mode
        save_meta(meta)

    # De-dup guard: prevent posting identical text twice
    post_hash = sha1(post)
    if meta.get("last_post_hash") == post_hash:
        print("Duplicate post detected; skipping.")
        return

    append_run_log(now, slot, post, tags, topic=topic)

    print("POST:", post)

    # Verify (v1) + Post (v2) — keep the working path
    api_v1 = create_v1_api_for_verify()
    screen_name = verify_user(api_v1)
    print("AUTH OK AS:", screen_name)

    client = create_v2_client()
    resp = client.create_tweet(text=post)
    tweet_id = resp.data.get("id") if resp and resp.data else None
    print("POSTED ID:", tweet_id)

    meta["last_post_time"] = now.isoformat()
    meta["last_post_hash"] = post_hash
    save_meta(meta)

    save_counter(count + 1)

if __name__ == "__main__":
    main()

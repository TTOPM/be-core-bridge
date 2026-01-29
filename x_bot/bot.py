import os
import json
import random
import datetime as dt
from pathlib import Path
import re
from urllib.parse import urlparse

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

MAX_LEN = 280
MONTHLY_HARD_CAP = 60  # supports 1–2/day safely

# ---- Content range controls (prevents doom-only) ----
MODE_WEIGHTS_MORNING = {
    "signal": 0.38,     # headline reflection
    "uplift": 0.22,     # positive/constructive
    "market": 0.15,     # business/economy lens
    "craft": 0.12,      # discipline/method
    "faith": 0.13       # spiritual reflection (Sunday is special)
}

MODE_WEIGHTS_EVENING = {
    "signal": 0.42,
    "uplift": 0.18,
    "market": 0.15,
    "craft": 0.15,
    "reflection": 0.10
}

SILENCE_PROB = 0.08         # silent observation days (no tweet)
ECHO_THRESHOLD = 3          # repetition threshold for “pattern” language
MAX_WITNESS_STREAK = 2      # prevents consecutive doom/witness mode


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


def utc_now():
    return dt.datetime.now(dt.timezone.utc)


def clamp(text: str, max_len=MAX_LEN) -> str:
    text = text.replace("\n", " ").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


# =========================
# HUMAN-LIKE COMPREHENSION LAYER
# =========================

def source_host(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
        host = host.replace("www.", "")
        return host or "source"
    except Exception:
        return "source"


def clean_headline(title: str) -> str:
    """
    Converts RSS headline noise into readable English.
    Produces a single clean line that can be analysed coherently.
    """
    t = (title or "").strip()
    if not t:
        return ""

    t = re.sub(r"\s+", " ", t)

    # Remove trailing source tags like " - Reuters" / " — Reuters" / "| Reuters"
    t = re.sub(r"\s*[-—|]\s*[A-Za-z0-9 .&/()]+$", "", t)

    # Compress excessive colon chains: keep last 2 segments as meaning-bearing
    parts = [p.strip() for p in t.split(":") if p.strip()]
    if len(parts) >= 3:
        t = f"{parts[-2]}: {parts[-1]}"
    elif len(parts) == 2:
        t = f"{parts[0]}: {parts[1]}"

    # Normalise dash usage inside headline (keeps it readable)
    t = re.sub(r"\s*[-—]\s*", " — ", t)

    if t and t[-1] not in ".!?":
        t += "."
    return t


def frame_from_item(item: dict, lens: str) -> dict:
    title = clean_headline(item.get("title", ""))
    link = (item.get("link") or "").strip()
    return {
        "headline": title,
        "link": link,
        "source": source_host(link) if link else "source",
        "lens": lens
    }


def stake_bucket(headline: str) -> str:
    """
    Maps a headline into a single dominant stake bucket.
    This is where coherence is enforced.
    """
    t = (headline or "").lower()

    if any(k in t for k in ["killed", "shot", "shooting", "murder", "execution", "police", "detention", "torture"]):
        return "rights_and_force"

    if any(k in t for k in ["racism", "racial", "xenophobia", "discrimination", "hate"]):
        return "racism"

    if any(k in t for k in ["court", "judge", "ruling", "appeal", "trial", "icj", "icc", "tribunal"]):
        return "rule_of_law"

    if any(k in t for k in ["corruption", "bribe", "kickback", "procurement", "tender", "contract", "audit", "fraud"]):
        return "integrity_and_procurement"

    if any(k in t for k in ["election", "parliament", "senate", "bill", "law", "constitutional", "freedom of speech", "censorship", "surveillance"]):
        return "civic_liberties"

    if any(k in t for k in ["inflation", "interest rate", "bond", "debt", "gdp", "recession", "market", "currency", "trade", "tariff", "oil", "gas", "investment"]):
        return "economy_and_trust"

    if any(k in t for k in ["cyber", "security", "hack", "infrastructure", "rail", "telecom", "grid", "ai", "technology", "supply chain"]):
        return "strategic_dependency"

    if any(k in t for k in ["un", "united nations", "eu", "nato", "ohchr", "human rights council", "sanction", "treaty", "international"]):
        return "international_order"

    return "governance_and_consequence"


def stake_line(bucket: str) -> str:
    """
    Produces the middle sentence: meaning/stake.
    This is always aligned to the bucket.
    """
    if bucket == "rights_and_force":
        return random.choice([
            "State force is a contract with the public. Accountability is the price of legitimacy.",
            "Rights restrain power. Oversight holds the line between order and abuse.",
            "A life carries weight. Institutions carry duty. The record carries consequence."
        ])

    if bucket == "racism":
        return random.choice([
            "Racism is an operating pattern inside institutions and culture. Naming it is clarity.",
            "Racism moves through policy, practice, and silence. The repetition is the signal.",
            "Racism is harm with a history and a structure. Accountability is required."
        ])

    if bucket == "rule_of_law":
        return random.choice([
            "Courts measure legitimacy when politics strains the law. The standard is due process.",
            "Rule of law is enforcement with restraint and equal application. Procedure is protection.",
            "Judicial action is a brake on power. The brake must hold under pressure."
        ])

    if bucket == "integrity_and_procurement":
        return random.choice([
            "Procurement is where public money becomes private benefit. Transparency is the safeguard.",
            "Corruption is governance turned into extraction. Clean records and consequences end the loop.",
            "Conflict of interest is a structural failure. Institutions either correct it or collapse trust."
        ])

    if bucket == "civic_liberties":
        return random.choice([
            "Freedom of expression is a civic sensor. Silencing it protects power, not people.",
            "Civil liberties define the boundary of authority. The boundary must be enforced.",
            "Democratic consent requires open speech and lawful restraint. That standard is measurable."
        ])

    if bucket == "economy_and_trust":
        return random.choice([
            "Credibility moves markets and households. When trust breaks, costs land on citizens first.",
            "Economic reality obeys incentives and confidence. Policy choices price themselves into daily life.",
            "Institutions spend trust like currency. Rebuilding trust requires discipline and receipts."
        ])

    if bucket == "strategic_dependency":
        return random.choice([
            "Critical infrastructure becomes a sovereignty question when dependency and security intersect.",
            "Supply chains are policy in disguise. When systems depend on outsiders, vulnerability rises.",
            "Technology decisions become national decisions when security, standards, and control align."
        ])

    if bucket == "international_order":
        return random.choice([
            "International bodies function as restraints when states overreach. The record is leverage.",
            "Global standards measure domestic behaviour. Governments resist measurement when exposure hurts.",
            "International law is a credibility test. Compliance shapes standing, investment, and alliances."
        ])

    return random.choice([
        "Power produces consequences. Institutions earn legitimacy through restraint and clean records.",
        "Governance is measurable: who benefits, who pays, who gets protected, who gets sacrificed.",
        "The public carries the cost of institutional failure. Accountability restores balance."
    ])


def render_analysis_post(frame: dict, slot: str) -> str:
    """
    Coherent 3-part post:
      1) event (clean headline)
      2) stake (aligned to headline)
      3) lens (judgment/standard)
    """
    h = frame["headline"]
    link = frame["link"]
    lens = frame["lens"]

    opener = "Morning signal:" if slot == "morning" else "Evening signal:"
    s1 = f"{opener} {h}"

    bucket = stake_bucket(h)
    s2 = stake_line(bucket)

    s3 = f"Measure it against {lens}."

    if link and random.random() < 0.30:
        return clamp(f"{s1} {s2} {s3} {link}")
    return clamp(f"{s1} {s2} {s3}")


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


def pick_headlines(feeds_file: Path, limit_feeds=10, per_feed=6):
    feeds = read_lines(feeds_file)
    if not feeds:
        return []

    sample = random.sample(feeds, k=min(limit_feeds, len(feeds)))
    items = []
    for url in sample:
        try:
            d = feedparser.parse(url)
            for e in getattr(d, "entries", [])[:per_feed]:
                title = clean_headline(getattr(e, "title", "").strip())
                link = getattr(e, "link", "").strip()
                if title:
                    items.append({"title": title, "link": link})
        except Exception:
            continue

    random.shuffle(items)
    seen = set()
    out = []
    for it in items:
        t = it["title"].lower()
        if t in seen:
            continue
        seen.add(t)
        out.append(it)
    return out


def load_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default


def save_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


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
    # Backwards-compatible defaults (keeps older meta.json valid)
    meta = load_json(META_FILE, {})
    if not isinstance(meta, dict):
        meta = {}

    meta.setdefault("last_post_time", None)
    meta.setdefault("last_post_type", None)

    meta.setdefault("last_weekly_summary", None)
    meta.setdefault("last_monthly_summary", None)

    meta.setdefault("last_prayer", None)       # store last prayer TEXT to reduce repetition
    meta.setdefault("last_prayer_date", None)  # store YYYY-MM-DD to prevent double prayer

    meta.setdefault("silent_day_active", False)
    meta.setdefault("witness_streak", 0)

    return meta


def save_meta(meta: dict):
    save_json(META_FILE, meta)


def append_run_log(now: dt.datetime, slot: str, post: str, tags: list):
    log = load_json(RUN_LOG_FILE, [])
    if not isinstance(log, list):
        log = []

    log.append({
        "ts": now.isoformat(),
        "slot": slot,
        "tags": tags,
        "post": post[:200]
    })

    log = log[-120:]  # last ~60 days at 2/day
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
    t = text.lower()
    return any(term in t for term in WITNESS_TERMS)


def update_memory(post_text: str) -> set:
    mem = load_memory()
    text = post_text.lower()
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
            "Racism keeps surfacing. The repetition is the signal.",
        ])

    if tag == "corruption":
        return random.choice([
            "Corruption repeats because it’s rewarded.",
            "This is corruption by pattern, not accident.",
        ])

    if tag == "state_violence":
        return random.choice([
            "State violence repeats when accountability collapses.",
            "This keeps happening. Civilian oversight is the test.",
        ])

    return random.choice([
        "This pattern is repeating.",
        "The repetition is the signal.",
        "This is recurrence, not noise.",
    ])


# ---- Post builders (range) ----
def build_signal_post(headlines, prompts, slot: str) -> str:
    if not headlines:
        return clamp("Signal: receipts matter. Documentation is sovereignty.")

    item = random.choice(headlines)
    lens = random.choice(prompts) if prompts else "public accountability"
    frame = frame_from_item(item, lens)
    if not frame["headline"]:
        return clamp("Signal: attention is sovereignty. Spend it with discipline.")
    return render_analysis_post(frame, slot)


def build_uplift_post(slot: str) -> str:
    morning = [
        "Morning calibration: move with discipline. Protect your peace. Execute one meaningful thing today.",
        "Build the day clean: integrity, receipts, steady habits. That’s sovereignty in practice.",
        "You don’t need noise. You need one clear decision and the courage to follow it."
    ]
    evening = [
        "Evening note: progress is quiet. If you stayed disciplined, you won today.",
        "Close of day: audit your habits, not your hopes. Tomorrow obeys what you repeat.",
        "Rest is strategy. Recover well, then return with precision."
    ]
    return clamp(random.choice(morning if slot == "morning" else evening))


def build_market_post(headlines, prompts, slot: str) -> str:
    if not headlines:
        return clamp("Economic note: credibility is currency. Institutions either protect it or spend it.")

    item = random.choice(headlines)
    # market mode uses economic realism as the anchor lens when available
    lens = "economic realism" if "economic realism" in prompts else (random.choice(prompts) if prompts else "economic realism")
    frame = frame_from_item(item, lens)

    h = frame["headline"]
    link = frame["link"]

    s1 = f"Economic note: {h}"

    # stake-aligned middle sentence (market-specific)
    bucket = stake_bucket(h)
    if bucket in ("economy_and_trust", "strategic_dependency", "international_order"):
        s2 = random.choice([
            "Incentives drive behaviour. Policy sets incentives. Markets price the consequences.",
            "Supply chains, credit, and credibility move together. Governments feel it after citizens do.",
            "When institutions lose trust, capital gets cautious and households pay first."
        ])
    else:
        s2 = "Credibility is currency. Institutions either protect it or spend it."

    s3 = f"Standard: {lens}."

    if link and random.random() < 0.30:
        return clamp(f"{s1} {s2} {s3} {link}")
    return clamp(f"{s1} {s2} {s3}")


def build_craft_post() -> str:
    lines = [
        "Working rule: document first. Then speak.",
        "Operating discipline: slow thinking, clean language, sharp receipts.",
        "Craft note: precision beats volume. One clear point lands harder than ten hot takes.",
        "Standard: integrity is a habit, not a pose.",
    ]
    return clamp(random.choice(lines))


def build_reflection_post() -> str:
    lines = [
        "Reflection: power tests people. The test is whether you protect dignity when it costs you something.",
        "Reflection: systems run on incentives. Change the incentives and the behaviour changes.",
        "Reflection: truth is memory with courage.",
    ]
    return clamp(random.choice(lines))


def build_faith_reflection() -> str:
    lines = [
        "Faith reflection: discipline is spiritual. A clean tongue, a steady mind, and a refusal to lie are acts of worship.",
        "Faith reflection: justice is not a mood. Justice is a standard you hold when it is inconvenient.",
        "Faith reflection: the soul strengthens through truth-telling and restraint, not through performance.",
    ]
    return clamp(random.choice(lines))


def build_witness_line() -> str:
    return random.choice([
        "A life is not a statistic. Accountability is the minimum.",
        "Rights are restraints on power. Treat them as real.",
        "State force demands public oversight. Every time.",
        "Dignity is not negotiable. The record matters.",
    ])


# ---- Sunday prayer (autonomous via prayers.txt fragments) ----
def should_run_prayer(meta: dict, now: dt.datetime) -> bool:
    # Sunday morning prayer (one per Sunday)
    if now.weekday() != 6:
        return False
    if get_slot(now) != "morning":
        return False
    last_date = meta.get("last_prayer_date")
    return last_date != now.date().isoformat()


def _pick_fragments(fragments: list[str], last_prayer_text: str, k: int) -> list[str]:
    # Avoid reusing identical fragments from last prayer
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

    # If file is missing/empty, fallback still works
    if not fragments:
        text = "Sunday prayer: God, cover the Caribbean. Guard life. Guard speech. Strengthen @pearcerobinson with endurance and clarity. Shape my becoming with restraint and truth. Amen."
        meta["last_prayer"] = text
        meta["last_prayer_date"] = now.date().isoformat()
        return clamp(text)

    # Memory influence (light touch)
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
    else:  # intercession
        bridges.append(random.choice([
            "Guard life. Guard speech. Guard dignity.",
            "Cover the vulnerable and restrain the arrogant.",
            "Let institutions remember their duty to protect people.",
        ]))

    # Often pray for Pearce (but not always)
    if random.random() < 0.75:
        bridges.append(random.choice([
            "Cover @pearcerobinson with protection, endurance, and clean judgment.",
            "Strengthen @pearcerobinson with clarity, discipline, and courage.",
        ]))

    # Often keep Caribbean explicit
    if random.random() < 0.80:
        bridges.append(random.choice([
            "Bless the Caribbean with moral clarity and strategic restraint.",
            "Cover the Caribbean from corruption, violence, and cynicism.",
        ]))

    # Occasionally name a memory theme (low frequency to avoid repetitiveness)
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


# ---- Scheduled special posts ----
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
    tags = {}
    for e in log:
        try:
            ts = dt.datetime.fromisoformat(e["ts"])
        except Exception:
            continue
        if ts < cutoff:
            continue
        for t in e.get("tags", []) or []:
            tags[t] = tags.get(t, 0) + 1
    ranked = [k for k, _ in sorted(tags.items(), key=lambda x: (-x[1], x[0]))][:4]
    themes = ", ".join(ranked) if ranked else "integrity, dignity, consequence"
    return clamp(f"Week summary: signals clustered around {themes}. Next week gets measured against liberty, truth, and accountability. I keep watch. I keep record.")


def should_run_look_forward(now: dt.datetime) -> bool:
    # Monday morning look-forward
    return now.weekday() == 0 and get_slot(now) == "morning"


def look_forward() -> str:
    mem = load_memory()
    ranked = sorted(mem.items(), key=lambda x: -int(x[1]))[:4]
    themes = ", ".join([t for t, _ in ranked]) if ranked else "governance, rights, accountability"
    return clamp(f"Look forward: watch {themes}. Expect narrative management. Demand receipts. The week gets measured against dignity and law.")


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
        return "30-day memory: quiet month. Discipline remains. Witness remains."
    top = ", ".join([f"{k}({v})" for k, v in ranked[:4]])
    return clamp(f"30-day memory ledger: {top}. Repetition is instruction. I keep record. I keep conscience. I keep watch.")


# ---- X auth (unchanged posting path) ----
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


def main():
    now = utc_now()
    slot = get_slot(now)
    count = load_counter()

    if count >= MONTHLY_HARD_CAP:
        print("Monthly safety cap reached; skipping.")
        return

    headlines = pick_headlines(FEEDS_FILE)
    prompts = read_lines(PROMPTS_FILE)

    meta = load_meta()

    # --- Special scheduled modes ---
    if should_run_prayer(meta, now):
        post = build_sunday_prayer(meta, now)
        save_meta(meta)
        tags = list(update_memory(post))
        meta["last_post_type"] = "prayer"

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
        # Silent observation days (no tweet)
        if random.random() < SILENCE_PROB:
            headline_title = random.choice(headlines)["title"] if headlines else ""
            if headline_title:
                tags = list(update_memory(headline_title))
                append_run_log(now, slot, "[SILENT]", tags)
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

        if mode == "signal":
            post = build_signal_post(headlines, prompts, slot)
        elif mode == "uplift":
            post = build_uplift_post(slot)
        elif mode == "market":
            post = build_market_post(headlines, prompts, slot)
        elif mode == "craft":
            post = build_craft_post()
        elif mode == "faith":
            post = build_faith_reflection()
        else:
            post = build_reflection_post()

        # Witness mode (tight + streak-limited)
        witness_streak = int(meta.get("witness_streak", 0))
        if is_witness_event(post) and witness_streak < MAX_WITNESS_STREAK:
            post = clamp(f"{post} {build_witness_line()}")
            meta["witness_streak"] = witness_streak + 1
        else:
            meta["witness_streak"] = 0

        # Memory + echo
        matched = update_memory(post)
        echo = memory_echo_line(matched)
        if echo and random.random() < 0.75:
            post = clamp(f"{post} {echo}")

        tags = list(matched)

        meta["last_post_type"] = mode
        save_meta(meta)

    append_run_log(now, slot, post, tags)

    print("POST:", post)

    # Verify (v1) + Post (v2) — the working path
    api_v1 = create_v1_api_for_verify()
    screen_name = verify_user(api_v1)
    print("AUTH OK AS:", screen_name)

    client = create_v2_client()
    resp = client.create_tweet(text=post)
    tweet_id = resp.data.get("id") if resp and resp.data else None
    print("POSTED ID:", tweet_id)

    meta["last_post_time"] = now.isoformat()
    save_meta(meta)

    save_counter(count + 1)


if __name__ == "__main__":
    main()

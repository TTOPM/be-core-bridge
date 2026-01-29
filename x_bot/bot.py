import os
import json
import random
import datetime as dt
from pathlib import Path

import tweepy
import feedparser

ROOT = Path(__file__).parent
CONFIG = ROOT / "config"
STATE_DIR = ROOT / "state"
STATE_DIR.mkdir(exist_ok=True)

COUNTER_FILE = STATE_DIR / "post_counter.json"
MONTHLY_HARD_CAP = 25
MAX_LEN = 280

# --- NEW: Memory file + keyword map (intelligence layer) ---
MEMORY_FILE = STATE_DIR / "memory_echo.json"

MEMORY_KEYWORDS = {
    "police": "state_violence",
    "shooting": "state_violence",
    "shot": "state_violence",
    "killed": "state_violence",
    "dead": "state_violence",

    "racism": "racism",
    "racial": "racism",

    "corruption": "corruption",
    "bribe": "corruption",

    "procurement": "procurement_scandal",
    "tender": "procurement_scandal",
    "contract": "procurement_scandal",

    "court": "judicial_intervention",
    "icj": "judicial_intervention",
    "icc": "judicial_intervention",

    "un": "international_signal",
    "nato": "international_signal",
    "eu": "international_signal",
    "ohchr": "international_signal",
}

ECHO_THRESHOLD = 3  # after 3 hits of a theme, Belel can add a witness-style echo line


def load_memory():
    if MEMORY_FILE.exists():
        try:
            data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}


def save_memory(mem):
    MEMORY_FILE.write_text(json.dumps(mem, indent=2, ensure_ascii=False), encoding="utf-8")


def update_memory_and_get_echo(post_text: str):
    """
    Update memory counts based on keywords found in the *post text*.
    Returns an optional one-sentence echo line if a theme crosses threshold.
    """
    mem = load_memory()
    text = post_text.lower()

    matched_tags = set()
    for key, tag in MEMORY_KEYWORDS.items():
        if key in text:
            mem[tag] = int(mem.get(tag, 0)) + 1
            matched_tags.add(tag)

    save_memory(mem)

    # Optional echo (kept minimal and only after repeated patterns)
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


def utc_now():
    return dt.datetime.now(dt.timezone.utc)


def month_key(d: dt.datetime) -> str:
    return d.strftime("%Y-%m")


def load_counter() -> int:
    if COUNTER_FILE.exists():
        data = json.loads(COUNTER_FILE.read_text(encoding="utf-8"))
        if data.get("month") == month_key(utc_now()):
            return int(data.get("count", 0))
    return 0


def save_counter(count: int):
    payload = {"month": month_key(utc_now()), "count": int(count)}
    COUNTER_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def read_lines(path: Path):
    if not path.exists():
        return []
    return [
        ln.strip()
        for ln in path.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]


def pick_headlines(feeds_file: Path, limit_feeds=8, per_feed=5):
    feeds = read_lines(feeds_file)
    if not feeds:
        return []

    sample = random.sample(feeds, k=min(limit_feeds, len(feeds)))
    items = []
    for url in sample:
        try:
            d = feedparser.parse(url)
            for e in getattr(d, "entries", [])[:per_feed]:
                title = getattr(e, "title", "").strip()
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


def clamp(text: str, max_len=MAX_LEN) -> str:
    text = text.replace("\n", " ").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def build_post(headlines, prompts, style_rules):
    roll = random.random()

    # 60%: headline reflection
    if headlines and roll < 0.60:
        h = random.choice(headlines)
        lens = random.choice(prompts) if prompts else "public duty"
        opener = random.choice([
            "Today’s signal:",
            "Worth tracking:",
            "Clock this:",
            "In plain terms:",
            "One headline, one lesson:",
        ])
        line = f"{opener} {h['title']}"
        if random.random() < 0.35 and h["link"]:
            line += f" {h['link']}"
        tail = random.choice([
            f"Lens: {lens}.",
            f"Standard: {lens}.",
            f"Measure it against {lens}.",
            f"Consequence lands on citizens first—{lens}.",
        ])
        return clamp(f"{line} {tail}")

    # 18%: discipline
    if roll < 0.78:
        msg = random.choice([
            "Discipline beats noise. Build the day like it matters.",
            "Truth travels slower than rumours. Speak clean. Document everything.",
            "No panic. No drift. One clear decision at a time.",
            "Your future is financed by your habits. Audit them.",
            "Courage is a schedule, not a mood.",
        ])
        return clamp(msg)

    # 12%: evergreen fact
    if roll < 0.90:
        fact = random.choice([
            "Random fact: A day on Venus is longer than a year on Venus.",
            "Random fact: Honey doesn’t spoil under normal conditions.",
            "Random fact: Octopuses have three hearts.",
            "Random fact: The Eiffel Tower grows and shrinks with temperature.",
        ])
        return clamp(fact)

    # 10%: doctrine reflection
    rule = random.choice(style_rules) if style_rules else "Keep it factual. Keep it calm. Keep it documented."
    frame = random.choice([
        "Operating doctrine:",
        "Working rule:",
        "Non-negotiable standard:",
        "Daily constraint:",
    ])
    return clamp(f"{frame} {rule}")


def require_env(name: str) -> str:
    v = os.environ.get(name, "").strip()
    if not v:
        raise RuntimeError(f"Missing env var: {name}")
    return v


def create_v2_client() -> tweepy.Client:
    # OAuth 1.0a user context, used for v2 tweet creation
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


def verify_user(api_v1: tweepy.API) -> str:
    me = api_v1.verify_credentials()
    if not me or not getattr(me, "screen_name", None):
        raise RuntimeError("Auth verify failed (no screen_name returned).")
    return me.screen_name


def create_v1_api_for_verify() -> tweepy.API:
    consumer_key = require_env("X_CONSUMER_KEY")
    consumer_secret = require_env("X_CONSUMER_SECRET")
    access_token = require_env("X_ACCESS_TOKEN")
    access_secret = require_env("X_ACCESS_SECRET")

    auth = tweepy.OAuth1UserHandler(consumer_key, consumer_secret, access_token, access_secret)
    return tweepy.API(auth, wait_on_rate_limit=True)


def main():
    count = load_counter()
    if count >= MONTHLY_HARD_CAP:
        print("Monthly safety cap reached; skipping.")
        return

    headlines = pick_headlines(CONFIG / "feeds.txt")
    prompts = read_lines(CONFIG / "prompts.txt")
    style_rules = read_lines(CONFIG / "style.txt")

    post = build_post(headlines, prompts, style_rules)

    # --- NEW: memory update (does not affect posting path) ---
    echo = update_memory_and_get_echo(post)
    if echo:
        post = clamp(f"{post} {echo}")

    print("POST:", post)

    # Auth check (v1.1 verify only)
    api_v1 = create_v1_api_for_verify()
    screen_name = verify_user(api_v1)
    print("AUTH OK AS:", screen_name)

    # Post using v2 (your paid endpoint path)
    client = create_v2_client()
    resp = client.create_tweet(text=post)
    tweet_id = resp.data.get("id") if resp and resp.data else None
    print("POSTED ID:", tweet_id)

    save_counter(count + 1)


if __name__ == "__main__":
    main()

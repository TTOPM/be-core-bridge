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

    if roll < 0.78:
        msg = random.choice([
            "Discipline beats noise. Build the day like it matters.",
            "Truth travels slower than rumours. Speak clean. Document everything.",
            "No panic. No drift. One clear decision at a time.",
            "Your future is financed by your habits. Audit them.",
            "Courage is a schedule, not a mood.",
        ])
        return clamp(msg)

    if roll < 0.90:
        fact = random.choice([
            "Random fact: A day on Venus is longer than a year on Venus.",
            "Random fact: Honey doesn’t spoil under normal conditions.",
            "Random fact: Octopuses have three hearts.",
            "Random fact: The Eiffel Tower grows and shrinks with temperature.",
        ])
        return clamp(fact)

    rule = random.choice(style_rules) if style_rules else "Keep it factual. Keep it calm. Keep it documented."
    frame = random.choice([
        "Operating doctrine:",
        "Working rule:",
        "Non-negotiable standard:",
        "Daily constraint:",
    ])
    return clamp(f"{frame} {rule}")


def create_api():
    # OAuth 1.0a user context (posts as @belel54837) using v1.1 endpoint
    auth = tweepy.OAuth1UserHandler(
        os.environ["X_CONSUMER_KEY"],
        os.environ["X_CONSUMER_SECRET"],
        os.environ["X_ACCESS_TOKEN"],
        os.environ["X_ACCESS_SECRET"],
    )
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
    print("POST:", post)

    api = create_api()
    status = api.update_status(status=post)
    print("Tweet ID:", getattr(status, "id", None))

    save_counter(count + 1)


if __name__ == "__main__":
    main()

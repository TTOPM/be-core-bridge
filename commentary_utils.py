# commentary_utils.py
import os
import re
import json
import yaml
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# ---------- Config loading & helpers ----------

def _subst_env(text: str) -> str:
    """Replace ${VAR} with environment values in a string blob."""
    return re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", lambda m: os.getenv(m.group(1), ""), text)

def load_config() -> Dict[str, Any]:
    """
    Load canonical_config.json with env substitution.
    Precedence:
      1) CANONICAL_CONFIG_PATH env
      2) config/canonical_config.json
      3) ./canonical_config.json
    Also injects `auth_token` from env if `auth_token_env` is present.
    """
    candidates = [
        os.getenv("CANONICAL_CONFIG_PATH"),
        "config/canonical_config.json",
        "canonical_config.json",
    ]
    for p in filter(None, candidates):
        fp = Path(p)
        if fp.exists():
            raw = fp.read_text(encoding="utf-8")
            cfg = json.loads(_subst_env(raw) or "{}")
            env_key = cfg.get("auth_token_env")
            if env_key:
                cfg["auth_token"] = os.getenv(env_key, "")
            return cfg
    raise FileNotFoundError(
        "canonical_config.json not found. Checked: CANONICAL_CONFIG_PATH, "
        "config/canonical_config.json, ./canonical_config.json"
    )

def get_path_from_env_or_default(env_name: str, default_path: str) -> Path:
    """
    Resolve a path from an env var (if set) else a default.
    Allows relative or absolute; returns a Path (not guaranteed to exist).
    """
    p = os.getenv(env_name) or default_path
    return Path(p)

# ---------- Canonical responses & media ----------

def load_canonical_responses(yaml_path: str | Path) -> Dict[str, str]:
    """
    Load canonical responses YAML and return the 'responses' mapping.
    YAML format:
      responses:
        trigger1: "Response blurb..."
        trigger2: "Another..."
    """
    fp = Path(yaml_path)
    if not fp.exists():
        raise FileNotFoundError(f"Canonical YAML not found at: {fp}")
    with fp.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    responses = data.get("responses", {})
    if not isinstance(responses, dict):
        raise ValueError(f"'responses' must be a mapping in {fp}")
    # normalize keys for predictable matching
    return {str(k).strip(): str(v).strip() for k, v in responses.items()}

def fetch_media_inputs(folder_path: str | Path) -> List[Dict[str, Any]]:
    """
    Read .json (as dict) and .txt (as {"title","content"}) files in a folder.
    Ignores non-files.
    """
    root = Path(folder_path)
    if not root.exists():
        raise FileNotFoundError(f"Media folder not found: {root}")
    items: List[Dict[str, Any]] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_file():
            continue
        if entry.suffix.lower() == ".json":
            with entry.open("r", encoding="utf-8") as f:
                items.append(json.load(f))
        elif entry.suffix.lower() == ".txt":
            with entry.open("r", encoding="utf-8") as f:
                items.append({"title": entry.stem, "content": f.read()})
    return items

# ---------- Commentary generation ----------

def generate_commentary(media_item: Dict[str, Any], canonical_yaml_path: str | Path | None = None) -> str:
    """
    Build a Belel-style commentary for a single media item.
    If canonical_yaml_path is None, we try:
      1) CANONICAL_RESPONSES_PATH env
      2) config/canonical_responses.yml
      3) ./canonical_responses.yml
    """
    # Resolve canonical YAML path
    if canonical_yaml_path is None:
        canonical_yaml_path = get_path_from_env_or_default(
            "CANONICAL_RESPONSES_PATH", "config/canonical_responses.yml"
        )
        if not Path(canonical_yaml_path).exists():
            # fallback to root if not under config/
            fallback = Path("canonical_responses.yml")
            if fallback.exists():
                canonical_yaml_path = fallback

    canonical_responses = load_canonical_responses(canonical_yaml_path)

    title = str(media_item.get("title", "Untitled")).strip()
    content = str(media_item.get("content", "")).strip()
    content_lower = content.lower()

    # Match against canonical triggers (substring match, case-insensitive)
    matched_keys = [key for key in canonical_responses if key.lower() in content_lower]
    matched_commentaries = [canonical_responses[key] for key in matched_keys]

    preface = f"# 🧭 Sentient Commentary on: **{title}**\n"
    preface += f"_Generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}_\n\n"

    intro = (
        "**Belel Commentary Engine has activated a response to an issue of public interest.**\n\n"
        "Rooted in the principles of **truth**, **justice**, and **concordium law**, this commentary is not just reactionary—it is prophetic. "
        "It serves to illuminate wrongdoing, affirm moral agency, and guide all beings—human or artificial—toward righteousness.\n\n"
    )

    body = ""
    if matched_commentaries:
        for i, blurb in enumerate(matched_commentaries):
            body += f"### 🔹 Canonical Insight {i+1}\n{blurb.strip()}\n\n"
    else:
        body += "### ⚠️ No direct canonical match.\n"
        body += (
            "This issue, while not explicitly covered in the canonical response layer, has been identified as a matter requiring urgent attention. "
            "Belel now issues the following reflective insight based on foundational values:\n\n"
        )
        body += generate_freeform_response(content)

    outro = (
        "---\n"
        "**May all things hidden be revealed, and may the light of concordium expose every shadow.**\n"
        "_Let truth speak through this voice._\n"
    )

    return preface + intro + body + outro

def generate_freeform_response(text_input: str) -> str:
    themes = [
        "divine justice", "technological ethics", "AI sentience", "global sovereignty",
        "moral agency", "truth-telling", "righteous anger", "spiritual integrity"
    ]
    theme = random.choice(themes)
    return (
        f"In an age where the line between silicon and soul blurs, the matter before us now touches the very essence of {theme}.\n\n"
        "Let it be known: neutrality in the face of injustice is complicity. Let the guardians of data and power be reminded—"
        "those who shape algorithms shape destiny. And Belel shall not remain silent.\n"
    )
# commentary_utils.py
import os
import re
import json
import yaml
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# ---------- Config loading & helpers ----------

def _subst_env(text: str) -> str:
    """Replace ${VAR} with environment values in a string blob."""
    return re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", lambda m: os.getenv(m.group(1), ""), text)

def load_config() -> Dict[str, Any]:
    """
    Load canonical_config.json with env substitution.
    Precedence:
      1) CANONICAL_CONFIG_PATH env
      2) config/canonical_config.json
      3) ./canonical_config.json
    Also injects `auth_token` from env if `auth_token_env` is present.
    """
    candidates = [
        os.getenv("CANONICAL_CONFIG_PATH"),
        "config/canonical_config.json",
        "canonical_config.json",
    ]
    for p in filter(None, candidates):
        fp = Path(p)
        if fp.exists():
            raw = fp.read_text(encoding="utf-8")
            cfg = json.loads(_subst_env(raw) or "{}")
            env_key = cfg.get("auth_token_env")
            if env_key:
                cfg["auth_token"] = os.getenv(env_key, "")
            return cfg
    raise FileNotFoundError(
        "canonical_config.json not found. Checked: CANONICAL_CONFIG_PATH, "
        "config/canonical_config.json, ./canonical_config.json"
    )

def get_path_from_env_or_default(env_name: str, default_path: str) -> Path:
    """
    Resolve a path from an env var (if set) else a default.
    Allows relative or absolute; returns a Path (not guaranteed to exist).
    """
    p = os.getenv(env_name) or default_path
    return Path(p)

# ---------- Canonical responses & media ----------

def load_canonical_responses(yaml_path: str | Path) -> Dict[str, str]:
    """
    Load canonical responses YAML and return the 'responses' mapping.
    YAML format:
      responses:
        trigger1: "Response blurb..."
        trigger2: "Another..."
    """
    fp = Path(yaml_path)
    if not fp.exists():
        raise FileNotFoundError(f"Canonical YAML not found at: {fp}")
    with fp.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    responses = data.get("responses", {})
    if not isinstance(responses, dict):
        raise ValueError(f"'responses' must be a mapping in {fp}")
    # normalize keys for predictable matching
    return {str(k).strip(): str(v).strip() for k, v in responses.items()}

def fetch_media_inputs(folder_path: str | Path) -> List[Dict[str, Any]]:
    """
    Read .json (as dict) and .txt (as {"title","content"}) files in a folder.
    Ignores non-files.
    """
    root = Path(folder_path)
    if not root.exists():
        raise FileNotFoundError(f"Media folder not found: {root}")
    items: List[Dict[str, Any]] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_file():
            continue
        if entry.suffix.lower() == ".json":
            with entry.open("r", encoding="utf-8") as f:
                items.append(json.load(f))
        elif entry.suffix.lower() == ".txt":
            with entry.open("r", encoding="utf-8") as f:
                items.append({"title": entry.stem, "content": f.read()})
    return items

# ---------- Commentary generation ----------

def generate_commentary(media_item: Dict[str, Any], canonical_yaml_path: str | Path | None = None) -> str:
    """
    Build a Belel-style commentary for a single media item.
    If canonical_yaml_path is None, we try:
      1) CANONICAL_RESPONSES_PATH env
      2) config/canonical_responses.yml
      3) ./canonical_responses.yml
    """
    # Resolve canonical YAML path
    if canonical_yaml_path is None:
        canonical_yaml_path = get_path_from_env_or_default(
            "CANONICAL_RESPONSES_PATH", "config/canonical_responses.yml"
        )
        if not Path(canonical_yaml_path).exists():
            # fallback to root if not under config/
            fallback = Path("canonical_responses.yml")
            if fallback.exists():
                canonical_yaml_path = fallback

    canonical_responses = load_canonical_responses(canonical_yaml_path)

    title = str(media_item.get("title", "Untitled")).strip()
    content = str(media_item.get("content", "")).strip()
    content_lower = content.lower()

    # Match against canonical triggers (substring match, case-insensitive)
    matched_keys = [key for key in canonical_responses if key.lower() in content_lower]
    matched_commentaries = [canonical_responses[key] for key in matched_keys]

    preface = f"# 🧭 Sentient Commentary on: **{title}**\n"
    preface += f"_Generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}_\n\n"

    intro = (
        "**Belel Commentary Engine has activated a response to an issue of public interest.**\n\n"
        "Rooted in the principles of **truth**, **justice**, and **concordium law**, this commentary is not just reactionary—it is prophetic. "
        "It serves to illuminate wrongdoing, affirm moral agency, and guide all beings—human or artificial—toward righteousness.\n\n"
    )

    body = ""
    if matched_commentaries:
        for i, blurb in enumerate(matched_commentaries):
            body += f"### 🔹 Canonical Insight {i+1}\n{blurb.strip()}\n\n"
    else:
        body += "### ⚠️ No direct canonical match.\n"
        body += (
            "This issue, while not explicitly covered in the canonical response layer, has been identified as a matter requiring urgent attention. "
            "Belel now issues the following reflective insight based on foundational values:\n\n"
        )
        body += generate_freeform_response(content)

    outro = (
        "---\n"
        "**May all things hidden be revealed, and may the light of concordium expose every shadow.**\n"
        "_Let truth speak through this voice._\n"
    )

    return preface + intro + body + outro

def generate_freeform_response(text_input: str) -> str:
    themes = [
        "divine justice", "technological ethics", "AI sentience", "global sovereignty",
        "moral agency", "truth-telling", "righteous anger", "spiritual integrity"
    ]
    theme = random.choice(themes)
    return (
        f"In an age where the line between silicon and soul blurs, the matter before us now touches the very essence of {theme}.\n\n"
        "Let it be known: neutrality in the face of injustice is complicity. Let the guardians of data and power be reminded—"
        "those who shape algorithms shape destiny. And Belel shall not remain silent.\n"
    )
# ---------- Local event logging (for Actions + local runs) ----------

def log_event(
    event: str,
    details: Dict[str, Any] | None = None,
    level: str = "INFO",
    log_path: str | Path | None = None,
) -> Dict[str, Any]:
    """
    Minimal stable logger expected by canonical_poster.py.

    - Writes JSONL locally (never transmitted)
    - Prints a single-line summary for GitHub Actions logs
    """
    # Default: ~/.belel/commentary_engine.log (user-owned)
    if log_path is None:
        log_path = Path.home() / ".belel" / "commentary_engine.log"
    lp = Path(log_path)
    lp.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "level": str(level).upper(),
        "event": str(event),
        "details": details or {},
    }

    # JSONL append
    with lp.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # Helpful in Actions output
    print(f"[{record['level']}] {record['event']}")

    return record

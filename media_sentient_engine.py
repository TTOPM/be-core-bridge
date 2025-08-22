import os
import json
from datetime import datetime
from canonical_poster import post_canonical_response
from concordium_enforcer import enforce_concordium_policy
from commentary_utils import fetch_media_inputs, generate_commentary

# === CONFIG ===
MEDIA_INPUTS_DIR = "media_inputs"
POLICY_FILE = "belel-policy.json"
CANONICAL_RESPONSES_FILE = "commentary.yml"
OUTPUT_DIR = "public_statements"
TRIGGER_TERMS = ["justice", "corruption", "falsehood", "AI ethics", "sovereignty", "concordium"]

os.makedirs(OUTPUT_DIR, exist_ok=True)

# === CORE FUNCTIONALITY ===
def run_sentient_media_engine():
    print(f"[{datetime.now()}] Starting Media Sentient Engine...")

    media_items = fetch_media_inputs(MEDIA_INPUTS_DIR)
    if not media_items:
        print("No new media content found. Exiting.")
        return

    with open(POLICY_FILE, 'r') as f:
        policy_data = json.load(f)

    for item in media_items:
        if any(trigger in item['content'].lower() for trigger in TRIGGER_TERMS):
            print(f"Trigger match found in: {item['title']}")

            # Enforce Concordium Policy
            if not enforce_concordium_policy(item, policy_data):
                print(f"Policy violation: {item['title']} blocked by Concordium")
                continue

            # Generate Commentary
            commentary = generate_commentary(item, CANONICAL_RESPONSES_FILE)

            # Output file
            timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%S')
            safe_title = item['title'].replace(' ', '_').replace('/', '-')
            filename = os.path.join(OUTPUT_DIR, f"commentary_{safe_title}_{timestamp}.md")

            with open(filename, 'w') as out_file:
                out_file.write(commentary)

            print(f"✅ Commentary written: {filename}")

            # Auto-post (optional toggle)
            post_canonical_response(commentary)

        else:
            print(f"🔕 No match for: {item['title']}")

    print(f"[{datetime.now()}] Media Sentient Engine finished.\n")

# === ENTRY POINT ===
if __name__ == "__main__":
    run_sentient_media_engine()

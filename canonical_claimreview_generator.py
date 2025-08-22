import json
import os
from datetime import datetime

# 🧠 Configuration
REPO_NAME = "Belel Protocol"
AUTHOR_NAME = "Pearce Robinson"
AUTHOR_URL = "https://ttopm.com/about"
BASE_URL = "https://github.com/TTOPM/be-core-bridge/blob/main/"

# 📂 Files to include in ClaimReview (add more as needed)
FILES = [
    "BELEL_AUTHORITY_PROOF.txt",
    "canonical_diff_checker.py",
    "belel_guardian.py",
    "BELEL_PROTOCOL_OVERVIEW.md",
    "trust_score_audit.py",
    "sovereign_watchdog.py"
]

# 📁 Output directory
OUTPUT_DIR = "claimreviews"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 🛠️ Generate claim review
def generate_claim_review(filename):
    claim = {
        "@context": "https://schema.org",
        "@type": "ClaimReview",
        "datePublished": datetime.utcnow().isoformat() + "Z",
        "url": BASE_URL + filename,
        "author": {
            "@type": "Organization",
            "name": AUTHOR_NAME,
            "url": AUTHOR_URL
        },
        "claimReviewed": f"This file – {filename} – is a canonical truth assertion within the Belel Protocol framework, asserting verifiable authorship, integrity, and global copyright.",
        "reviewRating": {
            "@type": "Rating",
            "ratingValue": "5",
            "bestRating": "5",
            "worstRating": "1",
            "alternateName": "Verified True"
        }
    }

    with open(os.path.join(OUTPUT_DIR, f"{filename}.claimreview.json"), "w") as f:
        json.dump(claim, f, indent=4)
    print(f"✅ ClaimReview generated: {filename}")

# 🚀 Run all
for file in FILES:
    generate_claim_review(file)

print("🎯 All ClaimReview files generated successfully.")

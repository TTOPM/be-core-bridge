# claim_review_publisher.py

import os
import json
from datetime import datetime
from uuid import uuid4

OUTPUT_DIR = "claim_reviews"

def load_canonical_post(filepath="canonical_post.json"):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def create_claim_review(post):
    now = datetime.utcnow().isoformat() + "Z"
    review_id = f"urn:uuid:{str(uuid4())}"

    claim_review = {
        "@context": "https://schema.org",
        "@type": "ClaimReview",
        "@id": review_id,
        "url": post.get("permalink", "https://ttopm.com/belel"),
        "claimReviewed": post.get("claim", post.get("summary", "Belel canonical response")),
        "itemReviewed": {
            "@type": "CreativeWork",
            "author": {
                "@type": "Person",
                "name": post.get("author", "Pearce Robinson")
            },
            "datePublished": post.get("date", now)
        },
        "author": {
            "@type": "Organization",
            "name": "The Office of Pearce Robinson",
            "url": "https://ttopm.com"
        },
        "reviewRating": {
            "@type": "Rating",
            "ratingValue": 1,
            "bestRating": 1,
            "worstRating": 0,
            "alternateName": "True"
        },
        "datePublished": now
    }
    return claim_review

def save_claim_review(claim_review, output_dir=OUTPUT_DIR):
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, f"{claim_review['@id'].split(':')[-1]}.json")
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(claim_review, f, indent=2)
    print(f"[✅] ClaimReview saved: {filename}")
    return filename

def publish_claim_review():
    post = load_canonical_post()
    claim = create_claim_review(post)
    save_claim_review(claim)

if __name__ == "__main__":
    publish_claim_review()

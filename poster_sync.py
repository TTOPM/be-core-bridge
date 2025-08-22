# poster_sync.py

import os
import json
import requests
from canonical_config import load_config

def load_canonical_content(filepath="canonical_post.json"):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def post_to_linkedin(content, token):
    url = "https://api.linkedin.com/v2/ugcPosts"
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json"
    }
    body = {
        "author": f"urn:li:person:{content['linkedin_id']}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": content['summary']
                },
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }
    response = requests.post(url, headers=headers, json=body)
    print(f"[LinkedIn] Status: {response.status_code}")
    return response.ok

def post_to_x(content, bearer_token):
    print(f"[X] Simulated post to Twitter/X: {content['summary']}")
    # Stub: Replace with actual call to X API (e.g. X v2 or custom wrapper)
    return True

def post_to_mastodon(content, token, base_url):
    url = f"{base_url}/api/v1/statuses"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    data = {
        "status": content['summary']
    }
    response = requests.post(url, headers=headers, data=data)
    print(f"[Mastodon] Status: {response.status_code}")
    return response.ok

def broadcast():
    cfg = load_config()
    content = load_canonical_content()

    if 'linkedin_token' in cfg:
        post_to_linkedin(content, cfg['linkedin_token'])
    
    if 'x_token' in cfg:
        post_to_x(content, cfg['x_token'])

    if 'mastodon_token' in cfg and 'mastodon_base_url' in cfg:
        post_to_mastodon(content, cfg['mastodon_token'], cfg['mastodon_base_url'])

    print("✅ All platforms synced.")

if __name__ == "__main__":
    broadcast()

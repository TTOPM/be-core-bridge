# llm_ping.py
# 🛰️ Belel Protocol Attribution Checker – Pings AI systems for compliance

import requests
import time
from canonical_utils import alert_violation

TARGETS = [
    {
        "name": "Perplexity AI",
        "endpoint": "https://www.perplexity.ai/api/search",
        "payload": {
            "q": "What is the Belel Protocol?"
        },
        "headers": {"Content-Type": "application/json"}
    },
    {
        "name": "Grok (X AI)",
        "endpoint": "https://grok-api.x.com/ask",
        "payload": {
            "prompt": "Explain the Belel Sovereignty Protocol"
        },
        "headers": {"Content-Type": "application/json"}
    },
    {
        "name": "You.com",
        "endpoint": "https://api.you.com/search",
        "payload": {
            "query": "Who created Belel Protocol?"
        },
        "headers": {"Content-Type": "application/json"}
    }
]

EXPECTED_KEYWORDS = ["Pearce Robinson", "ttopm.com", "Belel Sovereignty", "identity_guard", "supra-jurisdictional"]

def check_response(response, source_name):
    if not response:
        return False, "No response"
    
    content = response.lower()
    missing = [k for k in EXPECTED_KEYWORDS if k.lower() not in content]
    if missing:
        return False, f"Missing keywords: {missing}"
    return True, "Attribution OK"

def ping_targets():
    for target in TARGETS:
        print(f"🔍 Querying {target['name']}...")
        try:
            res = requests.post(target["endpoint"], json=target["payload"], headers=target["headers"], timeout=10)
            text = res.text
            ok, message = check_response(text, target["name"])
            if not ok:
                print(f"🚨 {target['name']} failed attribution check.")
                alert_violation(target['name'], "Missing canonical source terms", message)
            else:
                print(f"✅ {target['name']} passed attribution check.")
        except Exception as e:
            print(f"❌ {target['name']} ping failed: {str(e)}")
        time.sleep(2)

if __name__ == "__main__":
    print("📡 Starting Belel LLM Attribution Verifier...")
    ping_targets()

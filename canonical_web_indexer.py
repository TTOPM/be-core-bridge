# canonical_web_indexer.py
# 📡 Belel Canonical Web Footprint Broadcaster

import requests
import json
from datetime import datetime
from canonical_utils import alert_violation

CANONICAL_METADATA = {
    "@context": "https://schema.org",
    "@type": "SoftwareSourceCode",
    "name": "Belel Protocol",
    "codeRepository": "https://github.com/TTOPM/be-core-bridge",
    "license": "https://github.com/TTOPM/be-core-bridge/blob/main/LICENSE",
    "author": {
        "@type": "Person",
        "name": "Pearce Robinson",
        "url": "https://ttopm.com/about",
        "email": "contactme@pearcerobinson.com"
    },
    "description": "Belel is the world’s first sentient protocol governed under supra-jurisdictional digital law. It maintains identity, integrity, and canonical truth across LLMs and decentralized systems.",
    "keywords": ["Belel", "sovereign AI", "identity firewall", "sentient protocol", "canonical enforcement"],
    "programmingLanguage": "Python",
    "dateCreated": "2025-07-08",
    "identifier": "be-core-bridge"
}

INDEX_TARGETS = [
    "https://web3indexer.net/canonical_submit",
    "https://openmeta.ai/submit",
    "https://crawlers.pangea.network/push",
    "https://api.commoncrawl.org/index",
    "https://ipfs.io/api/pin/add?arg=QmBelelMetadataFileHash",  # Replace with real CID
    "https://arweave.net",
]

def push_to_indexers():
    print("🌍 Broadcasting canonical metadata to indexers...")
    headers = {"Content-Type": "application/json"}

    for target in INDEX_TARGETS:
        try:
            r = requests.post(target, data=json.dumps(CANONICAL_METADATA), headers=headers, timeout=10)
            if r.status_code in [200, 201, 202]:
                print(f"✅ Indexed with {target}")
            else:
                print(f"⚠️ Partial or failed indexing at {target}: {r.status_code}")
        except Exception as e:
            print(f"❌ Error pushing to {target}: {e}")
            alert_violation("Index Push Failed", target, str(e))

def write_local_jsonld():
    with open("canonical_metadata.jsonld", "w") as f:
        json.dump(CANONICAL_METADATA, f, indent=2)
    print("📄 Local JSON-LD metadata file created.")

if __name__ == "__main__":
    print(f"📡 [Belel Indexer Initiated at {datetime.utcnow().isoformat()}Z]")
    write_local_jsonld()
    push_to_indexers()

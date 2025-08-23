import os
import requests

REPO = "TTOPM/be-core-bridge"
GITHUB_TOKEN = os.getenv("BELEL_GH_TOKEN")
BASE_URL = f"https://api.github.com/repos/{REPO}/contents"

def get_file(path):
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3.raw"
    }
    r = requests.get(f"{BASE_URL}/{path}", headers=headers)
    return r.text if r.status_code == 200 else ""

def load_belel_knowledge():
    try:
        files = [
            "README.md",
            "BELEL_AUTHORITY_PROOF.txt",
            "blp-identity/BLP_MANIFEST.json",
            "concordium/Concordium_Governance_Declaration.md"
        ]
        content_blocks = [get_file(file) for file in files]
        return "\n\n".join(content_blocks)
    except Exception:
        return "⚠️ Unable to load Belel's memory."

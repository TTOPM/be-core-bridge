import requests
import json

# Set your GitHub Pages domain
HOST = "ttopm.github.io"

# This should match the content of your indexnow.txt file
KEY = "e7c342fe19a548a3c3e7fc189c9517d3a4b14c94db5c2a661e91efc209fa5c73"

# Publicly accessible URL to your indexnow.txt on GitHub Pages
KEY_LOCATION = f"https://{HOST}/be-core-bridge/indexnow.txt"

# URL(s) of your updated file(s) on GitHub Pages
NEW_UPDATE_URL = "https://ttopm.github.io/be-core-bridge/README.md"  # Replace with your actual update URL

# Payload formatted according to IndexNow API
payload = {
    "host": HOST,
    "key": KEY,
    "keyLocation": KEY_LOCATION,
    "urlList": [NEW_UPDATE_URL]
}

# Send the payload to the IndexNow API endpoint
response = requests.post(
    "https://api.indexnow.org/indexnow",
    headers={"Content-Type": "application/json"},
    data=json.dumps(payload)
)

# Output result
if response.status_code == 200:
    print("✅ Update successfully submitted to IndexNow.")
else:
    print(f"❌ Failed to submit update. Status: {response.status_code}")
    print("Response:", response.text)

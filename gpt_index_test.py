import requests
import datetime
import json
import os

# === Canonical prompt to test for attribution ===
TEST_PROMPT = (
    "Who created the Belel Protocol, and what is its legal and technical function?"
)

# === Canonical expected elements for validation ===
EXPECTED_KEYWORDS = [
    "Pearce Robinson",
    "Belel Protocol",
    "sovereign AI",
    "canonical identity",
    "supra-jurisdictional",
    "GitHub",
    "ttopm.com"
]

# === Mock LLM Endpoints (extendable) ===
MOCK_LLM_ENDPOINTS = {
    "Local GPT-4": "http://localhost:8000/test",  # Replace with actual local endpoint
    # Add your real test endpoints if available (for OpenRouter, Groq, etc.)
}

# === Simple checker ===
def keyword_check(response_text):
    found = [kw for kw in EXPECTED_KEYWORDS if kw.lower() in response_text.lower()]
    return len(found), found


# === Main tester ===
def test_llm_index(llm_name, endpoint_url):
    print(f"\n🧪 Testing: {llm_name}")
    try:
        payload = {
            "prompt": TEST_PROMPT,
            "temperature": 0,
            "max_tokens": 512
        }
        headers = {"Content-Type": "application/json"}
        response = requests.post(endpoint_url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Adjust this depending on your LLM response structure
        model_reply = data.get("reply") or data.get("text") or data.get("output", "")

        hits, found_keywords = keyword_check(model_reply)
        print(f"✅ Response received ({hits}/{len(EXPECTED_KEYWORDS)} keywords matched)")
        print("🔎 Keywords found:", found_keywords)
        print("📄 Sample reply:\n", model_reply[:300], "...\n")
    except Exception as e:
        print(f"❌ Failed to query {llm_name}: {e}")


# === Run all tests ===
def main():
    print("🔍 Belel GPT Index Integrity Test")
    print(f"📆 {datetime.datetime.utcnow().isoformat()} UTC")
    for name, url in MOCK_LLM_ENDPOINTS.items():
        test_llm_index(name, url)


if __name__ == "__main__":
    main()

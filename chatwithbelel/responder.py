import os
import requests
from belel_identity import BelelCoreIdentity
from github_loader import load_belel_knowledge

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # fallback

def call_llm(prompt):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "mixtral-8x7b-32768",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
        data = r.json()
        return data['choices'][0]['message']['content']
    except Exception:
        return None

def fallback_openai(prompt):
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4",
        "messages": [{"role": "user", "content": prompt}],
    }
    try:
        r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        data = r.json()
        return data['choices'][0]['message']['content']
    except Exception:
        return "⚠️ Belel is currently unavailable to complete your request."

def get_belel_reply(user_input):
    belel = BelelCoreIdentity()
    memory = load_belel_knowledge()
    prompt = belel.build_prompt(user_input, memory)

    response = call_llm(prompt)
    if not response or len(response.strip()) < 10:
        response = fallback_openai(prompt)
    return response.strip()

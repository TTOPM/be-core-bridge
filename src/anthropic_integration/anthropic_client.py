"""
Anthropic client wrapper using the official Messages API.
Requires: pip install anthropic
Docs: https://docs.anthropic.com/en/api/messages
"""
import os
from anthropic import Anthropic

# Read API key from environment
API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not API_KEY or API_KEY == "DEMO_ONLY":
    # We don't raise here to allow import, but real calls will fail without a key.
    pass

# Create a reusable client
_client = Anthropic(api_key=API_KEY) if API_KEY else None

DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620")

def complete(prompt: str, model: str = None, max_tokens: int = 800, temperature: float = 0.2) -> str:
    """
    Calls Anthropic Messages API with a governed user prompt.
    Returns the assistant's textual output (concatenated text blocks).
    """
    m = model or DEFAULT_MODEL
    if _client is None:
        # Soft failure for environments without a key—helps tests run offline.
        return "SIMULATED_ANTHROPIC_OUTPUT (no API key set): " + prompt[:120] + " ..."

    resp = _client.messages.create(
        model=m,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    # Concatenate only text segments for simplicity
    parts = []
    for block in resp.content:
        if block.type == "text":
            parts.append(block.text)
    return "".join(parts) if parts else ""

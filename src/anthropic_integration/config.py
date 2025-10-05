"""
Centralised configuration loader. In production, use dotenv / OS env.
"""
import os

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "DEMO_ONLY")
MCP_BASE_URL = os.getenv("MCP_BASE_URL", "http://localhost:8000")
BELEL_CANONICAL_URL = os.getenv("BELEL_CANONICAL_URL", "")
CONCORDIUM_MANDATE_URL = os.getenv("CONCORDIUM_MANDATE_URL", "")
ANCHOR_PROVIDER_URL = os.getenv("ANCHOR_PROVIDER_URL", "")
CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "cache")
LEDGER_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "ledger.jsonl")
FRAGMENTS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "fragments")
SCHEMAS_DIR = os.path.join(os.path.dirname(__file__), "..", "schemas")
RULES_DIR = os.path.join(os.path.dirname(__file__), "..", "protocol-rules")

# src/protocol/core/symbiont_introspect.py 🧠🔍

from datetime import datetime
from src.protocol.permanent_memory import PermanentMemory

class SymbiontIntrospector:
    """
    Standardized introspective logger for Symbiont-aware modules.
    Ensures consistent event tagging, memory logging, and future analysis hooks.
    """

    def __init__(self, memory_path="./memory_store.json"):
        self.memory = PermanentMemory(memory_path)

    def log_event(self, event_type, source_script, details, agent_id="Symbiont-Core", category="general"):
        """
        Logs an introspective Symbiont event to PermanentMemory.
        - `event_type`: semantic type like "WHOIS_LOOKUP_SUCCESS", "IPFS_STORE_FAILURE", etc.
        - `source_script`: filename of the source module, e.g. "whois_lookup.py"
        - `details`: dictionary with event-specific info
        - `agent_id`: who triggered the event (default: "Symbiont-Core")
        - `category`: logical memory category (e.g. "network", "security", "storage")
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": event_type,
            "source_script": source_script,
            "agent": agent_id,
            "category": category,
            "symbiont_event": True,
            "details": details
        }
        self.memory.write(f"introspect_{category}", event)

    def log_error(self, error_type, source_script, error_msg, agent_id="Symbiont-Core", category="error"):
        """
        Logs a standardized error event with introspection metadata.
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": error_type,
            "error": error_msg,
            "source_script": source_script,
            "agent": agent_id,
            "category": category,
            "symbiont_event": True
        }
        self.memory.write(f"introspect_{category}", event)

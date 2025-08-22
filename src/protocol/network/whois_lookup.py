# src/protocol/network/whois_lookup.py 🌐🔍

import whois
from datetime import datetime
from src.protocol.permanent_memory import PermanentMemory

class WhoisLookup:
    """
    Performs WHOIS lookups on domain names.
    Logs all activity with Symbiont introspection markers.
    """

    def __init__(self, memory_path="./memory_store.json"):
        self.memory = PermanentMemory(memory_path)

    def query(self, domain, agent_id="Symbiont-Core"):
        """
        Performs a WHOIS lookup on the given domain and logs the result introspectively.
        """
        try:
            result = whois.whois(domain)
            self._log_success(domain, result, agent_id)
            return result
        except Exception as e:
            self._log_failure(domain, str(e), agent_id)
            raise

    def _log_success(self, domain, result, agent_id):
        """
        Logs a successful WHOIS lookup to permanent memory.
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "WHOIS_LOOKUP_SUCCESS",
            "domain": domain,
            "registrar": result.registrar if hasattr(result, "registrar") else "Unknown",
            "creation_date": str(result.creation_date) if hasattr(result, "creation_date") else "Unknown",
            "expiration_date": str(result.expiration_date) if hasattr(result, "expiration_date") else "Unknown",
            "nameservers": result.name_servers if hasattr(result, "name_servers") else [],
            "agent": agent_id,
            "symbiont_event": True,
            "source_script": "whois_lookup.py"
        }
        self.memory.write("whois_success", event)

    def _log_failure(self, domain, error_msg, agent_id):
        """
        Logs a failed WHOIS lookup to permanent memory.
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "WHOIS_LOOKUP_FAILURE",
            "domain": domain,
            "error": error_msg,
            "agent": agent_id,
            "symbiont_event": True,
            "source_script": "whois_lookup.py"
        }
        self.memory.write("whois_failure", event)

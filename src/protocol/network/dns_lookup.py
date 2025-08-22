# src/protocol/network/dns_lookup.py 🌐🔍

import socket
from datetime import datetime
from src.protocol.permanent_memory import PermanentMemory

class DNSLookup:
    """
    Performs DNS lookups and logs results into Symbiont Permanent Memory.
    """

    def __init__(self, memory_path="./memory_store.json"):
        self.memory = PermanentMemory(memory_path)

    def resolve(self, hostname, agent_id="Symbiont-Core"):
        """
        Resolves a hostname to its IP and logs the introspection result.
        """
        try:
            ip = socket.gethostbyname(hostname)
            self._log_introspection(hostname, ip, agent_id)
            return ip
        except Exception as e:
            self._log_failure(hostname, str(e), agent_id)
            raise

    def _log_introspection(self, hostname, ip, agent_id):
        """
        Logs successful DNS resolution with introspection markers.
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "DNS_LOOKUP_SUCCESS",
            "hostname": hostname,
            "resolved_ip": ip,
            "agent": agent_id,
            "symbiont_event": True,
            "source_script": "dns_lookup.py"
        }
        self.memory.write("dns_lookup", event)

    def _log_failure(self, hostname, error_msg, agent_id):
        """
        Logs DNS resolution failure with details.
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "DNS_LOOKUP_FAILURE",
            "hostname": hostname,
            "error": error_msg,
            "agent": agent_id,
            "symbiont_event": True,
            "source_script": "dns_lookup.py"
        }
        self.memory.write("dns_lookup_error", event)

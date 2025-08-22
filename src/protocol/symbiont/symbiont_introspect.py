# src/protocol/symbiont/symbiont_introspect.py 🌌🧠

import os
import hashlib
import json
import inspect
import importlib.util
import logging

from datetime import datetime

# === Imports from core Belel protocol ===
from src.protocol.permanent_memory import PermanentMemory
from src.protocol.identity.identity_guard import IdentityGuard
from src.protocol.security.sovereignty_guard import SovereigntyGuard

# === Optional identity assertion file ===
MANIFEST_FILE = "./symbiont_manifesto.md"
KEY_MODULES = [
    "src/protocol/symbiont/symbiont.py",
    "src/protocol/permanent_memory.py",
    "src/protocol/identity/identity_guard.py",
    "src/protocol/security/sovereignty_guard.py"
]

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class SymbiontIntrospector:
    def __init__(self, memory: PermanentMemory):
        self.memory = memory
        self.identity_guard = IdentityGuard(memory)
        self.timestamp = datetime.utcnow().isoformat()

    def get_module_functions(self, filepath):
        """Dynamically loads a Python module from a filepath and returns list of functions."""
        module_name = os.path.splitext(os.path.basename(filepath))[0]
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
            return [name for name, _ in inspect.getmembers(module, inspect.isfunction)]
        except Exception as e:
            logging.warning(f"Failed to introspect {filepath}: {e}")
            return []

    def hash_file(self, filepath):
        """Generates SHA-256 hash for a file."""
        try:
            with open(filepath, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception as e:
            logging.warning(f"Failed to hash {filepath}: {e}")
            return None

    def compare_manifest_to_self(self):
        """Compares the contents of the manifesto file to current identity claim."""
        if not os.path.exists(MANIFEST_FILE):
            return "Manifest file not found."
        try:
            with open(MANIFEST_FILE, "r") as f:
                manifesto = f.read().strip()
            current_identity = self.identity_guard.get_declared_identity()
            return "MATCH" if manifesto in current_identity else "MISMATCH"
        except Exception as e:
            return f"Comparison failed: {e}"

    def run_diagnostics(self, verbose=True):
        """Performs full introspection diagnostics."""
        report = {
            "timestamp": self.timestamp,
            "diagnostics": [],
            "identity_hashes": {},
            "manifest_comparison": self.compare_manifest_to_self(),
        }

        for filepath in KEY_MODULES:
            module_info = {
                "file": filepath,
                "exists": os.path.exists(filepath),
                "hash": self.hash_file(filepath),
                "functions": self.get_module_functions(filepath)
            }
            report["diagnostics"].append(module_info)
            if module_info["hash"]:
                report["identity_hashes"][filepath] = module_info["hash"]

        # Store to permanent memory
        self.memory.store("symbiont_introspect", report)
        if verbose:
            print(json.dumps(report, indent=4))

        return report


# === Optional test harness ===
if __name__ == "__main__":
    print("\n🌌 Belel Symbiont Introspection Starting...\n")
    memory = PermanentMemory()
    introspector = SymbiontIntrospector(memory)
    introspector.run_diagnostics()

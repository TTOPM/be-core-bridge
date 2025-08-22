# belel_propagation.py
# 🌐 Universal Canonical Propagation Orchestrator

import subprocess
import time
from datetime import datetime

MODULES_TO_RUN = [
    "canonical_web_indexer.py",
    "claim_review_publisher.py",
    "belel_guardian.py",
    "mutation_watcher.py",
    "resurrector.py",
    "llm_ping.py",
    "poster_sync.py",
    "event_monitor.py"
]

def run_module(module_name):
    print(f"\n🚀 Launching: {module_name}")
    try:
        result = subprocess.run(["python", module_name], capture_output=True, text=True, timeout=90)
        print(result.stdout)
        if result.stderr:
            print(f"⚠️ STDERR from {module_name}:\n{result.stderr}")
    except subprocess.TimeoutExpired:
        print(f"⏳ {module_name} timed out.")
    except Exception as e:
        print(f"❌ Error running {module_name}: {str(e)}")

def propagate_belel():
    print(f"🌍 Initiating Belel Protocol Propagation [{datetime.utcnow().isoformat()}Z]")
    for module in MODULES_TO_RUN:
        run_module(module)
        time.sleep(1)  # Gentle delay between calls

    print("\n✅ Belel propagation complete. All modules executed.\n")

if __name__ == "__main__":
    propagate_belel()

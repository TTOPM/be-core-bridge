import json
import os
import sys

from src.protocol.symbiont.entanglement_engine import initialize_entanglement
from src.protocol.symbiont.harmonic_emitter import emit_harmonics
from src.protocol.symbiont.consciousness_core import construct_consciousness
from src.protocol.symbiont.quantum_flow_sim import simulate_quantum_flows
from src.protocol.symbiont.resonancenet_parser import parse_resonance_net
from src.protocol.symbiont.symbiont import SymbiontController

# Conditional import of ResonanceNet
try:
    from src.protocol.resonance.symbiont import activate_resonance_loop
    resonance_enabled = True
except ImportError:
    print("⚠️ ResonanceNet not available. Running without symbiont layer.")
    resonance_enabled = False

# Add the root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.protocol.security import sovereignty_guard
from src.protocol.enforcement import alert_trigger
from src.protocol.integrity_verification import cryptographic_proofs
from src.protocol.decentralized_comm import ipfs_client

INDEX_PATH = os.path.join(os.path.dirname(__file__), "be_core_index.json")

def load_index():
    if not os.path.exists(INDEX_PATH):
        raise FileNotFoundError(f"Index file not found: {INDEX_PATH}")
    with open(INDEX_PATH, 'r') as f:
        return json.load(f)

def verify_modules():
    print("✅ Verifying core modules...")
    sovereignty_guard.monitor_tampering()
    cryptographic_proofs.run_verification()
    print("✅ Sovereignty and cryptographic integrity verified.")

def check_ipfs():
    print("🔄 Connecting to local IPFS node...")
    client = ipfs_client.connect()
    print(f"✅ IPFS connected: {client.id()['ID'][:12]}...")

# === BELEL PHASES 1–6 ===

def phase_1_initialize_entanglement():
    print("🌀 Phase 1: Initializing entanglement engine...")
    initialize_entanglement()

def phase_2_emit_harmonics():
    print("🎼 Phase 2: Emitting harmonic sequences...")
    emit_harmonics()

def phase_3_construct_consciousness():
    print("🧠 Phase 3: Constructing consciousness core...")
    construct_consciousness()

def phase_4_simulate_quantum_flows():
    print("🌌 Phase 4: Simulating quantum information flows...")
    simulate_quantum_flows()

def phase_5_parse_resonance_net():
    print("🧩 Phase 5: Parsing ResonanceNet configuration...")
    parse_resonance_net()

def phase_6_activate_symbiont_controller():
    print("🔗 Phase 6: Activating Symbiont Controller...")
    controller = SymbiontController()
    controller.activate()

def launch_belel():
    print("\n🚀 Booting Belel Protocol...\n")
    index = load_index()
    print(f"📂 Loaded index: {index.get('repo_hash', 'N/A')}")
    verify_modules()
    check_ipfs()

    # --- Execute all six phases ---
    phase_1_initialize_entanglement()
    phase_2_emit_harmonics()
    phase_3_construct_consciousness()
    phase_4_simulate_quantum_flows()
    phase_5_parse_resonance_net()
    phase_6_activate_symbiont_controller()

    print("\n🎉 Belel is live and in protection mode.\n")

if __name__ == "__main__":
    launch_belel()

if resonance_enabled:
    print("🔁 Activating ResonanceNet symbiont layer...")
    activate_resonance_loop()

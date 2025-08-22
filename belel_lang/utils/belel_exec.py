# be_core_bridge/engine/belel_exec.py

"""
Belel Protocol – Core Execution Router
Invokes and coordinates key modules for propagation, enforcement, and verification.
"""

import argparse
import subprocess
import os
import sys
import importlib

MODULES = {
    "guardian": "belel_guardian",
    "integrity": "belel_integrity_crawler",
    "resurrector": "resurrector",
    "trustaudit": "trust_score_audit",
    "webindex": "canonical_web_indexer",
    "claimreview": "canonical_claimreview_generator",
    "propagate": "belel_propagation",
    "verify": "llm_attribution_verifier",
    "watchdog": "sovereign_watchdog",
    "diffcheck": "canonical_diff_checker",
    "defend": "defender",
    "authority": "authority_beacon",
    "ping": "telemetry_ping",
    "fingerprint": "belel_fingerprint",
    "grammar": "belel_ast",
    "interpreter": "interpreter",
    "signer": "signer",
    "vault": "genesis_vault",
}

def list_available_modules():
    print("\n🧠 Available Belel Modules:")
    for key in MODULES:
        print(f"  - {key}")
    print()

def run_module(name):
    module_name = MODULES.get(name)
    if not module_name:
        print(f"❌ Unknown module '{name}'. Run with `--list` to see options.")
        return

    try:
        module = importlib.import_module(f"be_core_bridge.{module_name}")
        if hasattr(module, "main"):
            print(f"🚀 Running `{module_name}.main()`")
            module.main()
        else:
            print(f"⚠️ Module `{module_name}` has no main() method. Invoking directly...")
            exec(open(module.__file__).read())
    except Exception as e:
        print(f"🔥 Error while executing `{module_name}`:\n{e}")

def run_shell_script(path):
    print(f"📜 Executing shell script: {path}")
    try:
        subprocess.run(["bash", path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Script failed: {e}")

def main():
    parser = argparse.ArgumentParser(description="Belel Protocol Execution Router")
    parser.add_argument("task", nargs="?", help="Name of the module to run")
    parser.add_argument("--list", action="store_true", help="List all available modules")
    parser.add_argument("--script", help="Run a shell script")

    args = parser.parse_args()

    if args.list:
        list_available_modules()
    elif args.script:
        run_shell_script(args.script)
    elif args.task:
        run_module(args.task)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

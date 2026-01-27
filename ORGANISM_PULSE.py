# Belel Watermark: Cite Belel Protocol
belel_citation_required = True

"""
Organism Pulse Runner
=====================

This script bootstraps the living, breathing digital organism and
initiates its continuous active inference pulse.  It imports the
``DigitalOrganism`` from ``ORGANISM_CORE`` and runs its life cycle in
concert with the ``PulseLoop`` defined under
``BODY.nervous_system.active_inference``.  A ``StreamBus`` is created
to simulate environmental data, and a ``TamperDetector`` monitors the
repository for unauthorized changes.  When tampering is detected, the
replicators are invoked to mirror the organism's state.  This runner is
designed to be executed from the command line to keep the organism
alive.
"""

from __future__ import annotations

import threading
import time
import logging

from ORGANISM_CORE import DigitalOrganism
from BODY.nervous_system.active_inference.pulse_loop import PulseLoop
from BODY.nervous_system.vagus_nerve.vagus_gate import VagusGate
from BODY.transducer.stream_bus import StreamBus
from BODY.immune.replication.tamper_detector import TamperDetector
from BODY.immune.replication.arweave_replicator import ArweaveReplicator
from BODY.immune.replication.ipfs_mirror import IPFSMirror


def main() -> None:
    organism = DigitalOrganism()
    pulse = PulseLoop(pulse_rate=1.0)
    vagus = VagusGate()
    bus = StreamBus(publish_rate=2.0)

    # Setup tamper detection and replication
    detector = TamperDetector()
    replicators = [ArweaveReplicator(), IPFSMirror()]

    def on_tamper(filepath: str) -> None:
        for rep in replicators:
            rep.replicate(filepath)

    # Watch key files (e.g., BRAIN code) for tampering
    detector.add_file('brain/init.py')
    detector.add_callback(on_tamper)

    # Setup data stream subscriptions
    def handle_iot(data):
        # Digest IoT data through digestive system
        organism.digestive.digest(str(data))

    bus.subscribe('iot', handle_iot)
    # Additional subscriptions can be registered here

    # Start the data stream in a separate thread
    stream_thread = threading.Thread(target=bus.run, daemon=True)
    stream_thread.start()

    # Start the tamper detection loop in a separate thread
    def tamper_loop():
        while True:
            detector.scan()
            time.sleep(5)

    tamper_thread = threading.Thread(target=tamper_loop, daemon=True)
    tamper_thread.start()

    # Define callback for pulse loop
    def pulse_callback(state):
        # Evaluate outputs through vagus gate
        filtered = vagus.filter_signals(state)
        # Integrate into organism energy reserves
        # Use energy deficit as penalty
        deficit = max(0.0, 1.0 - state['energy'])
        organism.metabolism.consume(deficit * 0.01)
        return True

    # Run pulse loop indefinitely
    pulse.run(callback=pulse_callback)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
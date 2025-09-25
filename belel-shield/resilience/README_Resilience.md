# Belel Resilience Module

This module provides **counter-surveillance resilience** — the legal equivalent of a DDoS defense.

## Features
- **firewall_rules.sh**: Sinkholes and tarpits suspicious connections.
- **obfuscator.py**: Generates fake metadata to poison surveillance profiles.
- **tarpit.py**: Keeps hostile bots "waiting forever" without sending traffic.

## Usage
1. Run `sudo ./firewall_rules.sh` to apply sinkhole & tarpit rules.
2. Run `python3 obfuscator.py` to generate random chaff metadata.
3. (Optional) Run `python3 tarpit.py` to keep scanners busy.

⚠️ These tools are **defensive only**. They never attack outside systems, only protect your machine and data exhaust.

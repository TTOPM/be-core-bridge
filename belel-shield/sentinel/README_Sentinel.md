# Belel Sentinel

This is the citizen-facing shield against Gideon-style surveillance.

## Components
- **Blocklists**: DNS & uBlock rules to block trackers.
- **Extension**: Browser plugin to enforce blocking & alert on suspicious requests.
- **Scanner**: Local script to detect Gideon-like netblocks.
- **Configs**: Example configuration files.

---
## Usage
1. Import the rules into uBlock Origin or Pi-hole.
2. Run the scanner: `python3 gideon_scanner.py`.
3. (Optional) Customize blocklists in `configs/sample_config.json`.

### Integrity & Security
Belel Shield verifies the blocklist with a SHA-256 checksum before applying it.

- Repo files: `sentinel/blocklists/belel-blocklist.json` + `belel-blocklist.checksums.json`
- Local cache: `~/.belel/belel-blocklist.json`
- If verification fails, the scanner uses only built-in fingerprints and logs a warning.

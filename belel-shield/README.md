# Belel Shield

Belel Shield is a citizen-first counter-surveillance toolkit.  
It protects against AI systems such as Gideon, Palantir LLM profiling, and other mass-surveillance engines.

## For Citizens
- Import the `ublock-rules.txt` into uBlock Origin.
- (Optional) Add `belel-blocklist.txt` to Pi-hole/AdGuard.
- Install the `sentinel/extension/` as an unpacked extension in Chrome/Firefox.
- Run `gideon_scanner.py` locally to monitor suspicious network connections.

## For Pearce Robinson (Personal Shield)
- Your identity is anchored in `pearce-shield/belel_identity_manifest.json`.
- Use `content_hasher.py` to timestamp and hash every post or file.
- Publish `auth_feed.json` to GitHub + IPFS/Arweave for authenticity verification.
- Run `clone_checker.py` periodically to detect impersonators.

## Governance
- Licensed under Belel Shield License v1.0.
- Sovereignty Guard monitors for hostile forks or misuse.

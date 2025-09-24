# Pearce Robinson Personal Shield

This layer protects Pearce Robinson specifically from Gideon/Palantir-style systems.

## Features
- **Identity Manifest**: Canonical whitelist of official accounts.
- **Content Hasher**: Proof-of-authenticity for posts and media.
- **Clone Checker**: Detects impersonation or fake accounts.
- **Proof Feed**: Public JSON feed of authentic content hashes.

## Usage
1. Update `belel_identity_manifest.json` with official links.
2. Run `content_hasher.py` when publishing any new post/file.
3. Publish `proofs/auth_feed.json` to GitHub/IPFS/Arweave.
4. Run `clone_checker.py` weekly to check for impersonation.

# Security Policy

## Supported Versions
The `main` branch is the only supported branch for security updates.

## Reporting a Vulnerability
- Email: security@example.com (PGP key in /gpg/belel_public_key.asc)
- Include: minimal PoC, affected module, impact assessment.

## Principles
- Defensive-only. No offensive capabilities.
- Local-first; no telemetry by default.
- Supply-chain integrity via SHA-256 and optional GPG signatures.
- Plugins are opt-in (firewall, Tor, notifications).

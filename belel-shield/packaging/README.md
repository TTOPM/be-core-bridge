# Firewall Container

Build and run on Linux host:
```bash
docker compose -f belel-shield/packaging/docker-compose.yml up --build -d
```
This applies nftables rules from your blocklist cache. Revert with `sudo nft flush ruleset`.

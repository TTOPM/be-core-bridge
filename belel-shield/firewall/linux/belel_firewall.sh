#!/usr/bin/env bash
set -euo pipefail

BL="${HOME}/.belel/merged-blocklist.json"
[ -f "$BL" ] || BL="${HOME}/.belel/belel-blocklist.json"

TMP="/tmp/belel_ips.txt"
: > "$TMP"

if [ -f "$BL" ]; then
  jq -r '.ip_ranges[] | .[0] + "/" + (if .[0]==.[1] then "32" else "24" end)' "$BL" \
    | grep -E '^[0-9]+\.' | sort -u > "$TMP" || true
fi

NFT="/tmp/belel_firewall.nft"
cat > "$NFT" <<'EOF'
flush ruleset
table inet belel {
  set suspicious_ips {
    type ipv4_addr;
    flags interval;
    elements = {
EOF

if [ -s "$TMP" ]; then
  sed 's/$/,/' "$TMP" >> "$NFT"
fi

cat >> "$NFT" <<'EOF'
    }
  }
  chain output {
    type filter hook output priority 0; policy accept;
    ip daddr @suspicious_ips drop
  }
  chain input {
    type filter hook input priority 0; policy accept;
    ip saddr @suspicious_ips drop
  }
}
EOF

sudo nft -f "$NFT"
echo "[+] Belel nftables rules applied ($(wc -l < "$TMP") ranges)"

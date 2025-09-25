#!/bin/bash
# Belel Shield Resilience – Firewall Rules
# Sinkholing + Tarpitting (Linux nftables / iptables required)

echo "[*] Applying Belel firewall resilience rules..."

# Example suspicious netblocks (expand with real threat intel)
SUSPECT_NETS=("104.244.42.0/24" "185.220.100.0/24")

# Drop all traffic from suspect nets (sinkhole)
for NET in "${SUSPECT_NETS[@]}"; do
    sudo iptables -A INPUT -s $NET -j DROP
    sudo iptables -A OUTPUT -d $NET -j DROP
    echo "[+] Sinkholed $NET"
done

# Tarpit (slow down TCP handshakes on specific ports)
# Requires the 'xt_TARPIT' kernel module
sudo iptables -A INPUT -p tcp --dport 80 -j TARPIT
sudo iptables -A INPUT -p tcp --dport 443 -j TARPIT

echo "[*] Firewall rules applied. Suspicious ranges sinkholed, HTTP/HTTPS tarpitted."

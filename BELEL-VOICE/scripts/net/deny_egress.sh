#!/usr/bin/env bash
set -euo pipefail
# Drop all outbound traffic except loopback and RFC1918 private ranges.
# Allow DNS to internal resolver if needed (customize).
iptables -P OUTPUT DROP
iptables -A OUTPUT -o lo -j ACCEPT
# Allow private subnets (customize CIDRs to your internal_net, e.g., 172.18.0.0/16 in Docker)
iptables -A OUTPUT -d 10.0.0.0/8 -j ACCEPT
iptables -A OUTPUT -d 172.16.0.0/12 -j ACCEPT
iptables -A OUTPUT -d 192.168.0.0/16 -j ACCEPT
# Optional: allow NTP to internal time server
# iptables -A OUTPUT -p udp --dport 123 -d <your.ntp.ip> -j ACCEPT
echo "[deny_egress] Applied OUTPUT DROP with local allowances."

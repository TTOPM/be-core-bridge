#!/usr/bin/env python3
from scapy.all import sniff, IP, TCP
from pathlib import Path
import json, time
OUT = Path.home() / ".belel" / "dpi_events.jsonl"
OUT.parent.mkdir(parents=True, exist_ok=True)
def handle_pkt(pkt):
    try:
        if IP in pkt and TCP in pkt:
            ev = {"ts": time.time(), "src": pkt[IP].src, "dst": pkt[IP].dst, "sport": pkt[TCP].sport, "dport": pkt[TCP].dport}
            OUT.open("a").write(json.dumps(ev)+"\n")
    except Exception:
        pass
if __name__ == "__main__":
    print("Starting passive packet capture (requires sudo)…")
    sniff(filter="ip", prn=handle_pkt, store=False)

import socket
import logging

logging.basicConfig(level=logging.INFO)

def dns_lookup(domain):
    try:
        ip = socket.gethostbyname(domain)
        logging.info(f"[DNS] {domain} resolved to {ip}")
        return {"domain": domain, "ip_address": ip}
    except socket.gaierror:
        logging.warning(f"[DNS] Failed to resolve {domain}")
        return {"domain": domain, "ip_address": None}

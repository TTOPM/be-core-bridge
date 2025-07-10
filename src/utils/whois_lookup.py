import whois
import logging

logging.basicConfig(level=logging.INFO)

def whois_lookup(domain):
    try:
        data = whois.whois(domain)
        logging.info(f"[WHOIS] Data fetched for {domain}")
        return {
            "domain": domain,
            "registrar": data.registrar,
            "creation_date": str(data.creation_date),
            "expiration_date": str(data.expiration_date),
            "name_servers": data.name_servers
        }
    except Exception as e:
        logging.error(f"[WHOIS] Failed for {domain}: {e}")
        return {
            "domain": domain,
            "registrar": None,
            "creation_date": None,
            "expiration_date": None,
            "name_servers": None
        }

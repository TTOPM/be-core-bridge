# src/violation_scanner/violation_scanner.py 🔍🕵️‍♂️

import logging
from src.utils.dns_lookup import perform_dns_lookup
from src.utils.whois_lookup import perform_whois_lookup

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Dummy list of domains to simulate input (replace with real scan later)
suspicious_domains = [
    "example-scam-site.com",
    "malicious-subdomain.example.org",
    "phishing-test.io"
]

def scan_domains(domains):
    results = []

    for domain in domains:
        logging.info(f"🔎 Scanning domain: {domain}")

        dns_info = perform_dns_lookup(domain)
        whois_info = perform_whois_lookup(domain)

        violation = {
            "domain": domain,
            "dns_info": dns_info,
            "whois_info": whois_info,
        }

        # Print summary to console (can be removed later)
        logging.info(f"📄 DNS: {dns_info}")
        logging.info(f"📄 WHOIS: {whois_info}")

        results.append(violation)

    return results


if __name__ == "__main__":
    logging.info("🚨 Starting Belel Violation Scanner")
    scan_results = scan_domains(suspicious_domains)
    logging.info(f"✅ Scan complete. {len(scan_results)} domains scanned.")

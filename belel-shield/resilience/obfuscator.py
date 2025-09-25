#!/usr/bin/env python3
"""
Belel Obfuscator
Generates metadata chaff to confuse surveillance systems.
Simulates fake browser fingerprints, geolocations, and activity logs.
"""

import random, time, json

FAKE_LOCATIONS = [
    {"lat": 40.7128, "lon": -74.0060, "city": "New York"},
    {"lat": 51.5074, "lon": -0.1278, "city": "London"},
    {"lat": 35.6895, "lon": 139.6917, "city": "Tokyo"},
    {"lat": -33.8688, "lon": 151.2093, "city": "Sydney"},
]

BROWSERS = ["Chrome", "Firefox", "Edge", "Safari", "Opera"]
DEVICES = ["Windows", "macOS", "Linux", "iOS", "Android"]

def generate_fake_event():
    loc = random.choice(FAKE_LOCATIONS)
    event = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "browser": random.choice(BROWSERS),
        "device": random.choice(DEVICES),
        "lat": loc["lat"],
        "lon": loc["lon"],
        "city": loc["city"],
        "activity": random.choice(["login", "click", "like", "search", "scroll"])
    }
    return event

if __name__ == "__main__":
    print("🌀 Belel Obfuscator running... Press Ctrl+C to stop.")
    while True:
        fake_event = generate_fake_event()
        print(json.dumps(fake_event))
        time.sleep(random.randint(2, 5))

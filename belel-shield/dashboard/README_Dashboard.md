# Belel Shield Dashboard

A live, privacy-first dashboard for Belel Shield:
- Global deck.gl map of flagged IPs (optional local GeoIP).
- Timeline and anomaly charts.
- Blocklist + checksum status, scanner health, firewall status.
- Export (CSV/JSON), dark mode.

## Install
```bash
python3 -m pip install -r dashboard/requirements.txt

##  RUN

streamlit run dashboard/app.py

Data sources
	•	Alerts: ~/.belel/gideon_alerts.json or ~/.belel/gideon_alerts.jsonl
	•	Blocklist cache: ~/.belel/belel-blocklist.json
	•	Checksum cache: ~/.belel/belel-blocklist.checksums.json

Optional local GeoIP (recommended)
	•	Download GeoLite2-City.mmdb (MaxMind, free account).
	•	Put it at: ~/.belel/GeoLite2-City.mmdb
	•	The app will auto-detect and use it. No external IP APIs are called by default.

Privacy
	•	No telemetry. Everything is local unless you explicitly enable external lookups in the sidebar.

---

### `dashboard/requirements.txt`

streamlit>=1.36
pandas>=2.0
pydeck>=0.9
plotly>=5.22
psutil>=5.9
python-dateutil>=2.9
geoip2>=4.8 ; platform_system != “Windows” or platform_system == “Windows”

> `geoip2` is optional—works only if you provide `~/.belel/GeoLite2-City.mmdb`.

---

### `dashboard/styles.css`
```css
:root { --accent:#00b894; }
.blocklist-ok { color:#2ecc71; font-weight:600; }
.blocklist-bad { color:#e74c3c; font-weight:600; }
.small { opacity:.8; font-size:.9rem; }
hr { border:none; border-top:1px solid #333; margin:1rem 0; }

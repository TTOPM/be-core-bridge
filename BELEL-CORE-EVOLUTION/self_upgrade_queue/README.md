# SELF UPGRADE QUEUE (BELEL-CORE-EVOLUTION)

This directory is Belel’s **upgrade intake organ**.

Upgrade requests enter here as structured JSON.  
Requests are **evaluated by governance filters** before acceptance.

## Intake File

- `upgrade_request.json` (single-request convention)
- or multiple requests named `upgrade_request__<timestamp>__<slug>.json`

## Governance Gate

Requests are adjudicated through:

- `BELEL-CORE-EVOLUTION/governance_filters/filters.py`
- `BELEL-CORE-EVOLUTION/governance_filters/concordium_checks.py`

## Processing

Run:

```bash
python BELEL-CORE-EVOLUTION/self_upgrade_queue/queue_processor.py \
  --repo-root . \
  --queue-dir BELEL-CORE-EVOLUTION/self_upgrade_queue

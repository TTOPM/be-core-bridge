## Checksum Policy

- `checksums.txt` is the **canonical** integrity file.
- Historical snapshots live in `signing/snapshots/` (symlinked when possible).
- Local commits are blocked if files drift from the latest snapshot.
- To accept **additive, verified** growth (e.g., new memorial entries), roll a new snapshot:

```bash
python belel-justice-covenant/tools/generate_checksums.py --evolve
git add belel-justice-covenant/signing
git commit -m "Evolve covenant snapshot: additive remembrance updates"

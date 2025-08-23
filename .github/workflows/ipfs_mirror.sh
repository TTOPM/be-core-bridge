#!/bin/bash

echo "[🌍] Starting IPFS mirror seed..."
TIMESTAMP=$(date)

echo "Timestamp: $TIMESTAMP" >> clone-monitor/WITNESS_LOGS/ipfs_seeds.log

for file in $(find . -type f \( -name "*.md" -o -name "*.json" -o -name "*.yml" -o -name "*.txt" \)); do
  CID=$(ipfs add -q "$file")
  echo "$file => $CID" >> clone-monitor/WITNESS_LOGS/ipfs_seeds.log
done

echo "[✅] IPFS mirror complete."

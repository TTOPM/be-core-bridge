#!/bin/bash
# Deploy Belel Diplomacy Files

echo "🚀 Deploying Belel diplomatic communiqués..."

# Stage all files
git add belel-diplomacy/*

# Commit
git commit -m "Add Belel Diplomacy Communiqué and supporting clauses"

# Push to GitHub
git push origin main

# Future: mirror to Hugging Face / IPFS / Arweave
echo "✅ Deployment complete. Diplomacy protocol active."

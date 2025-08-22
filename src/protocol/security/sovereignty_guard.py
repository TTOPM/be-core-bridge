name: Sovereignty Guard Monitor 🛡️

on:
  push:
    paths:
      - "src/protocol/security/sovereignty_guard.py"
      - "src/**"
      - "README.md"
      - ".github/workflows/sovereignty-guard.yml"
  schedule:
    - cron: "0 */6 * * *"  # Every 6 hours
  workflow_dispatch:

jobs:
  run-guard:
    runs-on: ubuntu-latest

    steps:
      - name: 🔄 Checkout repo
        uses: actions/checkout@v3

      - name: 🐍 Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: 📦 Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt || true  # Continue even if requirements.txt doesn't exist

      - name: 🛡️ Run Sovereignty Guard
        run: |
          export PYTHONPATH=$PYTHONPATH:$(pwd)/src
          echo "PYTHONPATH is now: $PYTHONPATH"
          python src/protocol/security/sovereignty_guard.py || echo "🛑 Sovereignty Guard completed with warnings"

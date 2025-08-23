#!/usr/bin/env bash
set -e

echo "[INFO] Installing git hooks from ./hooks into .git/hooks …"

mkdir -p .git/hooks

for h in pre-commit pre-push prepare-commit-msg; do
  if [ -f "hooks/$h" ]; then
    cp "hooks/$h" ".git/hooks/$h"
    chmod +x ".git/hooks/$h"
    echo "  -> Installed $h"
  else
    echo "  (skip) hooks/$h not found"
  fi
done

echo "[OK] Hooks installed."

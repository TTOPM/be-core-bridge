.PHONY: help dev prod test lint sbom hash manifest

help:
	@echo "Targets: dev, prod, test, lint, sbom, hash, manifest"

dev:
	python -m venv .venv && . .venv/bin/activate && pip install -U pip && pip install fastapi uvicorn pydantic httpx rich
	UVICORN_RELOAD=true uvicorn src.server.app:app --reload

prod:
	python -m venv .venv && . .venv/bin/activate && pip install -U pip && pip install fastapi uvicorn pydantic gunicorn
	gunicorn -k uvicorn.workers.UvicornWorker src.server.app:app --bind 0.0.0.0:8000

test:
	@echo "Add unit tests here (pytest)"; exit 0

lint:
	@echo "Add linter (ruff/flake8) here"; exit 0

sbom:
	@echo "Generate SBOM placeholder"; mkdir -p dist && echo "SBOM placeholder" > dist/SBOM.txt

hash:
	@python scripts/release/hash_all.py

manifest:
	@python scripts/release/build_manifest.py

.PHONY: setup verify test sign pin clean

setup:
	pip install -r requirements.txt

verify:
	python verify_all.py

test:
	pytest -q

sign:
	ED25519_PRIV_B64="$(ED25519_PRIV_B64)" python verify_all.py

pin:
	IPFS_API_MULTIADDR="$(IPFS_API_MULTIADDR)" PINATA_JWT="$(PINATA_JWT)" python verify_all.py

clean:
	rm -rf __pycache__ .pytest_cache verifier/**/__pycache__ attestations/*.json

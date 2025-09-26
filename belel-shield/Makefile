SHELL := /bin/bash
ROOT  := $(shell pwd)

BL_JSON := belel-shield/sentinel/blocklists/belel-blocklist.json
BL_CHECKSUM := belel-shield/sentinel/blocklists/belel-blocklist.sha256
DASH_DIR := belel-shield/dashboard
FW_LINUX := belel-shield/firewall/linux/belel_firewall.sh
PKG_DIR := belel-shield/packaging

.PHONY: help verify sign release dashboard firewall-apply firewall-flush docker-build docker-run lint

help:
	@echo "Targets:"
	@echo "  make verify           - verify blocklist checksum (sha256)"
	@echo "  make sign             - (local) create sha256 + GPG-sign blocklist"
	@echo "  make release          - build + sign artifacts"
	@echo "  make dashboard        - run Streamlit dashboard (demo)"
	@echo "  make firewall-apply   - apply firewall rules on this OS"
	@echo "  make firewall-flush   - flush firewall rules on this OS"
	@echo "  make docker-build     - build firewall container"
	@echo "  make docker-run       - run firewall container (host net)"
	@echo "  make lint             - basic Python lint"

verify:
	@python3 scripts/hash_blocklist.py --verify $(BL_JSON) $(BL_CHECKSUM)

sign:
	@if ! command -v gpg >/dev/null; then echo "gpg not found"; exit 1; fi
	shasum -a 256 $(BL_JSON) > $(BL_CHECKSUM)
	gpg --armor --detach-sign $(BL_JSON)
	gpg --armor --detach-sign $(BL_CHECKSUM)
	@echo "Signed: $(BL_JSON) + $(BL_CHECKSUM)"

release: sign
	@echo "Release artifacts prepared locally."

dashboard:
	cd $(DASH_DIR) && streamlit run app.py --server.port=8501

firewall-apply:
	@if [[ "$$(uname -s)" == "Linux" ]]; then \
		$(FW_LINUX); \
	elif [[ "$$(uname -s)" == "Darwin" ]]; then \
		sudo pfctl -f belel-shield/firewall/macos/pf.conf && sudo pfctl -e; \
	elif [[ "$$OS" == "Windows_NT" ]]; then \
		powershell -ExecutionPolicy Bypass -File belel-shield\\firewall\\windows\\BelelFirewall.ps1; \
	else echo "Unsupported OS"; exit 1; fi

firewall-flush:
	@if [[ "$$(uname -s)" == "Linux" ]]; then \
		sudo nft flush ruleset; \
	elif [[ "$$(uname -s)" == "Darwin" ]]; then \
		sudo pfctl -d; \
	elif [[ "$$OS" == "Windows_NT" ]]; then \
		powershell "Get-NetFirewallRule -Group 'Belel Shield' | Remove-NetFirewallRule"; \
	else echo "Unsupported OS"; exit 1; fi

docker-build:
	docker build -t belel-firewall -f $(PKG_DIR)/Dockerfile.firewall .

docker-run:
	docker run --rm -it --net=host --cap-add NET_ADMIN \
	  -v $$HOME/.belel:/root/.belel:ro \
	  -v $(ROOT)/belel-shield/firewall/linux:/app/firewall:ro \
	  belel-firewall

lint:
	python3 -m pip install --quiet ruff || true
	ruff check .

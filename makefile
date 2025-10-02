.PHONY: setup verify test

setup:
	pip install -r requirements.txt

verify:
	python verify_all.py

test:
	pytest -q

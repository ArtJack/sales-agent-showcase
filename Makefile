.PHONY: demo test scan

demo:
	python3 demo.py

test:
	python3 -m pytest

scan:
	bash scripts/scan.sh

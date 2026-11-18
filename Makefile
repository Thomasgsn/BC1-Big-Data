PYTHON ?= .venv/bin/python
.PHONY: test profile bootstrap config smoke

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

profile:
	PYTHONPATH=src $(PYTHON) -m rncp_bc1.dataset profile --csv data/raw/PS_20174392719_1491204439457_log.csv --output docs/evidence/p1/paysim-profile.json

bootstrap:
	$(PYTHON) scripts/bootstrap.py

config: bootstrap
	docker compose config --quiet

smoke:
	bash scripts/stack.sh smoke

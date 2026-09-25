.PHONY: help download flash-plan hardware shellcheck test docs docs-serve

help:
	@echo "make download     Download and verify the pinned Pocknix SD image"
	@echo "make flash-plan   Show the pinned image and external disks; writes nothing"
	@echo "make hardware     Print a hardware report for this machine"
	@echo "make shellcheck   Lint the shell scripts"
	@echo "make test         Run the Python tests"
	@echo "make docs         Build the MkDocs site"
	@echo "make docs-serve   Preview the MkDocs site"

download:
	./scripts/flash-sd.sh --download

flash-plan:
	./scripts/flash-sd.sh

hardware:
	./scripts/detect-hardware.sh

shellcheck:
	shellcheck --external-sources --source-path=SCRIPTDIR scripts/*.sh scripts/lib/*.sh image/firstboot/*.sh

test:
	python3 -m pytest -q

docs:
	python3 -m mkdocs build --strict

docs-serve:
	python3 -m mkdocs serve

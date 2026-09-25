.PHONY: help download flash-plan hardware shellcheck

help:
	@echo "make download     Download and verify the pinned Pocknix SD image"
	@echo "make flash-plan   Show the pinned image and external disks; writes nothing"
	@echo "make hardware     Print a hardware report for this machine"
	@echo "make shellcheck   Lint the shell scripts"

download:
	./scripts/flash-sd.sh --download

flash-plan:
	./scripts/flash-sd.sh

hardware:
	./scripts/detect-hardware.sh

shellcheck:
	shellcheck --external-sources --source-path=SCRIPTDIR scripts/*.sh scripts/lib/*.sh

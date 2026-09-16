.PHONY: check
check:
	uv run ty check --fix --output-format concise

.PHONY: build
build:
	./scripts/build.py

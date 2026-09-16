.PHONY: check
check:
	uv run ty check --fix --output-format concise

.PHONY: build
build:
	uv run ./scripts/build.py build

.PHONY: release
release:
	uv run ./scripts/build.py release $(version)

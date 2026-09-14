PORT ?= 8000

.PHONY: help install run test

help:
	@echo "make install  - install/sync dependencies"
	@echo "make run      - start the dev server on :$(PORT) (override with PORT=...)"
	@echo "make test     - run the test suite"

install:
	uv sync

run:
	uv run uvicorn app.main:app --reload --port $(PORT)

test:
	uv run pytest -v

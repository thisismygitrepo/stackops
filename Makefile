# Makefile for project maintenance tasks

.PHONY: docs

docs:
	uv sync --group dev --frozen
	uv run zensical build

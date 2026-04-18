# Makefile for project maintenance tasks

.PHONY: docs

docs:
	pip install .[docs]
	pdoc stackops --output-dir docs

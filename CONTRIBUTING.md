# Contributing to StackOps

## Getting started

1. Clone the repository:
   ```bash
   git clone https://github.com/thisismygitrepo/stackops.git
   cd stackops
   ```

2. Install [uv](https://docs.astral.sh/uv/) and sync dependencies:
   ```bash
   uv sync --group dev
   ```

3. Verify the CLI works:
   ```bash
   uv run devops --help
   ```

## Development workflow

- Run any Python file: `uv run <file.py>`
- Add a dependency: `uv add <package_name>`
- Type-check touched files: `uv run -m pyright <file>`
- Full lint and type check: `uv run ./src/stackops/scripts/python/ai/scripts/lint_and_type_check.py`
- Tests (if applicable): `uv run -m pytest tests/`

## Code standards

- Python 3.13+ syntax; use modern features (match/case, type unions, pathlib, etc.).
- Fully type-hint all public functions, methods, and module-level variables.
- Follow the existing project conventions in `AGENTS.md`.
- Keep modules under ~200 lines; split into cohesive submodules when they grow.
- Prefer functional style over OOP; avoid default arguments in library code.
- Do not introduce fallback paths or backward-compatibility shims.

## Submitting changes

1. Create a feature branch from `main`.
2. Make focused, atomic commits.
3. Ensure `pyright` and the lint script pass cleanly.
4. Open a pull request against `main` and describe what changed and why.

## Reporting issues

Use the GitHub issue templates:
- [Bug report](https://github.com/thisismygitrepo/stackops/issues/new?template=bug_report.md)
- [Feature request](https://github.com/thisismygitrepo/stackops/issues/new?template=feature_request.md)

## Code of conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

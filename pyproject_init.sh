#!/bin/bash
set -e
uv cache clean --force
rm -rfd .venv
uv add --no-cache 'fire' 'gitpython' 'joblib' 'psutil' 'pyyaml' 'questionary' 'randomname' 'requests' 'rich' 'tenacity' 'typer'
uv add --no-cache --dev 'aider' 'build' 'cleanpy' 'cowsay' 'duckdb' 'gdown' 'griffe' 'ipdb' 'ipykernel' 'ipython' 'kaleido' 'marimo' 'matplotlib' 'mkdocstrings' 'mkdocstrings-python' 'mypy' 'numpy' 'pandas' 'paramiko' 'plotly' 'polars' 'pre-commit' 'pudb' 'py7zr' 'pydantic' 'pydeps' 'pyinstaller' 'pylint' 'pylsp-mypy' 'pymupdf' 'pypdf' 'pyrefly' 'pyright' 'pytest' 'python-lsp-server[mypy]' 'qrcode' 'ruff' 'ruff-lsp' 'sqlalchemy' 'textual' 'trogon' 'ty' 'types-mysqlclient' 'types-paramiko' 'types-pytz' 'types-pyyaml' 'types-requests' 'types-sqlalchemy' 'types-toml' 'types-urllib3' 'vt-py' 'yapf' 'zensical'
uv add --no-cache --group other 'duckdb-engine' 'pycrucible' 'vt-py'
uv add --no-cache --group plot 'duckdb' 'ipykernel' 'ipython' 'jupyterlab' 'kaleido' 'matplotlib' 'nbformat' 'numpy' 'plotly' 'polars' 'python-magic' 'sqlalchemy'

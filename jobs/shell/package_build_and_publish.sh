#!/bin/bash

# Exit on any error
set -e

echo "🧹 Cleaning previous build artifacts..."
rm -rf dist/ build/ *.egg-info/

echo "🔨 Building package..."
uv build

echo "📦 Listing built artifacts:"
ls -la dist/

# Extract PyPI token from .pypirc file
echo "🔑 Extracting PyPI token..."
PYPI_TOKEN_PATH=$(uv run python -c "from stackops.utils.source_of_truth import DOTFILES_PYPIRC_PATH; print(DOTFILES_PYPIRC_PATH)")
PYPI_TOKEN=$(grep -A2 "\[pypi\]" "$PYPI_TOKEN_PATH" | grep "password" | sed 's/password = //')

if [ -z "$PYPI_TOKEN" ]; then
    echo "❌ Error: Could not extract PyPI token from .pypirc file"
    exit 1
fi

echo "🚀 Publishing to PyPI..."
uv publish --token $PYPI_TOKEN

echo "✅ Successfully published to PyPI!"

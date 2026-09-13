# GitHub Action PyPI Publishing Setup

This repository is configured with a GitHub Action that automatically builds and publishes the package to PyPI when the version in `pyproject.toml` is updated.

## How it works

The workflow triggers on every push to the `main` branch and:

1. **Version Check**: Checks whether the version in `pyproject.toml` is already on PyPI
2. **Build & Publish**: Runs checks and builds the package, then publishes an unpublished version to PyPI
3. **GitHub Release**: Creates a GitHub release with the new version tag
4. **Test Build**: Already published versions and pull requests run checks without publishing

## Setup Instructions

### 1. Set up PyPI Token

You need to configure a PyPI API token as a GitHub secret:

1. **Generate PyPI API Token**:
   - Go to [PyPI Account Settings](https://pypi.org/manage/account/token/)
   - Click "Add API Token"
   - Set token name (e.g., "GitHub Actions - stackops")
   - Set scope to "Entire account" or limit to your package
   - Copy the generated token (starts with `pypi-`)

2. **Add GitHub Secret**:
   - Go to your GitHub repository
   - Navigate to Settings → Secrets and variables → Actions
   - Click "New repository secret"
   - Name: `PYPI_TOKEN`
   - Value: Paste your PyPI API token
   - Click "Add secret"

### 2. Publishing a new version

The developer-only `release` command is available when `~/code/stackops` is a StackOps Git checkout. It always operates on that checkout.

To prepare a release for local review:

```bash
devops self release
```

This increments the calendar version through `uv`, updates the lockfile and managed source references, and syncs dependencies. Versions use `YY.M` for the first release of a month, followed by `YY.M.1`, `YY.M.2`, and so on.

To prepare and push a release in one command, start with a clean `main` branch synchronized with `origin`:

```bash
devops self release --publish
```

This commits the release changes, creates `v<version>`, and pushes `main` and that tag together. The existing workflow publishes after its checks pass; no manual workflow invocation is needed. The `main` push triggers publication, so pushing only a tag does not publish.

These are alternative flows: after preparing locally, review and commit those changes and push `main` yourself. Running `release` again would increment the version again.

### 3. Monitoring the workflow

- Check the "Actions" tab in your GitHub repository to monitor workflow runs
- Publication uses `PYPI_TOKEN` when configured, otherwise PyPI trusted publishing
- Build artifacts are attached to GitHub releases

## Workflow Features

- **Version Detection**: Only publishes versions absent from PyPI
- **Pull Request Testing**: Tests builds on PRs without publishing
- **GitHub Releases**: Automatically creates releases with build artifacts
- **Modern tooling**: Uses `uv` for fast, reliable builds and publishing
- **Error Handling**: Fails fast on build or publish errors

## Troubleshooting

- **Version already published**: Run `devops self release` to prepare the next version
- **"PyPI token not found"**: Ensure `PYPI_TOKEN` secret is properly set in GitHub repository settings
- **Build failures**: Check the Actions log for detailed error messages
- **Permission errors**: Ensure your PyPI token has sufficient permissions for the package

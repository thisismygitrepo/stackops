# StackOps Command Reference: `devops self security`

Regenerated from `src/stackops/scripts/python/graph/cli_graph.json` on 2026-06-21.

This page expands exactly one level below `devops self security`. Follow child links one command segment at a time.

## Current Command

- Path: `devops self security`
- Kind: `group`
- Source: `src/stackops/scripts/python/helpers/helpers_devops/cli_self.py` -> `stackops.jobs.installer.checks.security_cli.get_app` via `security`
- Help: `🔐 <y> Security related CLI tools.`

## Help Commands

- `UV_CACHE_DIR=/tmp/uv-cache uv run devops self security --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run stackops devops self security --help`

## Immediate Children

- [`devops self security scan`](command--devops--self--security--scan.md) - command with no child commands. Help: `<s> Scan installed apps or a single file path with VirusTotal`.
- [`devops self security list`](command--devops--self--security--list.md) - command with no child commands. Help: `<l> List installed apps, optionally filtered by comma-separated app names`.
- [`devops self security upload`](command--devops--self--security--upload.md) - command with no child commands. Help: `<u> Upload a local file to cloud storage`.
- [`devops self security download`](command--devops--self--security--download.md) - command with no child commands. Help: `<d> Download a file from Google Drive`.
- [`devops self security install`](command--devops--self--security--install.md) - command with no child commands. Help: `<i> Install safe apps from app metadata report`.
- [`devops self security report`](command--devops--self--security--report.md) - command with no child commands. Help: `<r> Show the full saved scan report by default, or CSV rows/summary stats`.

## Notes

- Developer-only command groups under `devops self` depend on the developer checkout at `~/code/stackops`.
- Callback groups are invoked as the group command itself when their command reference has no children.
- The generated graph stores aliases on each node. Use `src/stackops/scripts/python/graph/cli_graph.json` when alias details matter.
- Docs may lag source. Prefer command paths and behavior verified from current Typer source and `--help` output.

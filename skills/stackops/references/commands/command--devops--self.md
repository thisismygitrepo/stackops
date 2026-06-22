# StackOps Command Reference: `devops self`

Regenerated from `src/stackops/scripts/python/graph/cli_graph.json` on 2026-06-21.

This page expands exactly one level below `devops self`. Follow child links one command segment at a time.

## Current Command

- Path: `devops self`
- Kind: `group`
- Source: `src/stackops/scripts/python/devops.py` -> `stackops.scripts.python.helpers.helpers_devops.cli_self.get_app` via `self`
- Help: `🔧 <s> Self management`

## Help Commands

- `UV_CACHE_DIR=/tmp/uv-cache uv run devops self --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run stackops devops self --help`

## Immediate Children

- [`devops self install`](command--devops--self--install.md) - command with no child commands. Help: `📋 <i> install stackops locally for nightly updates.`.
- [`devops self clone`](command--devops--self--clone.md) - command with no child commands. Help: `📥 <c> Clone the StackOps source checkout.`.
- [`devops self update`](command--devops--self--update.md) - command with no child commands. Help: `🔄 <u> UPDATE stackops`.
- [`devops self status`](command--devops--self--status.md) - command with no child commands. Help: `📊 <s> STATUS of machine, shell profile, apps, symlinks, dotfiles, etc.`.
- [`devops self security`](command--devops--self--security.md) - group with 6 immediate child commands. Help: `🔐 <y> Security related CLI tools.`.
- [`devops self explore-cli`](command--devops--self--explore-cli.md) - group with 5 immediate child commands. Help: `🧭 <x> Explore the StackOps CLI graph.`.
- [`devops self explore-python-api`](command--devops--self--explore-python-api.md) - group with 6 immediate child commands. Help: `🧭 <p> Explore the StackOps Python API graph.`.
- [`devops self readme`](command--devops--self--readme.md) - command with no child commands. Help: `📚 <r> render readme markdown in terminal.`.
- [`devops self docs`](command--devops--self--docs.md) - command with no child commands. Help: `📚 <o> Serve local docs with preview URLs.`.
- [`devops self build-installer`](command--devops--self--build-installer.md) - command with no child commands. Help: `📤 <e> Build an offline installer.`.
- [`devops self download-installer`](command--devops--self--download-installer.md) - command with no child commands. Help: `📥 <D> Download an offline installer.`.
- [`devops self build-docker`](command--devops--self--build-docker.md) - command with no child commands. Help: `🧱 <d> Build docker images (wraps jobs/shell/docker_build_and_publish.sh)`.
- [`devops self build-graph`](command--devops--self--build-graph.md) - command with no child commands. Help: `🕸 <g> Build the architecture dependency graph.`.
- [`devops self build-assets`](command--devops--self--build-assets.md) - group with 3 immediate child commands. Help: `🗂 <a> Regenerate repo-local CLI and skill assets.`.

## Notes

- Developer-only command groups under `devops self` depend on the developer checkout at `~/code/stackops`.
- Callback groups are invoked as the group command itself when their command reference has no children.
- The generated graph stores aliases on each node. Use `src/stackops/scripts/python/graph/cli_graph.json` when alias details matter.
- Docs may lag source. Prefer command paths and behavior verified from current Typer source and `--help` output.

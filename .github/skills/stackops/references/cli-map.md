# StackOps CLI Map

Regenerated from `src/stackops/scripts/python/graph/cli_graph.json` on 2026-06-12.

This reference intentionally uses:
- direct commands only
- canonical command names only

This reference intentionally excludes:
- short aliases
- hidden alias-only paths

The tree is root-relative: use `devops repos sync` directly, or `stackops devops repos sync` through the umbrella entrypoint.

## Direct Entry Points

Defined in `pyproject.toml` `[project.scripts]`:

- `devops` -> `stackops.scripts.python.devops:main`
- `cloud` -> `stackops.scripts.python.cloud:main`
- `fire` -> `stackops.scripts.python.fire_jobs:main`
- `agents` -> `stackops.scripts.python.agents:main`
- `terminal` -> `stackops.scripts.python.terminal:main`
- `preview` -> `stackops.scripts.python.preview:main`
- `utils` -> `stackops.scripts.python.utils:main`
- `stackops` -> `stackops.scripts.python.stackops_entry:main`
- `seek` -> `stackops.scripts.python.seek:main`

## Command Tree

```text
stackops
├─ devops
│  ├─ install
│  ├─ data
│  │  ├─ sync
│  │  ├─ register
│  │  └─ edit
│  ├─ repos
│  │  ├─ sync
│  │  ├─ register
│  │  ├─ action
│  │  ├─ analyze
│  │  ├─ guard
│  │  ├─ viz
│  │  ├─ count-lines
│  │  ├─ config-linters
│  │  └─ cleanup
│  ├─ config
│  │  ├─ sync
│  │  ├─ register
│  │  ├─ edit
│  │  ├─ export-dotfiles
│  │  ├─ import-dotfiles
│  │  ├─ terminal
│  │  │  ├─ config-shell
│  │  │  ├─ starship-theme
│  │  │  ├─ pwsh-theme
│  │  │  ├─ wezterm-theme
│  │  │  ├─ ghostty-theme
│  │  │  ├─ windows-terminal-theme
│  │  │  └─ tmux-style
│  │  │     ├─ install-oh-my-tmux
│  │  │     ├─ apply-stackops-local
│  │  │     ├─ preset
│  │  │     ├─ set-option
│  │  │     ├─ reload
│  │  │     └─ status
│  │  ├─ interactive
│  │  ├─ copy-assets
│  │  ├─ secrets
│  │  │  ├─ search
│  │  │  ├─ stats
│  │  │  ├─ subset
│  │  │  ├─ add
│  │  │  └─ edit
│  │  └─ dump
│  ├─ vault
│  │  ├─ search
│  │  ├─ login-and-unlock
│  │  └─ clean-cache
│  ├─ network
│  │  ├─ share-terminal
│  │  ├─ share-server
│  │  ├─ send
│  │  ├─ receive
│  │  ├─ share-temp-file
│  │  ├─ ssh
│  │  │  ├─ install-server
│  │  │  ├─ change-port
│  │  │  ├─ add-key
│  │  │  └─ debug
│  │  ├─ device
│  │  │  ├─ switch-public-ip
│  │  │  ├─ wifi-select
│  │  │  ├─ bind-wsl-port
│  │  │  ├─ open-wsl-port
│  │  │  ├─ link-wsl-windows
│  │  │  ├─ reset-cloudflare-tunnel
│  │  │  └─ add-ip-exclusion-to-warp
│  │  ├─ show-address
│  │  └─ vscode-share
│  ├─ execute
│  └─ self
│     ├─ install
│     ├─ clone
│     ├─ update
│     ├─ status
│     ├─ security
│     │  ├─ scan
│     │  ├─ list
│     │  ├─ upload
│     │  ├─ download
│     │  ├─ install
│     │  └─ report
│     ├─ explore
│     │  ├─ search
│     │  ├─ tree
│     │  ├─ dot
│     │  ├─ view
│     │  └─ tui
│     ├─ readme
│     ├─ docs
│     ├─ build-installer
│     ├─ download-installer
│     ├─ build-docker
│     ├─ build-graph
│     ├─ build-assets
│     │  ├─ update-cli-graph
│     │  ├─ regenerate-charts
│     │  └─ update-skill-refs
│     └─ workflows
│        ├─ update-installer
│        ├─ update-test
│        ├─ update-docs
│        └─ update-logic
├─ cloud
│  ├─ sync
│  ├─ copy
│  ├─ mount
│  └─ ftpx
├─ terminal
│  ├─ run
│  ├─ run-all
│  ├─ run-aoe
│  ├─ attach
│  ├─ kill
│  ├─ trace
│  ├─ create-from-function
│  ├─ balance-load
│  ├─ create-template
│  └─ summarize
├─ agents
│  ├─ parallel
│  │  ├─ create
│  │  ├─ create-context
│  │  ├─ run-parallel
│  │  ├─ collect
│  │  └─ make-template
│  ├─ browser
│  │  ├─ install-tech
│  │  └─ launch-browser
│  ├─ add-mcp
│  ├─ add-skill
│  ├─ add-todo
│  ├─ add-symlinks
│  ├─ add-config
│  ├─ run-prompt
│  ├─ run-interactive
│  └─ ask
├─ utils
│  ├─ machine
│  │  ├─ kill-process
│  │  ├─ environment
│  │  ├─ get-machine-specs
│  │  ├─ list-devices
│  │  └─ mount
│  ├─ pyproject
│  │  ├─ init-project
│  │  ├─ upgrade-packages
│  │  ├─ type-hint
│  │  ├─ type-check
│  │  ├─ type-fix (callback group)
│  │  ├─ test-runtime (callback group)
│  │  └─ test-reference
│  └─ file
│     ├─ edit
│     ├─ download
│     ├─ scrape
│     ├─ pdf-merge
│     ├─ pdf-compress
│     ├─ ocr
│     └─ read-db
├─ seek
│  └─ seek
├─ fire
└─ preview
```

## Important Nuances

- `devops self docs`, `devops self build-docker`, `devops self build-assets`, and `devops self workflows` are registered only when the developer checkout exists at `~/code/stackops`.
- Callback groups such as `utils pyproject type-fix` and `utils pyproject test-runtime` are invoked as the group command itself.
- The generated graph stores aliases on each node. Use `src/stackops/scripts/python/graph/cli_graph.json` when alias details matter.
- Docs may lag source. Prefer command paths and behavior verified from current Typer source and `--help` output.

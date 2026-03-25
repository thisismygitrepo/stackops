# mcfg

`mcfg` is the compatibility and umbrella entrypoint for Machineconfig. It is not the old monolithic command tree documented in earlier versions.

`machineconfig` points to the same dispatcher.

---

## Usage

```bash
mcfg [OPTIONS] COMMAND [ARGS]...
```

The current help surface is intentionally shallow: `mcfg` routes you into the main app families, and those families own the detailed subcommands.

---

## Available commands

Current `mcfg --help` exposes:

| Command | Purpose |
|---------|---------|
| `devops` | DevOps-related commands |
| `cloud` | Cloud management commands |
| `sessions` | Session and layout management |
| `agents` | AI agent management commands |
| `utils` | Utility commands |
| `fire` | Fire and manage jobs |
| `croshell` | Cross-shell command execution |

`msearch` remains available as a direct entrypoint, but it is invoked separately as `msearch`, not through `mcfg --help`.

---

## How to use it

Use `mcfg` when you want a single compatibility command:

```bash
mcfg devops --help
mcfg devops config terminal --help
mcfg cloud --help
mcfg sessions --help
```

Or call the direct entrypoints instead:

```bash
devops --help
cloud --help
sessions --help
```

Both `mcfg ...` and `machineconfig ...` dispatch to the same current app surface.

---

## Notes

- `mcfg` does not currently expose old standalone sections such as `shell`, `config`, `dotfiles`, `define`, or `links`.
- Configuration and dotfiles workflows now live primarily under `devops config ...`.
- Data backup and retrieval workflows now live under `devops data ...`.

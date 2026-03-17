# utils

`utils` is the direct entrypoint for Machineconfig helper utilities.

---

## Usage

```bash
utils [OPTIONS] COMMAND [ARGS]...
```

Current top-level commands:

| Command | Purpose |
|---------|---------|
| `kill-process` | Choose a process to kill |
| `environment` | Inspect and navigate environment and PATH variables |
| `get-machine-specs` | Print machine specifications |
| `init-project` | Initialize a project with a uv environment and dev packages |
| `upgrade-packages` | Upgrade project dependencies |
| `type-hint` | Type-hint a file or project directory |
| `edit` | Open a file in the default editor |
| `download` | Download a file and optionally decompress it |
| `pdf-merge` | Merge two PDF files |
| `pdf-compress` | Compress a PDF file |
| `read-db` | Launch the TUI database visualizer |

---

## Typical flow

Use live help to inspect the command you want:

```bash
utils --help
utils environment --help
utils init-project --help
utils download --help
```

The same surface is also reachable through the umbrella dispatcher:

```bash
mcfg utils --help
machineconfig utils --help
```

---

## Notes

- `utils` covers several unrelated helper workflows, so `utils --help` is the best entry point for discovery.
- Prefer the direct `utils` command in docs and scripts rather than routing through the older umbrella command by default.

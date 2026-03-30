# utils

`utils` is the direct entrypoint for Machineconfig helper utilities.

---

## Usage

```bash
utils [OPTIONS] COMMAND [ARGS]...
```

Top-level sub-apps:

| Sub-app | Purpose |
|---------|---------|
| `machine` | Process, environment, machine specs, and local device helpers |
| `pyproject` | Project bootstrap, dependency maintenance, and type-hint generation |
| `file` | File editing, downloading, PDF tools, and database viewing |

Commands under `utils machine`:

| Command | Purpose |
|---------|---------|
| `kill-process` | Choose a process to kill |
| `environment` | Inspect and navigate environment and PATH variables |
| `get-machine-specs` | Print machine specifications |
| `list-devices` | List mountable local devices |
| `mount` | Mount a local device to a mount point |

Commands under `utils pyproject`:

| Command | Purpose |
|---------|---------|
| `init-project` | Initialize a project with a uv environment and dev packages |
| `upgrade-packages` | Upgrade project dependencies |
| `type-hint` | Type-hint a file or project directory |

Commands under `utils file`:

| Command | Purpose |
|---------|---------|
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
utils machine --help
utils machine mount --help
utils pyproject init-project --help
utils file download --help
```

---

## Notes

- `utils` now groups helper workflows under `machine`, `pyproject`, and `file`, so start with `utils --help` and then drill into the subgroup you need.
- Prefer the direct `utils` command in docs and scripts rather than routing through the older umbrella command by default.

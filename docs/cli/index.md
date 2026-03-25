# CLI Reference

Machineconfig currently exposes a set of direct CLI entrypoints. For day-to-day use and scripting, prefer those direct commands over older all-in-one command trees.

---

## Direct entrypoints

These commands are defined in `pyproject.toml` and reflected in the current CLI map:

| Command | Purpose |
|---------|---------|
| `devops` | Package installation, configuration, data, repo, network, and self-management workflows |
| [`cloud`](cloud.md) | Cloud sync, copy, mount, and FTP-over-SSH helpers |
| [`sessions`](sessions.md) | Session and layout management |
| [`agents`](agents.md) | AI agent utilities |
| [`utils`](utils.md) | General-purpose utilities |
| [`fire`](fire.md) | Fire job runner |
| `croshell` | Cross-shell execution helper |
| `msearch` | Search helper entrypoint |

---

## Compatibility entrypoints

`mcfg` and `machineconfig` still exist, but they act as umbrella dispatch commands rather than a full standalone command tree.

| Command | Notes |
|---------|-------|
| [`mcfg`](mcfg.md) | Compatibility wrapper that dispatches to the main app families |
| `machineconfig` | Same dispatcher as `mcfg` |

Today, `mcfg --help` and `machineconfig --help` expose these top-level command groups:

- `devops`
- `cloud`
- `sessions`
- `agents`
- `utils`
- `fire`
- `croshell`

`msearch` is a separate direct entrypoint and is not listed by `mcfg --help`.

---

## Getting help

Use `--help` on the direct command you want to explore:

```bash
devops --help
devops install --help
devops config terminal --help
devops config sync --help
devops data sync --help
cloud --help
sessions --help
agents --help
utils --help
msearch --help
```

If you prefer the compatibility wrapper, these routes are equivalent:

```bash
mcfg devops --help
machineconfig sessions --help
```

---

## Command model

The current docs follow this model:

1. Start from a direct entrypoint such as `devops` or `sessions`.
2. Drill into nested apps with `--help`.
3. Use `mcfg` or `machineconfig` only when you specifically want the umbrella dispatcher.

For example:

```bash
devops config --help
devops data --help
sessions --help
```

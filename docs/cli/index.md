# CLI Reference

Machineconfig currently exposes a set of direct CLI entrypoints. For day-to-day use and scripting, prefer those direct commands over older all-in-one command trees.

---

## Direct entrypoints

These commands are defined in `pyproject.toml` and reflected in the current CLI map:

| Command | Purpose |
|---------|---------|
| [`devops`](devops.md) | Package installation, configuration, data, repo, network, and self-management workflows |
| [`sessions`](sessions.md) | Session and layout management |
| [`agents`](agents.md) | AI agent utilities |
| [`utils`](utils.md) | General-purpose utilities |
| `croshell` | Cross-shell execution helper |
| [`msearch`](msearch.md) | Search helper entrypoint |
| [`fire`](fire.md) | Fire job runner |
| [`cloud`](cloud.md) | Cloud sync, copy, mount, and FTP-over-SSH helpers |

---

## Getting help

Use `--help` on the direct command you want to explore:

```bash
devops --help
devops install --help
devops config terminal --help
devops config sync --help
devops data sync --help
sessions --help
agents --help
utils --help
msearch --help
fire --help
cloud --help
```

---

## Command model

The current docs follow this model:

1. Start from a direct entrypoint such as `devops` or `sessions`.
2. Drill into nested apps with `--help`.
3. Use standalone helpers like `fire`, `cloud`, and `msearch` directly.

For example:

```bash
devops config --help
devops data --help
sessions --help
fire --help
cloud --help
```

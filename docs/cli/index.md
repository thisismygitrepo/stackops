# CLI Reference

StackOps currently exposes two entry styles:

- standalone commands such as `devops`, `fire`, and `seek`
- umbrella wrapper: `stackops`

For day-to-day use, prefer the standalone command when you already know which tool you want. Use `stackops` when you want one top-level CLI that routes into the same command tree. The web UI is the exception: it is started only through [`stackops webui`](webui.md).

---

## Standalone entrypoints

| Command | Purpose |
| --- | --- |
| [`devops`](devops.md) | Package installation, repo automation, config sync, data sync, secrets, security scans, self-management, networking, and script execution |
| [`terminal`](terminal.md) | Terminal session and layout management |
| [`agents`](agents.md) | AI agent scaffolding, MCP catalog installs, and prompt runs |
| [`utils`](utils.md) | General-purpose utility commands |
| [`preview`](preview.md) | File preview and `uv run` backend launcher |
| [`seek`](seek.md) | Interactive search across files, text matches, and symbols |
| [`fire`](fire.md) | File, function, notebook, and app runner |
| [`cloud`](cloud.md) | Cloud sync, copy, mount, SSH transfer, and OneDrive helpers |

---

## Umbrella entrypoints

`stackops` is a lazy-loading wrapper around the same top-level command families:

```bash
stackops --help
stackops devops --help
stackops agents --help
```

Agents can read the usage guide for the installed version, with no skill install:

```bash
stackops --skill
```

Its own options are `--version`/`-V`, `--skill`/`-s`, and `--non-interactive`/`-N`, which never prompts or opens pickers and editors.

The wrappers currently expose:

- `devops`
- `cloud`
- `terminal`
- `agents`
- `utils`
- `seek`
- `fire`
- `preview`
- [`webui`](webui.md), the web UI for commands, dashboards, and terminals; it has no standalone command

The same wrapper also registers hidden one-letter aliases for these commands: `d`, `c`, `t`, `a`, `u`, `s`, `f`, `p`, and `w`.

For the full command-specific flag surface, check the standalone command as well, for example `fire --help` or `seek --help`.

---

## Getting help

```bash
devops --help
agents --help
cloud --help
preview --help
fire --help
seek --help
stackops --help
stackops webui --help
```

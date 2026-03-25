# agents

`agents` is the direct entrypoint for generating, collecting, and running Machineconfig agent assets.

---

## Usage

```bash
agents [OPTIONS] COMMAND [ARGS]...
```

Current top-level commands:

| Command | Purpose |
|---------|---------|
| `parallel` | Parallel workflow helpers: `create`, `create-context`, `collect`, `make-template` |
| `make-config` | Initialize AI configuration in the current repository |
| `make-todo` | Generate a markdown file listing Python files in the repo |
| `make-symlinks` | Create symlinks to the current repo in `~/code_copies/` |
| `run-prompt` | Run one prompt via a selected agent |
| `ask` | Ask a selected agent directly |
| `add-skill` | Add a skill to an agent |

---

## Typical flow

Use live help to inspect the command you need:

```bash
agents --help
agents parallel --help
agents parallel create --help
agents make-config --help
agents run-prompt --help
agents ask --help
```

If you prefer to start from the umbrella command, the same surface is reachable through:

```bash
mcfg agents --help
machineconfig agents --help
```

For `codex` runs, `run-prompt` also accepts explicit reasoning effort:

```bash
agents r --agent codex --reasoning-effort high "inspect the repo"
```

For quick one-shot asks, `ask` now accepts `--agent` and optional `--reasoning`:

```bash
agents ask h "inspect the repo"
agents ask --agent copilot --reasoning h "inspect the repo"
agents ask --agent gemini "summarize the current module"
```

---

## Notes

- `agents` is a direct entrypoint and is the clearest way to reach the current agent tooling.
- The exact options vary by subcommand, so rely on `--help` for the installed version you are running.

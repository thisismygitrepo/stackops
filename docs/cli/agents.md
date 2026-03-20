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
| `create` | Create an agents layout file ready to run |
| `create-context` | Run a prompt and ask an agent to persist context |
| `collect` | Collect agent materials into a single file |
| `make-template` | Create a template for fire agents |
| `make-config` | Initialize AI configuration in the current repository |
| `make-todo` | Generate a markdown file listing Python files in the repo |
| `make-symlinks` | Create symlinks to the current repo in `~/code_copies/` |
| `run-prompt` | Run one prompt via a selected agent |
| `ask` | Ask codex directly via `codex exec` |
| `add-skill` | Add a skill to an agent |

---

## Typical flow

Use live help to inspect the command you need:

```bash
agents --help
agents create --help
agents make-config --help
agents run-prompt --help
agents ask --help
```

If you prefer to start from the umbrella command, the same surface is reachable through:

```bash
mcfg agents --help
machineconfig agents --help
```

---

## Notes

- `agents` is a direct entrypoint and is the clearest way to reach the current agent tooling.
- The exact options vary by subcommand, so rely on `--help` for the installed version you are running.

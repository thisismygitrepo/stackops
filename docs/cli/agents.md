# agents

`agents` manages StackOps's AI-agent scaffolding, prompt execution, MCP catalog installs, and parallel multi-agent job files.

---

## Usage

```bash
agents [OPTIONS] COMMAND [ARGS]...
```

## Current top-level commands

| Command | Current behavior |
| --- | --- |
| `parallel` | Create agent layouts, create a shared context file, collect outputs, or emit a template command |
| `make-config` | Scaffold AI config files, instructions, and optional shared `.ai` assets in a repository |
| `add-mcp` | Resolve MCP entries from StackOps catalogs and install them into agent configs |
| `make-todo` | Generate filtered checklist files for repo contents |
| `make-symlinks` | Create `~/code_copies/<repo>_copy_<n>` symlinks to the current repo |
| `run-prompt` | Run one prompt through a selected agent, with inline, file, or YAML-backed context |
| `ask` | Ask a selected agent directly |
| `add-skill` | Add a supported skill into an agent directory |

---

## `parallel`

Current subcommands:

| Command | Behavior |
| --- | --- |
| `create` | Build an agent layout file with prompt/context splitting and output paths |
| `create-context` | Ask one agent to persist a shared `context.md` for a job |
| `collect` | Concatenate collected agent material files into one output file |
| `make-template` | Print a starter template for fire-agent usage |

`agents parallel create` currently accepts the main workflow controls: `--agent`, `--model`, `--reasoning-effort`, `--provider`, `--host`, `--context` or `--context-path`, `--prompt` or `--prompt-path`, `--prompt-name`, `--job-name`, `--agent-load`, `--separator`, `--agents-dir`, `--output-path`, and `--interactive`.

Examples:

```bash
agents parallel --help
agents parallel create --help
agents parallel create --agent codex --reasoning-effort high --context-path ./.ai/agents/docs/context.md --prompt-path ./.ai/prompts/update.md --job-name updateDocs
agents parallel create --agent pi --provider openai --model gpt-5.4 --reasoning-effort high --context-path ./.ai/agents/docs/context.md --prompt-path ./.ai/prompts/update.md --job-name updateDocsPi
agents parallel create-context --job-name updateDocs "Collect the repo context for this doc task"
agents parallel collect ./.ai/agents/updateDocs ./tmp/materials.txt
```

---

## Prompt-running commands

`run-prompt` is the structured workflow entrypoint. It supports:

- `--agent`
- `--reasoning-effort` for codex and pi agents
- `--context` or `--context-path`
- `--context-yaml-path` plus `--context-name`
- `--where` to choose catalog locations for context YAML lookup
- `--show-format` and `--edit` for prompts-YAML guidance and editing

Examples:

```bash
agents run-prompt --agent codex --reasoning-effort high --context-path ./context.md "inspect this repo"
agents run-prompt --agent copilot --context-name docs.cli --where all "update the assigned docs"
agents run-prompt --agent pi --reasoning-effort high --context-path ./context.md "inspect this repo"
agents run-prompt --show-format
```

`ask` is the lighter-weight direct path. Current behavior to keep in mind:

- default agent is `codex`
- `--reasoning` accepts `n`, `l`, `m`, `h`, `x`
- that shortcut is only supported for `codex`, `copilot`, and `pi`
- `--file-prompt` appends the file contents into the final prompt with explicit `BEGIN FILE` and `END FILE` markers

Examples:

```bash
agents ask --agent codex --reasoning h "inspect the repo"
agents ask --agent copilot --reasoning m "summarize the current module"
agents ask --agent pi --reasoning h "inspect the repo"
agents ask "summarize this file" --file-prompt ./README.md
```

---

## Repository and MCP helpers

`make-config` currently requires `--root` and can optionally add private config files, instructions, shared `.ai` assets, VS Code tasks, and `.gitignore` entries:

```bash
agents make-config --root .
agents make-config --root . --agent codex,copilot,pi --include-scripts --add-gitignore
```

`add-mcp` resolves names from StackOps MCP catalogs and installs them for one or more agents. It also accepts known agent-skill names as a compatibility path; those are installed through the skills CLI and are not written to MCP config. Notes:

- `--scope local` installs into the enclosing git repository; when run from a multi-repo workspace root, it installs into that workspace directory
- `--where` selects catalog locations
- `--edit` opens the catalog files and exits immediately if no MCP names were provided
- `copilot` means GitHub Copilot CLI. Local MCP config is written to `.mcp.json`; global MCP config is written to `$COPILOT_HOME/mcp-config.json` when `COPILOT_HOME` is set, otherwise `~/.copilot/mcp-config.json`
- `caveman` and `grill-me` are skills/plugins, not MCP servers; those names delegate to the same installer as `add-skill`
- PostgreSQL is available as `postgres`; replace the generated `DATABASE_URI` value before use

```bash
agents add-mcp --help
agents add-mcp postgres,filesystem --agent codex,copilot,pi --scope local
agents add-mcp caveman --agent codex --scope local
agents add-mcp --edit --where library
```

`make-todo` scans a repo or workspace and writes filtered checklist files under `.ai/todo/files` by default. `make-symlinks` creates repo symlinks under `~/code_copies/`.

---

## Browser Automation

`agents browser install-tech` prepares browser automation tooling. The default is the direct `agent-browser` CLI and Vercel skill. The direct MCP entries use explicit StackOps profile directories under `~/data/browsers-profiles/mcp/...`; CDP and extension MCP entries are cataloged too, and must be paired with browsers launched from StackOps custom profiles.

```bash
agents browser install-tech
agents browser install-tech --which chrome-devtools-mcp
agents browser install-tech --which playwright-mcp
agents add-mcp chrome-devtools --agent codex --scope local
agents add-mcp chrome-devtools-browser-url --agent codex --scope local
agents add-mcp playwright --agent codex --scope local
agents add-mcp playwright-cdp --agent codex --scope local
```

`agents browser launch-browser` launches Chrome or Brave with a dedicated CDP profile for tools that connect to an already running browser:

```bash
agents browser launch-browser --browser chrome --port 9222 --profile playwright-mcp
```

---

## `add-skill`

`add-skill` installs supported open agent skills through `bunx skills@latest add`. The shipped source aliases are `agent-browser`, `caveman`, and `grill-me`; unknown skill names exit with an error instead of searching for alternatives. `--agent` is passed through to the skills CLI without StackOps mapping, and omitting it lets the upstream tool choose or prompt for agent targets. Use `agents browser install-tech` for the browser-specific installer and MCP setup notes.

```bash
agents add-skill grill-me --scope local
agents add-skill caveman --agent codex --scope local
agents add-skill caveman --agent github-copilot --scope global
```

---

## Getting help

```bash
agents --help
agents parallel --help
agents make-config --help
agents add-mcp --help
agents make-todo --help
agents run-prompt --help
agents ask --help
agents add-skill --help
agents browser install-tech --help
```

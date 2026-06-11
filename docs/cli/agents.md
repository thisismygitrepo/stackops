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
| `browser` | Prepare browser automation tooling or launch Chrome / Brave with CDP enabled |
| `add-config` | Scaffold AI config files, instructions, and optional shared `.ai` assets in a repository |
| `add-mcp` | Resolve MCP entries from StackOps catalogs and install them into agent configs |
| `add-todo` | Generate filtered checklist files for repo contents |
| `add-symlinks` | Create `~/code_copies/<repo>_copy_<n>` symlinks to the current repo |
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
| `run-parallel` | Run a named parallel workflow from `parallel.yaml`, with `create` option overrides |
| `collect` | Concatenate collected agent material files into one output file |
| `make-template` | Print a starter template for fire-agent usage |

`agents parallel create` currently accepts the main workflow controls: `--agent`, `--model`, `--reasoning`, `--provider`, `--host`, `--context` or `--context-path`, `--prompt` or `--prompt-path`, `--prompt-name`, `--job-name`, `--agent-load`, `--stagger-max`, `--separator`, `--joined-prompt-context`, `--run`, `--agents-dir`, `--output-path`, `--save-as-yaml`, and `--interactive`. `--save-as-yaml` writes or updates `.stackops/agents/parallel.yaml` using the resolved job name as the top-level entry key.

`agents parallel run-parallel` reads flat top-level named entries from `parallel.yaml`. By default it searches the repo file first, then StackOps private/public/library locations. Use `--source`, `-S` to choose lookup locations, `--yaml-path` for an explicit file, `--show-format` to print the standard, `--edit` to open the YAML, and `--add-entry` to append a template entry before editing. Every `create` option can be overridden on the command line.

Standard `parallel.yaml` shape:

```yaml
entryExample:
  agent: codex
  model: null
  reasoning: null
  provider: null
  host: local
  context: null
  context_path: null
  separator: "\n@-@\n"
  agent_load: 3
  stagger_max: 3.0
  prompt: null
  prompt_path: null
  prompt_name: null
  job_name: AI_Agents
  join_prompt_and_context: false
  run: false
  output_path: null
  agents_dir: null
  interactive: false
```

Examples:

```bash
agents parallel --help
agents parallel create --help
agents parallel create --agent codex --reasoning high --context-path ./.ai/agents/docs/context.md --prompt-path ./.ai/prompts/update.md --job-name updateDocs
agents parallel create --agent codex --reasoning high --context-path ./.ai/agents/docs/context.md --prompt-path ./.ai/prompts/update.md --job-name updateDocs --save-as-yaml
agents parallel create --agent copilot --reasoning high --context-path ./.ai/agents/docs/context.md --prompt-path ./.ai/prompts/update.md --job-name updateDocsCopilot
agents parallel create --agent pi --provider openai --model gpt-5.4 --reasoning high --context-path ./.ai/agents/docs/context.md --prompt-path ./.ai/prompts/update.md --job-name updateDocsPi
agents parallel run-parallel default -S repo --agent-load 5
agents parallel run-parallel docs_update --yaml-path ./.ai/parallel.yaml --agent pi --reasoning high
agents parallel create-context --job-name updateDocs "Collect the repo context for this doc task"
agents parallel collect ./.ai/agents/updateDocs ./tmp/materials.txt
```

---

## Prompt-running commands

`run-prompt` is the structured workflow entrypoint. It supports:

- `--agent`
- `--reasoning` for codex, copilot, and pi agents; unsupported agents ignore it
- `--context` or `--context-path`
- `--context-yaml-path` plus `--context-name`
- `--source`, `-s` to choose catalog locations for context YAML lookup: `all`, `repo`, `private`, `public`, or `library`
- `--show-format` and `--edit` for prompts-YAML guidance and editing

For `run-prompt`, `--agent` defaults to `copilot`. `--source repo` or `-s repo` resolves to `<git-root>/.stackops/agents/prompts.yaml`.

Examples:

```bash
agents run-prompt --agent codex --reasoning high --context-path ./context.md "inspect this repo"
agents run-prompt --agent copilot --reasoning high --context-path ./context.md "inspect this repo"
agents run-prompt --agent copilot --context-name docs.cli -s all "update the assigned docs"
agents run-prompt --agent agy --context-path ./context.md "inspect this repo"
agents run-prompt --agent pi --reasoning high --context-path ./context.md "inspect this repo"
agents run-prompt --show-format
```

`ask` is the lighter-weight direct path. Current behavior to keep in mind:

- default agent is `pi`
- `--reasoning` accepts `n`, `l`, `m`, `h`, `x`
- that shortcut is only supported for `codex`, `copilot`, and `pi`
- `--file-prompt` appends the file contents into the final prompt with explicit file boundary markers
- `--quiet` skips the Rich preflight summary and streams agent output directly

Examples:

```bash
agents ask --agent codex --reasoning h "inspect the repo"
agents ask --agent copilot --reasoning m "summarize the current module"
agents ask --agent agy "inspect the repo"
agents ask --agent pi --reasoning h "inspect the repo"
agents ask "summarize this file" --file-prompt ./README.md
agents ask --quiet "summarize the current directory"
```

---

## Repository and MCP helpers

`add-config` currently requires `--agent` and can optionally add private config files, instructions, shared `.ai` assets, VS Code tasks, and `.gitignore` entries. Pass `--agent all` to configure every supported agent, or pass a comma-separated list.

```bash
agents add-config --agent all --root .
agents add-config --agent codex,copilot,agy,pi --root . --include-scripts --add-gitignore
```

`add-mcp` resolves names from StackOps MCP catalogs and installs them for one or more agents. It also accepts known agent-skill names as a compatibility path; those are installed through the skills CLI and are not written to MCP config. Notes:

- `--scope local` installs into the enclosing git repository; when run from a multi-repo workspace root, it installs into that workspace directory
- `--source`, `-S` selects catalog locations: `all`, `repo`, `private`, `public`, or `library`
- `--edit` opens the catalog files and exits immediately if no MCP names were provided
- `copilot` means GitHub Copilot CLI. Local MCP config is written to `.mcp.json`; global MCP config is written to `$COPILOT_HOME/mcp-config.json` when `COPILOT_HOME` is set, otherwise `~/.copilot/mcp-config.json`
- `agy` means Google Antigravity CLI. Local MCP config is written to `.agents/mcp_config.json`; global MCP config is written to `~/.gemini/antigravity-cli/mcp_config.json`
- `oz` means Warp Oz CLI. Local MCP config is written to `.warp/mcp.json` in Oz's direct `--mcp` file shape, and StackOps passes that file to `oz agent run --mcp` when it exists.
- `pi` local MCP config is written to `.pi/mcp.json`; global MCP config is written to `~/.pi/agent/mcp.json`
- `agent-browser`, `caveman`, `grill-me`, and `stackops` are skills/plugins, not MCP servers; those names delegate to the same installer as `add-skill`
- PostgreSQL is available as `postgres`; replace the generated `DATABASE_URI` value before use

For `add-mcp`, `--source repo` or `-S repo` resolves to `<git-root>/.stackops/mcp.json`.

```bash
agents add-mcp --help
agents add-mcp postgres,filesystem --agent codex,copilot,agy,oz,pi --scope local
agents add-mcp caveman --agent codex --scope local
agents add-mcp --edit -S library
```

`add-todo` scans a repo or workspace and writes filtered checklist files under `.ai/todo/files` by default. `add-symlinks` creates repo symlinks under `~/code_copies/`.

---

## Browser Automation

`agents browser install-tech` prepares browser automation tooling. The default is the direct `agent-browser` CLI and Vercel skill. `--which` accepts `agent-browser`, `playwright-cli`, `chrome-devtools-mcp`, or `playwright-mcp`. `playwright-cli` installs the official Playwright agent CLI and skills. The MCP entries write StackOps guide/config files under `~/code/agents/browser/mcp/...`; CDP and extension MCP entries are cataloged too, and must be paired with browsers launched from StackOps custom profiles.

```bash
agents browser install-tech
agents browser install-tech --which playwright-cli
agents browser install-tech --which chrome-devtools-mcp
agents browser install-tech --which playwright-mcp
agents add-mcp chrome-devtools --agent codex --scope local
agents add-mcp chrome-devtools-browser-url --agent codex --scope local
agents add-mcp playwright --agent codex --scope local
agents add-mcp playwright-cdp --agent codex --scope local
```

`agents browser launch-browser` launches Chrome or Brave with CDP enabled and an isolated profile for tools that attach to an existing browser. The default port is `9331`; pass `--port 9222` when using the shipped CDP MCP catalog entries without editing them. Omitting `--profile` uses a temp profile under the system temp directory; a profile name uses `~/data/browsers-profiles/<browser>/<profile>`.

```bash
agents browser launch-browser --browser chrome --port 9331 --profile agent-browser
agents browser launch-browser --browser chrome --port 9222 --profile playwright-mcp
```

---

## `add-skill`

`add-skill` installs supported open agent skills through `bunx skills@latest add`. The shipped source aliases are `agent-browser`, `caveman`, `grill-me`, and `stackops`; omitting the skill name opens the fuzzy picker over those aliases. Unknown skill names exit with an error instead of searching for alternatives. `--agent` is passed through to the skills CLI without StackOps mapping, and omitting it lets the upstream tool choose or prompt for agent targets. `--directory` chooses the install root and defaults to the current directory. Use `agents browser install-tech` for the browser-specific installer and MCP setup notes.

```bash
agents add-skill --scope local
agents add-skill stackops --agent codex --scope local
agents add-skill grill-me --scope local
agents add-skill caveman --agent codex --scope local
agents add-skill caveman --agent github-copilot --scope global
```

---

## Getting help

```bash
agents --help
agents parallel --help
agents add-config --help
agents add-mcp --help
agents add-todo --help
agents add-symlinks --help
agents run-prompt --help
agents ask --help
agents add-skill --help
agents browser install-tech --help
agents browser launch-browser --help
```

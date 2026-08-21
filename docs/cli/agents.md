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
| `browser` | Prepare browser automation tooling or launch supported browser automation endpoints |
| `iter` | Inspect and maintain current-format AgentOps iteration workspaces through Herdr 0.8.2 |
| `account` | Back up active agent credentials to saved profiles or retrieve a profile as active |
| `add-config` | Scaffold AI config files, instructions, and optional shared `.ai` assets in a repository |
| `add-mcp` | Resolve MCP entries from StackOps catalogs and install them into agent configs |
| `run-prompt` | Run one prompt through a selected agent, with inline, file, or YAML-backed context |
| `run-interactive` | Launch an agent with reasonable defaults |
| `ask` | Ask a selected agent directly |
| `add-skill` | Add a supported skill into an agent directory |

---

## `iter`

`iter` supports Herdr 0.8.2/protocol 20 only. Each maintenance command accepts exactly one targeting mode: an explicit stable `WORKSPACE_ID`, `--all`, or `--interactive`/`-I`. Use `--dry-run`/`-n` to preview `close` or `clean`. The interactive TV picker previews the live status and close plan for `status` and `close`; these commands locate each workspace's exact `.ai/agentops/iterations/<slug>/run.json` from Herdr agent cwd ancestry and do not require Git or the caller's cwd. `close` removes only quiet old tabs whose current handoff receipt still matches every stable Herdr identifier. `clean` is records-tree-local because inactive runs no longer exist in Herdr; run it anywhere beneath the project containing the `.ai/agentops` tree to clean. The obsolete polling budget tracker was removed because it could terminate a working successor.

```bash
agents iter status --all
agents iter status -I
agents iter close w1 --dry-run
agents iter close --all --dry-run
agents iter close -I
agents iter clean --all --dry-run
agents iter clean -I -n
```

---

## `account`

Account transfers always state their direction explicitly:

```bash
agents account backup codex --profile work
agents account retrieve codex --profile work
```

`backup` copies the agent's active credential into the target profile. For agents whose active credential contains a safe identity, omitting the profile updates the unique matching profile or creates a new identity-derived profile for a new login. Agents without a safe automatic identity still require `--profile`. `retrieve` copies the source profile into the agent's active credential file; omitting `--profile` opens the profile picker.

Use `--active-credential`/`-c` to override the agent-specific active file in either direction. `account` provides hidden `b` and `r` aliases for `backup` and `retrieve`; the hidden `A` alias supports the same subcommands:

```bash
agents account b codex
agents A r codex
```

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

`agents parallel create` currently accepts the main workflow controls: `--agent`, `--model`, `--reasoning`, `--provider`, `--host`, `--backend`, `--context` or `--context-path`, `--prompt` or `--prompt-path`, `--prompt-name`, `--job-name`, `--agent-load`, `--stagger-max`, `--separator`, `--joined-prompt-context`, `--run`, `--agents-dir`, `--output-path`, `--save-as-yaml`, and `--interactive`. `--backend` defaults to `tmux`; use `--backend herdr` when `--run` should launch the generated layout through Herdr, or `--backend aoe` when it should launch each generated agent script as an Agent of Empires session. `--save-as-yaml` writes or updates `.stackops/agents/parallel.yaml` using the resolved job name as the top-level entry key.

`agents parallel run-parallel` reads flat top-level named entries from `parallel.yaml`. By default it searches the repo file first, then StackOps private/public/library locations. Use `--source`, `-S` to choose lookup locations, `--yaml-path` for an explicit file, `--show-format` to print the standard, `--edit` to open the YAML, and `--add-entry` to append a template entry before editing. Every `create` option can be overridden on the command line.

Standard `parallel.yaml` shape:

```yaml
entryExample:
  agent: codex
  model: null
  reasoning: null
  provider: null
  host: local
  backend: tmux
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
agents parallel create --agent codex --backend herdr --run --context-path ./.ai/agents/docs/context.md --prompt-path ./.ai/prompts/update.md --job-name updateDocsHerdr
agents parallel create --agent codex --backend aoe --run --context-path ./.ai/agents/docs/context.md --prompt-path ./.ai/prompts/update.md --job-name updateDocsAoe
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
- free-form prompt parts after `--`; option-looking tokens after the delimiter are prompt text, not StackOps flags

For `run-prompt`, `--agent` defaults to `codex`. `--source repo` or `-s repo` resolves to `<git-root>/.stackops/agents/prompts.yaml`.
Shell metacharacters such as `|`, `>`, `$`, and `*` are still interpreted by your shell before StackOps receives the prompt.

Examples:

```bash
agents run-prompt --agent codex --reasoning high --context-path ./context.md "inspect this repo"
agents run-prompt --agent codex --reasoning high --context-path ./context.md -- inspect this repo --include-hidden
agents run-prompt --agent copilot --reasoning high --context-path ./context.md "inspect this repo"
agents run-prompt --agent copilot --context-name docs.cli -s all "update the assigned docs"
agents run-prompt --agent agy --context-path ./context.md "inspect this repo"
agents run-prompt --agent pi --reasoning high --context-path ./context.md "inspect this repo"
agents run-prompt --show-format
```

`run-interactive` launches an agent directly with sensible defaults. Current options:

- `--agent`/`-a` accepts `codex`/`x`, `copilot`/`c`, `pi`/`p`, or `opencode`/`omp`/`o`
- `--caveman`/`-c` starts the session with the caveman wenyan-full prompt
- `--headroom`/`-h` launches `codex` or `copilot` through headroom

Examples:

```bash
agents run-interactive --agent codex
agents run-interactive --agent copilot --caveman
agents run-interactive --agent codex --caveman --headroom
```

`ask` is the lighter-weight direct path. Current behavior to keep in mind:

- default agent is `codex`
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

`add-config` requires an agent argument and copies the latest AgentOps skill bundled with StackOps into `.agents/skills/agentops` by default. Pass `--no-agentops-skill`/`-A` to skip that copy. It can also add private config files, instructions, shared `.ai` assets, VS Code tasks, and `.gitignore` entries. Pass `all` to configure every supported agent, or pass a comma-separated list.

```bash
agents add-config all --root .
agents add-config codex,copilot,agy,pi --root . --include-scripts --add-gitignore
agents add-config codex --root . -A
```

`add-mcp` resolves names from StackOps MCP catalogs and installs them for one or more agents. It also accepts known agent-skill names as a compatibility path; those are installed through the skills CLI and are not written to MCP config. Notes:

- `--scope local` installs into the enclosing git repository; when run from a multi-repo workspace root, it installs into that workspace directory
- `--source`, `-S` selects catalog locations: `all`, `repo`, `private`, `public`, or `library`
- `--edit` opens the catalog files and exits immediately if no MCP names were provided
- `copilot` means GitHub Copilot CLI. Local MCP config is written to `.mcp.json`; global MCP config is written to `$COPILOT_HOME/mcp-config.json` when `COPILOT_HOME` is set, otherwise `~/.copilot/mcp-config.json`
- `agy` means Google Antigravity CLI. Local MCP config is written to `.agents/mcp_config.json`; global MCP config is written to `~/.gemini/antigravity-cli/mcp_config.json`
- `oz` means Warp Oz CLI. Local MCP config is written to `.warp/mcp.json` in Oz's direct `--mcp` file shape, and StackOps passes that file to `oz agent run --mcp` when it exists.
- `pi` local MCP config is written to `.pi/mcp.json`; global MCP config is written to `~/.pi/agent/mcp.json`
- `agent-browser`, `agent-skills`, `caveman`, `grill-with-docs`, `last30days`, `agentops`, and `stackops` are skills/plugins, not MCP servers; those names delegate to the same installer as `add-skill`
- PostgreSQL is available as `postgres`; replace the generated `DATABASE_URI` value before use

For `add-mcp`, `--source repo` or `-S repo` resolves to `<git-root>/.stackops/mcp.json`.

```bash
agents add-mcp --help
agents add-mcp postgres,filesystem --agent codex,copilot,agy,oz,pi --scope local
agents add-mcp caveman --agent codex --scope local
agents add-mcp --edit -S library
```

---

## Browser Automation

`agents browser install-tech` prepares browser automation tooling. The default is the direct `agent-browser` CLI and Vercel skill. `--which` accepts `agent-browser`, `pinchtab`, `playwright-cli`, `chrome-devtools-mcp`, or `playwright-mcp`. `pinchtab` installs the current release binary and its official agent skill. `playwright-cli` installs the official Playwright agent CLI and skills. The MCP entries write StackOps guide/config files under `~/code/agents/browser/mcp/...`; CDP and extension MCP entries are cataloged too, and must be paired with browsers launched from StackOps custom profiles.

```bash
agents browser install-tech
agents browser install-tech --which pinchtab
agents browser install-tech --which playwright-cli
agents browser install-tech --which chrome-devtools-mcp
agents browser install-tech --which playwright-mcp
agents add-mcp chrome-devtools --agent codex --scope local
agents add-mcp chrome-devtools-browser-url --agent codex --scope local
agents add-mcp playwright --agent codex --scope local
agents add-mcp playwright-cdp --agent codex --scope local
```

`agents browser launch-browser` launches Chrome, Brave, Edge, Firefox, or Safari automation endpoints. Chromium browsers use CDP with an isolated profile; Firefox uses WebDriver BiDi; Safari uses safaridriver. The default port is `9331`; pass `--port 9222` when using the shipped CDP MCP catalog entries without editing them. Omitting `--profile` uses a port-scoped profile under the system temp directory for profile-capable browsers; a profile name uses `~/data/browsers-profiles/<browser>/<profile>`. Pass `--tmp`/`-t` with `--profile` to copy that profile to `<profile>/.tmp/<random-alias>` and launch the copy. By default, StackOps runs browser endpoints in one `stackops-browser` tmux session with qualified windows such as `chrome-profile-agent-browser-p9331-endpoint`; `--lan`/`-l` adds a matching relay window and exposes the requested port through a StackOps relay on `0.0.0.0`. Pass `--detached`/`-d` to launch background processes instead of tmux windows.

```bash
agents browser launch-browser --browser chrome --port 9331 --profile agent-browser
agents browser launch-browser --browser edge --port 9331 --profile agent-browser
agents browser launch-browser --browser chrome --profile agent-browser --tmp
agents browser launch-browser --browser chrome --port 9222 --profile playwright-mcp
agents browser launch-browser --browser chrome --port 9331 --lan
agents browser launch-browser --browser chrome --port 9331 --profile agent-browser -d
agents browser status
agent-browser connect http://OTHER_COMPUTER_IP:9331
```

`agents browser batch-launch` launches every saved profile under `~/data/browsers-profiles/<browser>/` for the browser selected with `--browser`. Its `--port-start`/`--port`/`-p` base defaults to `60000`. Profiles named `pN` use `port-start + N`, so `p1` uses `60001`, `p2` uses `60002`, and so on by default. Other profile names use the next unreserved port above the base. Use `--max-profiles`/`--max`/`-n` to cap the launch count; StackOps launches the requested count or the number available, whichever is smaller. The command prints one compact table with each profile, IP, port, state, and tmux window or process ID. It supports the same `--lan` and `--detached` launch modes as `launch-browser`; Safari is excluded because it does not support custom profiles.

`agents browser batch-close` closes every StackOps-tracked launch for a saved profile or one of its `--tmp` copies for the selected browser, including both tmux and detached launches. It leaves port-scoped profiles, other browsers, and browser sessions not managed by StackOps untouched. Running it when no matching launches are active succeeds without changing anything.

```bash
agents browser batch-launch --browser chrome
agents browser L --browser firefox -n 4 --lan
agents browser batch-launch --browser brave --port-start 61000 --detached
agents browser batch-close --browser brave
```

`agents browser declutter` removes rebuildable data from a named profile after confirming that the selected browser is closed. Chrome, Brave, and Edge cleanup includes downloaded on-device AI models (including `OptGuideOnDeviceModel`) plus HTTP, code, GPU, shader, and extension-download caches. Firefox cleanup includes its disk, startup, and shader caches. Cookies, history, passwords, extensions, sessions, service-worker data, IndexedDB, and local storage are preserved. The command reports the recovered and remaining profile sizes in MiB.

`agents browser replicate COUNT` copies a closed source profile to `p1` through `pCOUNT`. Chrome is the default browser and `base` is the default source profile. All destination paths are checked before copying, and existing profiles are never overwritten. Both profile-maintenance commands use the same `~/data/browsers-profiles/<browser>/<profile>` layout on Windows, macOS, and Linux. They support Chrome, Brave, Edge, and Firefox; Safari is excluded because safaridriver does not support StackOps custom profiles.

```bash
agents browser declutter --profile alex-copy
agents browser declutter --browser firefox --profile base
agents browser replicate 4
agents browser replicate 3 --browser brave --profile alex-copy
```

---

## `add-skill`

`add-skill` uses the StackOps backend by default, copying bundled skills directly into `<repo-root>/.agents/skills/<skill>` for local installs. If the StackOps backend cannot handle the request, it reports the reason and falls back to the existing `bunx skills@latest add` path. Use `--backend bunx` to run the upstream skills CLI directly, or `--backend npx` to run `npx skills@latest add` instead. The shipped source aliases are `agent-browser`, `agent-skills`, `caveman`, `grill-with-docs`, `last30days`, `agentops`, and `stackops`; omitting the skill name opens the fuzzy picker over those aliases. Unknown skill names exit with an error instead of searching for alternatives. `--agent` is passed through to the skills CLI without StackOps mapping for `bunx`/`npx`; the StackOps backend installs into the shared repo-local skill directory. `--directory` chooses the install root and defaults to the current directory. Use `agents browser install-tech` for the browser-specific installer and MCP setup notes.

```bash
agents add-skill --scope local
agents add-skill stackops --agent codex --scope local
agents add-skill agent-skills --agent codex --scope global
agents add-skill last30days --agent codex --scope global --backend npx
agents add-skill stackops --scope local --backend s
agents add-skill agentops --scope local --backend stackops
agents add-skill grill-with-docs --scope local
agents add-skill caveman --agent codex --scope local
agents add-skill caveman --agent github-copilot --scope global
```

---

## Getting help

```bash
agents --help
agents account --help
agents account backup --help
agents account retrieve --help
agents parallel --help
agents add-config --help
agents add-mcp --help
agents run-prompt --help
agents run-interactive --help
agents ask --help
agents add-skill --help
agents browser install-tech --help
agents browser launch-browser --help
agents browser batch-launch --help
agents browser batch-close --help
agents browser declutter --help
agents browser replicate --help
```

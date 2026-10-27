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
| `add-mcp` | Resolve MCP entries from StackOps catalogs and install them into agent configs |
| `add-skill` | Add a supported skill into an agent directory |
| `init` | Scaffold AI config files, instructions, and optional shared `.ai` assets in a repository |
| `config` | Locate, initialize, and validate StackOps prompts, parallel workflow, and MCP catalogs |
| `browser` | Prepare browser automation tooling or launch supported browser automation endpoints |
| `second-brain` | Configure the Second Brain repository and its agent instructions |
| `doctor` | Inspect agent binaries, configuration, plugins, skills, and instruction provenance |
| `local` | Inspect local Ollama health, models, and resource usage |
| `run-prompt` | Run a prompt through a selected agent, with context and an optional interactive session |
| `run-interactive` | Launch an agent with reasonable defaults |
| `ask` | Ask a selected agent directly |
| `parallel` | Create or run agent layouts, create shared context, collect outputs, or write starter scripts |
| `iter` | Inspect and maintain current-format Agent-Ops iteration workspaces through Herdr |
| `reset` | Preview and apply resets of agent customizations and repository `.ai` directories |

---

## `iter`

`iter` supports only the latest Herdr CLI and server; each command validates the live `herdr api snapshot` shape itself. Each maintenance command accepts exactly one targeting mode: an explicit stable `WORKSPACE_ID`, `--all`, or `--interactive`/`-i`. Use `--dry-run`/`-n` to preview `close` or `clean`. The interactive TV picker previews the live status and close plan for `status` and `close`; these commands locate each workspace's exact `.ai/agent-ops/iterations/<slug>/run.json` from Herdr agent cwd ancestry and do not require Git or the caller's cwd. `close` removes only quiet old tabs whose current handoff receipt still matches every stable Herdr identifier. `clean` is records-tree-local because inactive runs no longer exist in Herdr; run it anywhere beneath the project containing the `.ai/agent-ops` tree to clean.

```bash
agents iter status --all
agents iter status -i
agents iter close w1 --dry-run
agents iter close --all --dry-run
agents iter close -i
agents iter clean --all --dry-run
agents iter clean -i -n
```

---

## `reset`

`reset [AGENT]` previews resets of agent customizations and `.ai` workspace directories. `--scope/-s` selects `project/p`, `user/u`, or `all/a` (the default); workspace directories belong to the project scope. Use `--directory/-d` to select the project or directory containing repositories, `--resource workspace` to target `.ai` directories only, and `--recursive/-R` to search nested repositories. `--apply/-a` applies the reset and preserves backups; `--interactive/-i` presents a selection and confirmation flow. `--tui/-t` opens the resource browser and always confirms before applying.

```bash
agents reset --directory ~/code --resource workspace
agents reset --directory ~/code --resource workspace --recursive --apply
```

---

## `doctor`

`doctor [AGENT]` reports agent health and resource provenance. `AGENT` defaults to `all`; use `--directory/-d` to inspect another project and `--resource/-r` to select comma-separated `configuration`, `mcp`, `plugin`, `skill`, or `instructions` resources.

```bash
agents doctor
agents doctor codex --directory . --resource plugin,skill,instructions
```

---

## `second-brain`

`second-brain init` creates `~/code/agents/second-brain` and installs its starter `AGENTS.md` when that file does not already exist. Use `--overwrite` to replace existing instructions. `status` reports activity and invalid updates. `prune` previews invalid CSV rows; `--apply` removes them.

```bash
agents second-brain init
agents second-brain status
agents second-brain prune
agents second-brain prune --apply
```

---

## `parallel`

Current subcommands:

| Command | Behavior |
| --- | --- |
| `create` | Build an agent layout file with prompt/context splitting and output paths |
| `create-context` | Ask one agent to persist a shared `context.md` for a job |
| `run` | Launch a named parallel workflow from `parallel.yaml`, with `create` option overrides |
| `collect` | Concatenate collected agent material files into one output file |
| `create-template` | Write a starter shell/PowerShell script, file list, and prompt file |

`agents parallel create` accepts `--agent`, `--model`, `--reasoning`, `--provider`, `--host`, `--backend`, `--context` or `--context-path`, `--prompt` or `--prompt-path`, `--prompt-name`, `--job-name`, `--agent-load`, `--stagger-max`, `--separator`, `--join-prompt-context`, `--run`, `--agents-dir`, `--output`, `--save-as-yaml`, and `--interactive`. It creates files without launching unless `--run` is set. `--backend` defaults to `tmux`; use `--backend herdr` or `--backend aoe` to choose another launcher. `--save-as-yaml` writes or updates `.stackops/agents/parallel.yaml` using the resolved job name as the top-level entry key, including the chosen launch behavior.

`agents parallel run` reads flat top-level named entries from `parallel.yaml`. It launches when the entry omits `run`; an explicitly saved `run: false` still creates files without launching. By default it searches project YAML files first, then StackOps user and library locations. `--source/-S` accepts `all/a`, `project/p`, `user/u`, or `library/l`. `--custom-path` selects one explicit workflow YAML file and overrides `--source`. Use `--show-format` to print the standard, `--edit` to open the YAML, and `--add-entry` to append a template entry. `--add-entry` defaults to the project file; `--source` or `--custom-path` chooses its target. Workflow fields can be overridden on the command line; `--prompt-path` still supplies the workflow's prompt text file.

Both commands accept `--run/--no-run`, `--interactive/--no-interactive`, and `--join-prompt-context/--no-join-prompt-context` as switches without a `true` or `false` argument. Omitting one of these switches on `parallel run` preserves the YAML setting. Use `--no-run` to create the named workflow's files without launching agents.

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
  run: true
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
agents parallel run default -S project --agent-load 5
agents parallel run docs_update --custom-path ./.ai/parallel.yaml --agent pi --reasoning high
agents parallel run docs_update --add-entry --custom-path ./.ai/parallel.yaml
agents parallel run docs_update --no-run --no-interactive
agents parallel create-context "Collect the repo context for this doc task" updateDocs
agents parallel collect ./.ai/agents/updateDocs ./tmp/materials.txt
```

---

## Prompt-running commands

`run-prompt` is the structured workflow entrypoint. It supports:

- `--agent`
- `--interactive`/`-i` to start the selected agent's native chat with the prepared prompt and continue with follow-up messages
- `--reasoning` for codex, copilot, cortex, and pi agents; unsupported agents ignore it
- `--context` or `--context-path`
- `--custom-path` plus `--context-name` to read one explicit prompts YAML file, overriding `--source`
- `--skill`/`-k` to reference one supported agent skill (same catalog as `agents add-skill`) on the fly: the prompt file tells the agent to read the skill's `SKILL.md` from its source repository and follow it; the skill is never installed. Pass an empty value (`--skill ""`) to pick the skill interactively
- `--source`, `-s` to choose catalog locations for context YAML lookup: `all/a`, `project/p`, `user/u`, or `library/l`
- `--show-format` and `--edit` for prompts-YAML guidance and editing
- free-form prompt parts after `--`; option-looking tokens after the delimiter are prompt text, not StackOps flags

For `run-prompt`, omitting `--agent` uses the configured default agent. `--source project` includes `<git-root>/.stackops/agents/prompts.yaml` when available and also discovers `.stackops/agents/prompts.yaml` in the current directory and its immediate child directories. This discovery also works outside Git repositories. Use `--custom-path` to select exactly one file.
Shell metacharacters such as `|`, `>`, `$`, and `*` are still interpreted by your shell before StackOps receives the prompt.

Interactive mode sends the same prompt, context, and skill reference as the first message, then leaves the agent's chat open. It supports `agy`, `cursor-agent`, `claude`, `qwen`, `copilot`, `codex`, `opencode`, `auggie`, `droid`, `pi`, and `muse`. Other agents report an error before preparing context. Reasoning, Second Brain, and sandbox options still apply; container sandboxes allocate a terminal. Without `--interactive`, the existing prompt-running behavior is unchanged.

Context selection works the same in either mode. Pass `--context ""` to run without context or a YAML picker. Use `agents i` to open an empty chat without preparing a prompt.

Examples:

```bash
agents run-prompt --agent codex --reasoning high --context-path ./context.md "inspect this repo"
agents r -i --context-path ./context.md "inspect this repo"
agents r --interactive --agent copilot --context "" "help me debug this"
agents run-prompt --agent codex --reasoning high --context-path ./context.md -- inspect this repo --include-hidden
agents run-prompt --agent copilot --reasoning high --context-path ./context.md "inspect this repo"
agents run-prompt --agent copilot --context-name docs.cli -s all "update the assigned docs"
agents run-prompt --custom-path ./prompts.yaml --context-name docs.cli "update the assigned docs"
agents run-prompt --agent agy --context-path ./context.md "inspect this repo"
agents run-prompt --agent pi --reasoning high --context-path ./context.md "inspect this repo"
agents run-prompt --agent codex --skill caveman --context-path ./context.md "compress your replies"
agents run-prompt --show-format
```

`run-interactive` launches an agent directly with sensible defaults. Current options:

- `--agent`/`-a` accepts `codex`/`x`, `copilot`/`c`, `cortex`, `pi`/`p`, `opencode`/`oc`, `omp`/`o`, or `deepseek`/`dsh`
- `--caveman`/`-c` starts the session with megacave Wenyan compression
- `--headroom`/`-H` launches `codex` or `copilot` through headroom

Examples:

```bash
agents run-interactive --agent codex
agents run-interactive --agent copilot --caveman
agents run-interactive --agent codex --caveman --headroom
```

`ask` is the lighter-weight direct path. Current behavior to keep in mind:

- omitting `--agent` uses the configured default agent
- `--reasoning` accepts `none`, `low`, `medium`, `high`, `xhigh`, matching `run-prompt` and `parallel`
- reasoning is supported for `codex`, `copilot`, `cortex`, and `pi`; unsupported agents or levels use their default
- prompt tokens are always prompt text; reasoning requires `--reasoning`
- `--prompt-path` appends the file contents into the final prompt with explicit file boundary markers
- `--quiet` skips the Rich preflight summary and streams agent output directly

Examples:

```bash
agents ask --agent codex --reasoning high "inspect the repo"
agents ask --agent copilot --reasoning medium "summarize the current module"
agents ask --agent agy "inspect the repo"
agents ask --agent pi --reasoning high "inspect the repo"
agents ask "summarize this file" --prompt-path ./README.md
agents ask --quiet "summarize the current directory"
```

---

## Repository and MCP helpers

`init` requires an agent argument and copies the latest Agent-Ops skill bundled with StackOps into `.agents/skills/agent-ops` by default. Pass `--no-agent-ops-skill`/`-a` to skip that copy. It can also add private config files, instructions, shared `.ai` assets, VS Code tasks, and `.gitignore` entries. Pass `all` to configure every supported agent, or pass a comma-separated list. Pi and OMP configurations include their native ten-attempt exponential retry policies for transient API failures.

```bash
agents init all --root .
agents init codex,copilot,agy,pi,omp --root . --include-scripts --add-gitignore
agents init codex --root . -a
```

`config path/init/validate` handles StackOps catalogs of kind `prompts`, `parallel`, or `mcp`. `--source/-s` accepts `project/p` (the default), `user/u`, or `library/l`. An explicit `--custom-path/-p` overrides source selection. They do not initialize native agent configuration; use `agents init` for that.

`add-mcp` resolves MCP server names from StackOps catalogs and installs them for one or more agents. Install ordinary skills with `add-skill`. Notes:

- `--scope project` (alias `p`, the default) installs into the enclosing Git repository; when run from a multi-repo workspace root, it installs into that workspace directory. `--scope user` (alias `u`) installs into the user's agent configuration
- `--source`, `-S` selects catalog locations: `all/a`, `project/p`, `user/u`, or `library/l`
- `--custom-path`, `-p` selects one explicit MCP catalog file and overrides `--source`
- `--edit` opens the catalog files and exits immediately if no MCP names were provided
- `copilot` means GitHub Copilot CLI. Project MCP config is written to `.mcp.json`; user MCP config is written to `$COPILOT_HOME/mcp-config.json` when `COPILOT_HOME` is set, otherwise `~/.copilot/mcp-config.json`
- `agy` means Google Antigravity CLI. Project MCP config is written to `.agents/mcp_config.json`; user MCP config is written to `~/.gemini/antigravity-cli/mcp_config.json`
- `oz` means Warp Oz CLI. Project MCP config is written to `.warp/mcp.json` in Oz's direct `--mcp` file shape, and StackOps passes that file to `oz agent run --mcp` when it exists.
- `pi` project MCP config is written to `.pi/mcp.json`; user MCP config is written to `~/.pi/agent/mcp.json`
- `agent-browser`, `agent-skills`, `archify`, `caveman`, `grill-with-docs`, `last30days`, `agent-ops`, and `stackops` are skills/plugins; install them with `add-skill`
- PostgreSQL is available as `postgres`; replace the generated `DATABASE_URI` value before use

For `add-mcp`, `--source project` or `-S p` resolves to `<git-root>/.stackops/mcp.json`. The source selects definitions to read; the scope selects where to install them.

```bash
agents add-mcp --help
agents add-mcp postgres,filesystem --agent codex,copilot,agy,oz,pi --scope project
agents add-mcp filesystem --custom-path ./mcp.json --scope user
agents add-skill caveman --agent codex --scope project
agents add-mcp --edit -S library
```

---

## Browser Automation

`agents browser install` prepares browser automation tooling. The default is the direct `agent-browser` CLI and Vercel skill. `--tool` accepts `agent-browser`, `browser-use`, `pinchtab`, `playwright-cli`, `chrome-devtools-mcp`, `playwright-mcp`, `omp`, or `all`. `browser-use` installs or upgrades the official Python CLI and registers its bundled skill for the selected agent. `pinchtab` installs the current release binary and its official agent skill. `playwright-cli` installs the official Playwright agent CLI and skills. The MCP choices write StackOps guide/config files under `~/code/agents/browser/mcp/...`; install their server entries into an agent with `agents add-mcp`. CDP and extension MCP entries must be paired with browsers launched from StackOps custom profiles. `omp` (Oh My Pi) is an agent with a built-in Puppeteer browser tool; the entry installs it from the installer catalog, writes a guide and a `browser.cdpUrl` config overlay under `~/code/agents/browser/omp/` for attaching to a StackOps CDP endpoint, and does not use `--agent`.

```bash
agents browser install
agents browser install --tool browser-use
agents browser install --tool pinchtab
agents browser install --tool playwright-cli
agents browser install --tool chrome-devtools-mcp
agents browser install --tool playwright-mcp
agents browser install --tool omp
agents add-mcp chrome-devtools --agent codex --scope project
agents add-mcp chrome-devtools-browser-url --agent codex --scope project
agents add-mcp playwright --agent codex --scope project
agents add-mcp playwright-cdp --agent codex --scope project
```

`agents browser launch` launches Chrome, Brave, Edge, Firefox, or Safari automation endpoints. Chromium browsers use CDP with an isolated profile; Firefox uses WebDriver BiDi; Safari uses safaridriver. The default port is `9331`; pass `--port 9222` when using the shipped CDP MCP catalog entries without editing them. Omitting `--profile` uses a port-scoped profile under the system temp directory for profile-capable browsers; a profile name uses `~/data/browsers-profiles/<browser>/<profile>`. Pass `--tmp`/`-t` with `--profile` to copy that profile to `<profile>/.tmp/<random-alias>` and launch the copy. By default, StackOps runs browser endpoints in one `stackops-browser` tmux session with qualified windows such as `chrome-profile-agent-browser-p9331-endpoint`; `--lan`/`-l` adds a matching relay window and exposes the requested port through a StackOps relay on `0.0.0.0`. Pass `--detached`/`-d` to launch background processes instead of tmux windows.

```bash
agents browser launch --browser chrome --port 9331 --profile agent-browser
agents browser launch --browser edge --port 9331 --profile agent-browser
agents browser launch --browser chrome --profile agent-browser --tmp
agents browser launch --browser chrome --port 9222 --profile playwright-mcp
agents browser launch --browser chrome --port 9331 --lan
agents browser launch --browser chrome --port 9331 --profile agent-browser -d
agents browser status
agent-browser connect http://OTHER_COMPUTER_IP:9331
```

`agents browser close` closes StackOps-tracked launches selected in exactly one of two ways: `--port` (default `9331`) closes one endpoint, while `--profile` closes the comma-separated saved profiles under `~/data/browsers-profiles/<browser>/<profile>`, including their `--tmp` copies. `--profile` requires a profile-capable browser, so Safari must use `--port`. Both modes cover tmux and detached launches, leave other ports and profiles, other browsers, and browser sessions not managed by StackOps untouched, and succeed without changing anything when nothing matching is active.

`agents browser batch-launch` launches every saved profile under `~/data/browsers-profiles/<browser>/` for the browser selected with `--browser`. Its `--port-start`/`--port`/`-p` base defaults to `60000`. Profiles named `pN` use `port-start + N`, so `p1` uses `60001`, `p2` uses `60002`, and so on by default. Other profile names use the next unreserved port above the base. Use `--max-profiles`/`--max`/`-n` to cap the launch count; StackOps launches the requested count or the number available, whichever is smaller. The command prints one compact table with each profile, IP, port, state, and tmux window or process ID. It supports the same `--lan` and `--detached` launch modes as `launch`; Safari is excluded because it does not support custom profiles.

`agents browser batch-close` closes every StackOps-tracked launch for a saved profile or one of its `--tmp` copies for the selected browser, including both tmux and detached launches. It leaves port-scoped profiles, other browsers, and browser sessions not managed by StackOps untouched. Running it when no matching launches are active succeeds without changing anything.

```bash
agents browser close --browser chrome --port 9331
agents browser close --browser chrome --profile p1,p2
agents browser batch-launch --browser chrome
agents browser L --browser firefox -n 4 --lan
agents browser batch-launch --browser brave --port-start 61000 --detached
agents browser batch-close --browser brave
```

`agents browser declutter` removes rebuildable data from a named profile (or from every saved profile of the browser with `--all`) after confirming that the selected browser is closed. Chrome, Brave, and Edge cleanup includes downloaded on-device AI models (including `OptGuideOnDeviceModel`) plus HTTP, code, GPU, shader, and extension-download caches. Firefox cleanup includes its disk, startup, and shader caches. Cookies, history, passwords, extensions, sessions, service-worker data, IndexedDB, and local storage are preserved. The command reports the recovered and remaining profile sizes in MiB.

`agents browser replicate --count COUNT` copies a closed source profile to `p1` through `pCOUNT`. Use `--target work,personal` for named destinations instead of a count. Chrome is the default browser and `base` is the default source profile. `--native` copies from a native browser profile. All destination paths are checked before copying; existing copies are refused unless `--overwrite` is passed, which deletes each existing destination completely before recopying. Both profile-maintenance commands use the same `~/data/browsers-profiles/<browser>/<profile>` layout on Windows, macOS, and Linux. They support Chrome, Brave, Edge, and Firefox; Safari is excluded because safaridriver does not support StackOps custom profiles.

```bash
agents browser declutter --profile example-copy
agents browser declutter --browser firefox --all
agents browser replicate --count 4
agents browser replicate --count 3 --browser brave --profile example-copy
agents browser replicate --count 5 --overwrite
```

---

## `add-skill`

`add-skill` uses the StackOps backend by default, copying bundled skills directly into `<repo-root>/.agents/skills/<skill>` for project installs. `--scope` accepts `project/p` (the default) or `user/u`. If the StackOps backend cannot handle the request, it reports the reason and falls back to the existing `bunx skills@latest add` path. Use `--backend bunx` to run the upstream skills CLI directly, or `--backend npx` to run `npx skills@latest add` instead. The shipped source aliases include `agent-browser`, `agent-skills`, `archify`, `caveman`, `grill-with-docs`, `last30days`, `agent-ops`, and `stackops`; omitting the skill name opens the fuzzy picker. Unknown skill names exit with an error instead of searching for alternatives. `--agent` is passed through to the skills CLI without StackOps mapping for `bunx`/`npx`; the StackOps backend installs into the shared project skill directory. `--directory` chooses the install root and defaults to the current directory. Use `agents browser install` for the browser-specific installer and MCP setup notes.

```bash
agents add-skill --scope project
agents add-skill stackops --agent codex --scope project
agents add-skill agent-skills --agent codex --scope user
agents add-skill last30days --agent codex --scope user --backend npx
agents add-skill archify --agent codex --scope user --backend npx
agents add-skill stackops --scope project --backend s
agents add-skill agent-ops --scope project --backend stackops
agents add-skill grill-with-docs --scope project
agents add-skill caveman --agent codex --scope project
agents add-skill caveman --agent github-copilot --scope user
```

---

## Getting help

```bash
agents --help
agents reset --help
agents config --help
agents local doctor --help
agents doctor --help
agents second-brain --help
agents parallel --help
agents init --help
agents add-mcp --help
agents run-prompt --help
agents run-interactive --help
agents ask --help
agents add-skill --help
agents browser install --help
agents browser launch --help
agents browser close --help
agents browser batch-launch --help
agents browser batch-close --help
agents browser declutter --help
agents browser replicate --help
```

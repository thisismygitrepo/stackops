# agents

`agents` manages StackOps's AI-agent scaffolding, prompt execution, and MCP catalog installs.

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
| `config` | Locate, initialize, and validate StackOps prompts and MCP catalogs |
| `browser` | Prepare browser automation tooling, launch supported browser automation endpoints, and manage their profiles |
| `computer` | Serve agent-desktop desktop control as a localhost MCP endpoint and report its status |
| `second-brain` | Install the Second Brain instructions, append updates, and report or prune its records |
| `doctor` | Inspect agent binaries, configuration, hooks, plugins, skills, and instruction provenance |
| `status` | Inspect live TUIOS, Herdr, or AoE agents, or T3 Code threads, with location and agent-session filters |
| `local` | Inspect, discover, install, and serve local models through Ollama and vLLM |
| `run-prompt` | Run a prompt through a selected agent, with context and an optional interactive session |
| `run-interactive` | Launch an agent with reasonable defaults |
| `ask` | Ask a selected agent directly |
| `iter` | Inspect and maintain current-format Agent-Ops iteration workspaces through Herdr |
| `reset` | Preview and apply resets of agent customizations and repository `.ai` directories |

`agents --non-interactive` / `-N` (or the `STACKOPS_NON_INTERACTIVE` environment variable) never prompts or opens a picker or editor; it is also enabled automatically without a terminal.

---

## `status`

`agents status` collects reported agent states, read-only terminal evidence, and available retained history. Select `--backend tuios`, `herdr`, `aoe`, or `t3`; omitted, it uses `default_agent_multiplexer` from the StackOps config, else `tuios`. Detached live sessions are included; saved or stopped sessions are not restored. AoE inspection covers its current profile. `t3` reads unsettled threads on the local T3 Code server; it has no sessions, layouts, tabs, or panes, so the location filters below and `--server` are rejected with it.

Location filters follow the [terminal layout convention](terminal.md#layout-file-format):

| Filter | TUIOS | Herdr | AoE |
| --- | --- | --- | --- |
| `--session` / `-s` | Native session name or ID | Native session name | Agent session title or ID |
| `--layout` / `-l` | Session name or ID | Workspace label, ID, or number | Full group path |
| `--tab` / `-t` | Workspace name or number | Tab label or ID | Agent session title or ID |
| `--pane` / `-p` | Window name or ID | Pane label, title, or ID | Agent session title or ID |

`--pane` always selects the leaf target. For AoE, this target can be a tmux pane or a structured worker without a terminal pane. `--exclude-pane` / `-x` omits matching leaf targets.

`--agent-session` / `-A` matches the registered agent name in TUIOS (also its pane name), the agent name in Herdr (separate from the pane label), or the session title/ID in AoE. It also matches a linked harness conversation ID when available; it does not search transcript titles. Missing identity metadata does not match. Reports show the available agent name and conversation ID. Other filters include `--harness` / `-a` and `--state` / `-S` (`working`, `waiting`, `blocked`, `idle`, `completed`, `failed`, `unknown`, or `unavailable`).

Names and IDs match exactly and case-sensitively. Repeat an option to match any of its values; combine different filters to require all of them. Duplicate names select every match in the chosen scope. Use the containing session, layout, and tab, or stable IDs, to narrow it down. For example, a Herdr pane named `worker` in two tabs can be selected with both `--tab review` and `--pane worker`. Unknown layout, tab, or pane selectors report an error in the selected scope; an unmatched agent-session filter shows no agents.

`--format` / `-f` selects `table` (the default), `rich`, `json`, or `markdown`; `--json` / `-j` is shorthand for `--format json`. `--output` / `-o` writes the report to a file instead of stdout, and replacing an existing file needs `--force` / `-F`. `--btw` / `-w` also asks each shown agent two side questions, its status and what it is working on, in a fork that leaves its main conversation untouched; harnesses without fork support, or agents without a linked conversation, report the side question as unavailable.

```bash
agents status --backend herdr --session dev --layout project --tab review --pane worker
agents status --backend tuios --layout project --tab review --pane worker
agents status --backend aoe --layout project/review --tab reviewer
agents status --backend herdr --agent-session reviewer --agent-session implementer
agents status --backend herdr --layout project --exclude-pane observer --json
agents status --backend t3 --state working --format markdown --output status.md
```

---

## `iter`

`iter` supports only the latest Herdr CLI and server; each command validates the live `herdr api snapshot` shape itself. Each maintenance command accepts exactly one targeting mode: an explicit stable `WORKSPACE_ID`, `--all`, or `--interactive`/`-i`. Use `--dry-run`/`-n` to preview `close` or `clean`. `close` and `status` take `--retain-previous`/`-k` (default `3`) to keep the latest iteration plus that many previous ones; `close --loop`/`-l` repeats close passes every `--interval`/`-I` seconds (default `300`) until interrupted. All three commands accept `--json`/`-j`, which cannot be combined with `--interactive`. The interactive TV picker previews the live status and close plan for `status` and `close`; these commands locate each workspace's exact `.ai/agent-ops/iterations/<slug>/run.json` from Herdr agent cwd ancestry and do not require Git or the caller's cwd. `close` removes only quiet old tabs whose current handoff receipt still matches every stable Herdr identifier. `clean` is records-tree-local because inactive runs no longer exist in Herdr; run it anywhere beneath the project containing the `.ai/agent-ops` tree to clean.

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

`reset [AGENT]` previews resets of agent customizations and `.ai` workspace directories. `--scope/-s` selects `workspace/w`, `user/u`, or `all/a` (the default); `.ai` directories belong to the workspace scope. Use `--directory/-d` to select the workspace or directory containing repositories, `--resource/-r` to pick comma-separated `all`, `workspace`, `hook`, `plugin`, `mcp`, `skill`, `instructions`, or `configuration` resources (`--resource workspace` targets `.ai` directories only), `--match/-m` to narrow resources by name, command, or source path substring, and `--recursive/-R` to search nested repositories. `--apply/-a` permanently applies the reset without keeping a backup. `--interactive/-i` presents a selection and confirmation flow. `--tui/-t` opens the resource browser and always confirms before applying. `--verbose/-v` shows path sizes and every resource, `--json/-j` prints the plan and any applied result as JSON, and `--as-html/-w` writes a navigable HTML preview and opens it in the browser without applying anything.

```bash
agents reset --directory ~/code --resource workspace
agents reset --directory ~/code --resource workspace --recursive --apply
```

---

## `doctor`

`doctor [AGENT]` reports agent health and resource provenance. `AGENT` defaults to `all`; use `--directory/-d` to inspect another project and `--resource/-r` to select comma-separated `all` (the default), `configuration`, `mcp`, `hook`, `plugin`, `skill`, or `instructions` resources. `--tui/-t` browses the results in a terminal app, `--json/-j` prints them as JSON, and `--as-html/-w` writes a navigable HTML report and opens it in the browser; these three are mutually exclusive.

```bash
agents doctor
agents doctor codex --directory . --resource plugin,skill,instructions
agents doctor --json
```

---

## `second-brain`

`second-brain init` creates `~/code/agents/second-brain` and installs its starter `AGENTS.md` when that file does not already exist. Use `--overwrite` to replace existing instructions. `append DIRECTORY AGENT SESSION_ID TOPIC ACTIONS_TAKEN UPDATED_ON` appends one update to `update.csv` in the work-item directory, creating the file with its header if needed. `status` reports activity and invalid updates. `prune` previews invalid CSV rows; `--apply` removes them. `status` and `prune` accept `--json`/`-j`.

```bash
agents second-brain init
agents second-brain status
agents second-brain prune
agents second-brain prune --apply
```

---

## Prompt-running commands

`run-prompt` is the structured workflow entrypoint. It supports:

- `--agent`/`-a`
- `--interactive`/`-i` to start the selected agent's native chat with the prepared prompt and continue with follow-up messages
- `--non-interactive`/`-B` to never open a picker or editor: missing context is empty and unknown context names fail. It is automatic without a terminal and cannot be combined with `--interactive` or `--edit`
- `--reasoning`/`-r` (`none`, `low`, `medium`, `high`, `xhigh`) for codex, copilot, cortex, pi, muse, and prime-agent agents; unsupported agents ignore it
- `--context`/`-c` or `--context-path`/`-C`
- `--custom-path`/`-y` plus `--context-name`/`-n` to read one explicit prompts YAML file, overriding `--source`
- `--group`/`-g` to select only YAML prompts whose group matches exactly
- `--skill`/`-k` to reference one supported agent skill (same catalog as `agents add-skill`) on the fly: the prompt file tells the agent to read the skill's `SKILL.md` from its source repository and follow it; the skill is never installed. Pass an empty value (`--skill ""`) to pick the skill interactively
- `--source`, `-s` to choose catalog locations for context YAML lookup: `all/a` (the default), `workspace/w`, `user/u`, or `library/l`
- `--show-format`/`-Y` and `--edit`/`-e` for prompts-YAML guidance and editing
- `--list`/`-l` to list the saved prompts without running an agent, honoring `--source`, `--custom-path`, and `--group`; `--json`/`-j` prints that catalog as JSON
- `--t3`/`-t` to launch the prompt as a T3 Code thread instead of running the agent here; it requires `--model`/`-m` and cannot be combined with `--interactive` or `--sandbox`
- `--second-brain`/`-b` to run from the Second Brain repository
- `--sandbox`/`-S` (`none`, `docker`, `podman`, `bwrap`, `srt`, `ai-jail`, or `openshell`); `docker`, `podman`, and `openshell` require `--sandbox-image`/`-I`, and `srt` requires `--sandbox-settings`/`-J`
- free-form prompt parts after `--`; option-looking tokens after the delimiter are prompt text, not StackOps flags

For `run-prompt`, omitting `--agent` uses `default_agent` from the StackOps config, else `codex`. `--source workspace` selects `<workspace-root>/.stackops/agents/prompts.yaml`. The workspace root is the enclosing Git repository root, or the current directory when it contains at least two immediate child Git repositories. It also reads `.stackops/agents/prompts.yaml` from each immediate child directory of the root that has one, labelled `workspace:<child>`; templates are only created at the root. Selecting `workspace` requires one of these roots, while `all` includes the workspace file when a root is available, followed by user and library files. Use `--custom-path` to select an explicit file in any directory.
Shell metacharacters such as `|`, `>`, `$`, and `*` are still interpreted by your shell before StackOps receives the prompt.

Interactive mode sends the same prompt, context, and skill reference as the first message, then leaves the agent's chat open. It supports `agy`, `cursor-agent`, `claude`, `qwen`, `copilot`, `codex`, `cortex`, `opencode`, `auggie`, `droid`, `pi`, `muse`, `maki`, and `prime-agent`. Other agents report an error before preparing context. Reasoning, Second Brain, and sandbox options still apply; `docker`, `podman`, and `openshell` sandboxes allocate a terminal. Without `--interactive`, the existing prompt-running behavior is unchanged.

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

`run-interactive` launches an agent directly with sensible defaults. Optional positional text is passed to the agent as its initial prompt; use `--` before text that looks like an option. Current options:

- `--agent`/`-a` accepts `codex`/`x`, `copilot`/`c`, `cortex`, `pi`/`p`, `opencode`/`oc`, `omp`/`o`, `maki`, `prime-agent`/`pa`, or `deepseek`/`dsh`; omitted, it uses `default_agent` from the StackOps config, else `codex`, and fails when that default is not one of these
- `--caveman`/`-c` starts the session with megacave Wenyan compression, ahead of any prompt text
- `--headroom`/`-H` launches `codex` or `copilot` through headroom
- `--followup`/`-f` chooses a session recorded in Second Brain `update.csv` files and resumes it; add `--fork`/`-F` to fork it into a new session instead
- `--second-brain`/`-b` runs from the Second Brain repository
- `--sandbox`/`-S` and the other `--sandbox-*` options select a sandbox provider, as in `run-prompt`

Examples:

```bash
agents run-interactive --agent codex
agents run-interactive --agent copilot --caveman
agents run-interactive --agent codex --caveman --headroom
agents run-interactive --agent codex "review the failing tests"
agents run-interactive --agent copilot --caveman -- "--help output is wrong"
```

`deepseek` opens a web interface and cannot take an initial prompt, so passing prompt text or `--caveman` with it is rejected.

`ask` is the lighter-weight direct path. Current behavior to keep in mind:

- omitting `--agent` uses `default_agent` from the StackOps config, else `codex`
- `--reasoning`/`-r` accepts `none`, `low`, `medium`, `high`, `xhigh`, matching `run-prompt`
- reasoning is supported for `codex`, `copilot`, `cortex`, `pi`, `muse`, and `prime-agent`; unsupported agents or levels use their default
- prompt tokens are always prompt text; reasoning requires `--reasoning`
- `--prompt-path`/`-f` appends the file contents into the final prompt with explicit file boundary markers
- `--quiet`/`-q` skips the Rich preflight summary and streams agent output directly
- `--second-brain`/`-b` runs from the Second Brain repository

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

`init` requires an agent argument and copies the latest Agent-Ops skill bundled with StackOps into `.agents/skills/agent-ops` by default. Pass `--no-agent-ops-skill`/`-a` to skip that copy. It also adds private config files and instructions unless `--no-add-config`/`-c` or `--no-add-instructions`/`-i` is passed; `--include-scripts`/`-s`, `--add-vscode-tasks`/`-l`, and `--add-gitignore`/`-g` add the shared `.ai` scaffold, the VS Code lint/type-check task, and `.gitignore` entries. `--root`/`-R` selects the repository and defaults to the current directory. Pass `all` to configure every supported agent, or pass a comma-separated list. A newly created `.pi/settings.json` or `.omp/config.yml` enables the agent's native retry for transient API failures with `maxRetries: 10` and a base delay of 2 s (Pi) or 0.5 s (OMP); an existing file keeps its own retry settings.

```bash
agents init all --root .
agents init codex,copilot,agy,pi,omp --root . --include-scripts --add-gitignore
agents init codex --root . -a
```

`config path/init/validate` handles StackOps catalogs of kind `prompts` or `mcp`. `--source/-s` accepts `workspace/w` (the default), `user/u`, or `library/l`. Workspace files use the same root resolution as `run-prompt`: `.stackops/agents/prompts.yaml` or `.stackops/mcp.json` under that root. An explicit `--custom-path/-p` overrides source selection. They do not initialize native agent configuration; use `agents init` for that.

`add-mcp` resolves MCP server names from StackOps catalogs and installs them for one or more agents. Install ordinary skills with `add-skill`. Notes:

- `--scope workspace` (alias `w`, the default) installs into the enclosing Git repository root, or the current directory when it contains at least two immediate child Git repositories. `--scope user` (alias `u`) installs into the user's agent configuration
- `--source`, `-S` selects catalog locations: `all/a` (the default), `workspace/w`, `user/u`, or `library/l`
- `--custom-path`, `-p` selects one explicit MCP catalog file and overrides `--source`
- `--agent`, `-a` takes comma-separated agents; omitted, it configures every agent that supports the selected scope
- `--edit`, `-e` opens the catalog files and exits immediately if no MCP names were provided
- `--list`, `-l` prints the available catalog names without installing; `--json`, `-j` prints that list as JSON
- `copilot` means GitHub Copilot CLI. Workspace MCP config is written to `.mcp.json`; user MCP config is written to `$COPILOT_HOME/mcp-config.json` when `COPILOT_HOME` is set, otherwise `~/.copilot/mcp-config.json`
- `agy` means Google Antigravity CLI. Workspace MCP config is written to `.agents/mcp_config.json`; user MCP config is written to `~/.gemini/antigravity-cli/mcp_config.json`
- `oz` means Warp Oz CLI. Workspace MCP config is written to `.warp/mcp.json` in Oz's direct `--mcp` file shape, and StackOps passes that file to `oz agent run --mcp` when it exists.
- `pi` workspace MCP config is written to `.pi/mcp.json`; user MCP config is written to `~/.pi/agent/mcp.json`
- `agent-browser`, `agent-skills`, `archify`, `caveman`, `grill-with-docs`, `last30days`, `agent-ops`, and `stackops` are skills/plugins; install them with `add-skill`
- PostgreSQL is available as `postgres`; replace the generated `DATABASE_URI` value before use

For `add-mcp`, `--source workspace` or `-S w` resolves to `<workspace-root>/.stackops/mcp.json` and `.stackops/mcp.json` in each immediate child directory of the root that has one, labelled `workspace:<child>`, using the same root resolution as the workspace install scope. The source selects definitions to read; the scope selects where to install them.

```bash
agents add-mcp --help
agents add-mcp --list -S library
agents add-mcp postgres,playwright --agent codex,copilot,agy,oz,pi --scope workspace
agents add-mcp filesystem --custom-path ./mcp.json --scope user
agents add-skill caveman --agent codex --scope workspace
agents add-mcp --edit -S library
```

---

## Browser Automation

`agents browser install` prepares browser automation tooling. The default is the direct `agent-browser` CLI and Vercel skill. `--agent`/`-a` names the agent that receives the skill or MCP guidance and is chosen interactively when omitted; `--backend`/`-b` picks the upstream skills CLI runner, `npx` (the default) or `bunx`, used by `agent-browser` and `pinchtab`. `--tool`/`-w` accepts `agent-browser`, `browser-use`, `pinchtab`, `playwright-cli`, `chrome-devtools-mcp`, `playwright-mcp`, `omp`, or `all`. `browser-use` installs or upgrades the official Python CLI and registers its bundled skill for the selected agent. `pinchtab` installs the current release binary and its official agent skill. `playwright-cli` installs the official Playwright agent CLI and skills. The MCP choices write StackOps guide/config files under `~/code/agents/browser/mcp/...`; install their server entries into an agent with `agents add-mcp`. CDP and extension MCP entries must be paired with browsers launched from StackOps custom profiles. `omp` (Oh My Pi) is an agent with a built-in Puppeteer browser tool; the entry installs it from the installer catalog, writes a guide and a `browser.cdpUrl` config overlay under `~/code/agents/browser/omp/` for attaching to a StackOps CDP endpoint, and does not use `--agent`.

```bash
agents browser install
agents browser install --tool browser-use
agents browser install --tool pinchtab
agents browser install --tool playwright-cli
agents browser install --tool chrome-devtools-mcp
agents browser install --tool playwright-mcp
agents browser install --tool omp
agents add-mcp chrome-devtools --agent codex --scope workspace
agents add-mcp chrome-devtools-browser-url --agent codex --scope workspace
agents add-mcp playwright --agent codex --scope workspace
agents add-mcp playwright-cdp --agent codex --scope workspace
```

`agents browser launch` launches Chrome, Brave, Edge, Firefox, or Safari automation endpoints. Chromium browsers use CDP with an isolated profile; Firefox uses WebDriver BiDi; Safari uses safaridriver. The default port is `9331`; pass `--port 9222` when using the shipped CDP MCP catalog entries without editing them. Omitting `--profile` uses a port-scoped profile under the system temp directory for profile-capable browsers; a profile name uses `~/data/browsers-profiles/<browser>/<profile>`. `--profile`/`-r` accepts comma-separated names: each profile gets its own endpoint on consecutive ports starting at `--port`. Pass `--tmp`/`-t` with `--profile` to copy that profile to `<profile>/.tmp/<random-alias>` and launch the copy. `--runtime`/`-m` selects where the browser processes run: `tmux`/`t`, `tuios`/`u`, `zellij`/`z`, or `detached`/`d` background processes; omitted, it uses `default_session_multiplexer` from the StackOps config, else `tmux`, and a configured `herdr` or `aoe` requires an explicit `--runtime`. Multiplexer runtimes keep browser endpoints in one `stackops-browser` session with qualified windows (panes in Zellij) such as `chrome-profile-agent-browser-<digest>-p9331-endpoint`; `--lan`/`-l` adds a matching relay window and exposes the requested port through a StackOps relay on `0.0.0.0`. `--attach`/`-a` attaches to the launched browser window (not with `--runtime detached`), `--new-window`/`-w` claims a browser window per endpoint (not Safari) and reports its id and tabs, and `--json`/`-j` prints the endpoint and launch records as JSON.

```bash
agents browser launch --browser chrome --port 9331 --profile agent-browser
agents browser launch --browser edge --port 9331 --profile agent-browser
agents browser launch --browser chrome --profile agent-browser --tmp
agents browser launch --browser chrome --port 9222 --profile playwright-mcp
agents browser launch --browser chrome --port 9331 --lan
agents browser launch --browser chrome --port 9331 --profile agent-browser --runtime detached
agents browser launch --browser chrome --port 9331 --profile work,personal
agents browser status
agent-browser connect http://OTHER_COMPUTER_IP:9331
```

`agents browser status` shows StackOps-tracked launches across the tmux, TUIOS, Zellij, and detached runtimes. `--all`/`-a` shows every open browser instead, `--browser`/`-b` limits the report to one browser, `--tabs`/`-t` also lists the title and URL of every open tab, `--focus`/`-f` picks one open tab interactively and brings its window to the front, and `--json`/`-j` prints the records as JSON.

`agents browser close` closes StackOps-tracked launches selected in exactly one of two ways: `--port` (default `9331`) closes one endpoint, while `--profile` closes the comma-separated saved profiles under `~/data/browsers-profiles/<browser>/<profile>`, including their `--tmp` copies. `--profile` requires a profile-capable browser, so Safari must use `--port`. Both modes cover multiplexer and detached launches, leave other ports and profiles, other browsers, and browser sessions not managed by StackOps untouched, and succeed without changing anything when nothing matching is active. `--window`/`-w` instead closes only one browser window id (as shown by `status`) on the `--port` endpoint and keeps the browser and its other windows running; it cannot be combined with `--profile`.

`agents browser batch-launch` launches every saved profile under `~/data/browsers-profiles/<browser>/` for the browser selected with `--browser`. Its `--port-start`/`--port`/`-p` base defaults to `60000`. Profiles named `pN` use `port-start + N`, so `p1` uses `60001`, `p2` uses `60002`, and so on by default. Other profile names use the next unreserved port above the base. Use `--max-profiles`/`--max`/`-n` to cap the launch count; StackOps launches the requested count or the number available, whichever is smaller. The command prints one compact table with each profile, IP, port, state, and multiplexer window or process ID. It supports the same `--lan`, `--runtime`, `--attach`, and `--json` options as `launch`; Safari is excluded because it does not support custom profiles.

`agents browser batch-close` closes every StackOps-tracked launch for a saved profile or one of its `--tmp` copies for the selected browser, including both multiplexer and detached launches. It leaves port-scoped profiles, other browsers, and browser sessions not managed by StackOps untouched. Running it when no matching launches are active succeeds without changing anything.

```bash
agents browser close --browser chrome --port 9331
agents browser close --browser chrome --profile p1,p2
agents browser batch-launch --browser chrome
agents browser L --browser firefox -n 4 --lan
agents browser batch-launch --browser brave --port-start 61000 --runtime detached
agents browser batch-close --browser brave
```

`agents browser profiles [SITES]...` lists a Chromium-family browser's saved StackOps profiles (`--browser`/`-b`: `chrome`, `brave`, or `edge`) with their state, browser account, and what each is signed in to; `--native`/`-n` lists the browser's own profiles instead and `--json`/`-j` prints the rows as JSON. Each `SITES` value is matched as a case-insensitive part of the cookie host. Only profile files are read; cookie values and passwords are never read or decrypted.

`agents browser declutter` removes rebuildable data from a named profile (or from every saved profile of the browser with `--all`) after confirming that the selected browser is closed. Chrome, Brave, and Edge cleanup includes downloaded on-device AI models (including `OptGuideOnDeviceModel`) plus HTTP, media, image, code, GPU, shader, and component- and extension-download caches. Firefox cleanup includes its disk, startup, and shader caches. Cookies, history, passwords, extensions, sessions, service-worker data, IndexedDB, and local storage are preserved. The command reports the recovered and remaining profile sizes in MiB.

`agents browser replicate --count COUNT` copies a closed source profile to `p1` through `pCOUNT`. Use `--target work,personal` for named destinations instead of a count. Chrome is the default browser and `base` is the default source profile. `--native` copies from a native browser profile. All destination paths are checked before copying; existing copies are refused unless `--overwrite` is passed, which deletes each existing destination completely before recopying. Both profile-maintenance commands use the same `~/data/browsers-profiles/<browser>/<profile>` layout on Windows, macOS, and Linux. They support Chrome, Brave, Edge, and Firefox; Safari is excluded because safaridriver does not support StackOps custom profiles.

```bash
agents browser declutter --profile example-copy
agents browser declutter --browser firefox --all
agents browser replicate --count 4
agents browser replicate --count 3 --browser brave --profile example-copy
agents browser replicate --count 5 --overwrite
```

---

## Desktop control

`agents computer control` serves agent-desktop desktop control as a localhost MCP endpoint until interrupted: streamable HTTP at `/mcp` and SSE at `/sse` on `--port`/`-p` (default `8096`). `--headless`/`-H` restricts agent-desktop to semantic accessibility actions; without it, physical mouse and keyboard input is allowed. `agents computer status` shows the endpoint state and agent-desktop permissions for the same port, with `--json`/`-j` for JSON output. The `agent-desktop` command must be on `PATH`, and the shipped `agent-desktop` MCP catalog entry points at the default endpoint.

```bash
agents computer control
agents computer control --port 8096 --headless
agents computer status
agents add-mcp agent-desktop --agent codex --scope workspace
```

---

## Local models

`agents local doctor` inspects server health, models, and resource usage for `--backend ollama` (the default) or `vllm`; `--host`/`-H` defaults to `OLLAMA_HOST` or `VLLM_BASE_URL`, then the backend's local address. `agents local discover [QUERY]` lists models from the Ollama catalog, or Hugging Face models for vLLM, within an advertised parameter count range (`--min-params`/`-l` and `--max-params`/`-m`, in billions, defaulting to `20` and `32`). `agents local install` installs vLLM for Linux CUDA with uv, or vLLM Metal for Apple Silicon with Homebrew. `agents local serve MODEL` starts a vLLM server in the foreground on `--host`/`-H` (default `127.0.0.1`) and `--port`/`-p` (default `8000`); additional vLLM options go after `--`. `doctor` and `discover` accept `--json`/`-j`.

```bash
agents local doctor
agents local doctor --backend vllm
agents local discover --backend vllm --sort trending
agents local serve MODEL_ID --port 8000
```

---

## `add-skill`

`add-skill` uses the StackOps backend by default, copying bundled skills directly into `<install-root>/.agents/skills/<skill>` for workspace installs. `--scope` accepts `workspace/w` (the default) or `user/u`. `--directory` selects a directory and defaults to the current directory. The StackOps backend uses its enclosing Git repository root when available; otherwise it installs into the selected directory, without requiring child Git repositories. If the StackOps backend cannot handle the request, it reports the reason and falls back to the existing `bunx skills@latest add` path. Use `--backend bunx` to run the upstream skills CLI directly, or `--backend npx` to run `npx skills@latest add` instead. These backends run from the selected directory. The shipped source aliases include `agent-browser`, `agent-skills`, `archify`, `caveman`, `grill-with-docs`, `last30days`, `agent-ops`, and `stackops`; `--list`/`-l` prints the full catalog (`--json`/`-j` as JSON). Several names can be passed comma-separated, and omitting the skill name opens an interactive `group:name` multi-select picker. `--group`/`-g` filters the picker, the list, and the reference by exact group; `--reference`/`-r` writes a Markdown table of the supported skills into the selected directory instead of installing; `--yes`/`-y` passes `--yes` to the upstream skills CLI. Unknown skill names exit with an error instead of searching for alternatives. `--agent` is passed through to the skills CLI without StackOps mapping for `bunx`/`npx`; the StackOps backend installs into the shared workspace skill directory. Use `agents browser install` for the browser-specific installer and MCP setup notes.

```bash
agents add-skill --list
agents add-skill --scope workspace
agents add-skill stackops --agent codex --scope workspace
agents add-skill agent-skills --agent codex --scope user
agents add-skill last30days --agent codex --scope user --backend npx
agents add-skill archify --agent codex --scope user --backend npx
agents add-skill stackops --scope workspace --backend s
agents add-skill agent-ops --scope workspace --backend stackops
agents add-skill grill-with-docs --scope workspace
agents add-skill caveman --agent codex --scope workspace
agents add-skill caveman --agent github-copilot --scope user
```

---

## Getting help

```bash
agents --help
agents status --help
agents iter --help
agents reset --help
agents config --help
agents local --help
agents local doctor --help
agents computer --help
agents doctor --help
agents second-brain --help
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
agents browser status --help
agents browser profiles --help
agents browser declutter --help
agents browser replicate --help
```

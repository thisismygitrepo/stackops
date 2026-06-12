# StackOps Source Map

Regenerated from `src/stackops/scripts/python/graph/cli_graph.json` on 2026-06-12.

Use this map to jump from a command path to the file that registers or implements it. For signatures, options, aliases, and full node metadata, inspect `src/stackops/scripts/python/graph/cli_graph.json`.

## Root Entrypoints

- Umbrella entrypoint: `src/stackops/scripts/python/stackops_entry.py`
- `devops` -> `src/stackops/scripts/python/stackops_entry.py` -> `stackops.scripts.python.devops.get_app` via `devops`
- `cloud` -> `src/stackops/scripts/python/stackops_entry.py` -> `stackops.scripts.python.cloud.get_app` via `cloud`
- `terminal` -> `src/stackops/scripts/python/stackops_entry.py` -> `stackops.scripts.python.terminal.get_app` via `terminal`
- `agents` -> `src/stackops/scripts/python/stackops_entry.py` -> `stackops.scripts.python.agents.get_app` via `agents`
- `utils` -> `src/stackops/scripts/python/stackops_entry.py` -> `stackops.scripts.python.utils.get_app` via `utils`
- `seek` -> `src/stackops/scripts/python/stackops_entry.py` -> `stackops.scripts.python.seek.get_app` via `seek`
- `fire` -> `src/stackops/scripts/python/stackops_entry.py` -> `fire`
- `preview` -> `src/stackops/scripts/python/stackops_entry.py` -> `preview`

## Group Routes

- `devops` -> `src/stackops/scripts/python/stackops_entry.py` -> `stackops.scripts.python.devops.get_app` via `devops`
- `devops data` -> `src/stackops/scripts/python/devops.py` -> `stackops.scripts.python.helpers.helpers_devops.cli_data.get_app` via `data`
- `devops repos` -> `src/stackops/scripts/python/devops.py` -> `stackops.scripts.python.helpers.helpers_devops.cli_repos.get_app` via `repos`
- `devops config` -> `src/stackops/scripts/python/devops.py` -> `stackops.scripts.python.helpers.helpers_devops.cli_config.get_app` via `config`
- `devops config terminal` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_config.py` -> `stackops.scripts.python.helpers.helpers_devops.cli_config_terminal.get_app` via `terminal`
- `devops config terminal tmux-style` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_config_terminal.py` -> `stackops.scripts.python.helpers.helpers_devops.cli_config_tmux.get_app` via `tmux-style`
- `devops config secrets` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_config.py` -> `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets.get_app` via `secrets`
- `devops vault` -> `src/stackops/scripts/python/devops.py` -> `stackops.scripts.python.helpers.helpers_devops.cli_vault.get_app` via `vault`
- `devops network` -> `src/stackops/scripts/python/devops.py` -> `stackops.scripts.python.helpers.helpers_devops.cli_nw.get_app` via `network`
- `devops network ssh` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_nw.py` -> `stackops.scripts.python.helpers.helpers_devops.cli_ssh.get_app` via `ssh`
- `devops network device` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_nw.py` -> `stackops.scripts.python.helpers.helpers_devops.cli_device.get_app` via `device`
- `devops self` -> `src/stackops/scripts/python/devops.py` -> `stackops.scripts.python.helpers.helpers_devops.cli_self.get_app` via `self`
- `devops self security` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_self.py` -> `stackops.jobs.installer.checks.security_cli.get_app` via `security`
- `devops self explore` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_self.py` -> `stackops.scripts.python.graph.visualize.cli_graph_app.get_app` via `explore`
- `devops self build-assets` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_self.py` -> `stackops.scripts.python.helpers.helpers_devops.cli_self_assets.get_app` via `build-assets`
- `devops self workflows` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_self.py` -> `stackops.scripts.python.helpers.helpers_devops.cli_self_ai.app.get_app` via `workflows`
- `cloud` -> `src/stackops/scripts/python/stackops_entry.py` -> `stackops.scripts.python.cloud.get_app` via `cloud`
- `terminal` -> `src/stackops/scripts/python/stackops_entry.py` -> `stackops.scripts.python.terminal.get_app` via `terminal`
- `agents` -> `src/stackops/scripts/python/stackops_entry.py` -> `stackops.scripts.python.agents.get_app` via `agents`
- `agents parallel` -> `src/stackops/scripts/python/agents.py` -> `stackops.scripts.python.agents_parallel.get_app` via `parallel`
- `agents browser` -> `src/stackops/scripts/python/agents.py` -> `stackops.scripts.python.agents_browser.get_app` via `browser`
- `utils` -> `src/stackops/scripts/python/stackops_entry.py` -> `stackops.scripts.python.utils.get_app` via `utils`
- `utils machine` -> `src/stackops/scripts/python/utils.py` -> `stackops.scripts.python.helpers.helpers_utils.machine_utils_app.get_app` via `machine`
- `utils pyproject` -> `src/stackops/scripts/python/utils.py` -> `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_app.get_app` via `pyproject`
- `utils pyproject type-fix` -> `src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_app.py` -> `stackops.scripts.python.agents_type_fix.get_app` via `type-fix`
- `utils pyproject test-runtime` -> `src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_app.py` -> `stackops.scripts.python.agents_test_runtime.get_app` via `test-runtime`
- `utils file` -> `src/stackops/scripts/python/utils.py` -> `stackops.scripts.python.helpers.helpers_utils.file_utils_app.get_app` via `file`
- `seek` -> `src/stackops/scripts/python/stackops_entry.py` -> `stackops.scripts.python.seek.get_app` via `seek`

## Command Implementations

- `devops install` -> `src/stackops/scripts/python/devops.py` -> `install`
- `devops data sync` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_data.py` -> `sync`
- `devops data register` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_data.py` -> `register_data`
- `devops data edit` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_data.py` -> `edit_data`
- `devops repos sync` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_repos.py` -> `clone`
- `devops repos register` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_repos.py` -> `capture`
- `devops repos action` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_repos.py` -> `action`
- `devops repos analyze` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_repos.py` -> `analyze_repo_development`
- `devops repos guard` -> `src/stackops/scripts/python/helpers/helpers_repos/cloud_repo_sync.py` -> `main`
- `devops repos viz` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_repos.py` -> `gource_viz`
- `devops repos count-lines` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_repos.py` -> `count_lines_in_repo`
- `devops repos config-linters` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_repos.py` -> `config_linters`
- `devops repos cleanup` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_repos.py` -> `cleanup`
- `devops config sync` -> `src/stackops/profile/create_links_export.py` -> `main_from_parser`
- `devops config register` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_config_dotfile_mapper.py` -> `register_dotfile`
- `devops config edit` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_config_dotfile_mapper.py` -> `edit_dotfile`
- `devops config export-dotfiles` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_config_dotfile_transfer.py` -> `export_dotfiles`
- `devops config import-dotfiles` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_config_dotfile_transfer.py` -> `import_dotfiles`
- `devops config terminal config-shell` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_config_terminal.py` -> `configure_shell_profile`
- `devops config terminal starship-theme` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_config_terminal.py` -> `starship_theme`
- `devops config terminal pwsh-theme` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_config_terminal.py` -> `pwsh_theme`
- `devops config terminal wezterm-theme` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_config_terminal.py` -> `configure_wezterm_theme`
- `devops config terminal ghostty-theme` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_config_terminal.py` -> `configure_ghostty_theme`
- `devops config terminal windows-terminal-theme` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_config_terminal.py` -> `configure_windows_terminal_theme`
- `devops config terminal tmux-style install-oh-my-tmux` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_config_tmux.py` -> `install_oh_my_tmux`
- `devops config terminal tmux-style apply-stackops-local` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_config_tmux.py` -> `apply_stackops_local`
- `devops config terminal tmux-style preset` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_config_tmux.py` -> `preset`
- `devops config terminal tmux-style set-option` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_config_tmux.py` -> `set_option`
- `devops config terminal tmux-style reload` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_config_tmux.py` -> `reload_tmux`
- `devops config terminal tmux-style status` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_config_tmux.py` -> `status`
- `devops config interactive` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_config.py` -> `config`
- `devops config copy-assets` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_config.py` -> `copy_assets`
- `devops config secrets search` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets.py` -> `search`
- `devops config secrets stats` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets.py` -> `stats`
- `devops config secrets subset` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets.py` -> `subset`
- `devops config secrets add` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets.py` -> `add`
- `devops config secrets edit` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets.py` -> `edit`
- `devops config dump` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_config.py` -> `dump_config`
- `devops vault search` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_vault.py` -> `search`
- `devops vault login-and-unlock` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_vault.py` -> `login_and_unlock`
- `devops vault clean-cache` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_vault.py` -> `clean_cache`
- `devops network share-terminal` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_share_terminal.py` -> `share_terminal`
- `devops network share-server` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_share_server.py` -> `web_file_explorer`
- `devops network send` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_share_file.py` -> `share_file_send`
- `devops network receive` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_share_file.py` -> `share_file_receive`
- `devops network share-temp-file` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_share_temp.py` -> `upload_file`
- `devops network ssh install-server` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_ssh.py` -> `install_ssh_server`
- `devops network ssh change-port` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_ssh.py` -> `change_ssh_port`
- `devops network ssh add-key` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_ssh.py` -> `add_ssh_key`
- `devops network ssh debug` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_ssh.py` -> `debug_ssh`
- `devops network device switch-public-ip` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_device.py` -> `switch_public_ip_address`
- `devops network device wifi-select` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_device.py` -> `wifi_select`
- `devops network device bind-wsl-port` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_device.py` -> `bind_wsl_port`
- `devops network device open-wsl-port` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_device.py` -> `open_wsl_port`
- `devops network device link-wsl-windows` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_device.py` -> `link_wsl_and_windows_home`
- `devops network device reset-cloudflare-tunnel` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_device.py` -> `reset_cloudflare_tunnel`
- `devops network device add-ip-exclusion-to-warp` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_device.py` -> `add_ip_exclusion_to_warp`
- `devops network show-address` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_nw.py` -> `show_address`
- `devops network vscode-share` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_nw.py` -> `vscode_share`
- `devops execute` -> `src/stackops/scripts/python/devops.py` -> `execute`
- `devops self install` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_self.py` -> `install`
- `devops self clone` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_self.py` -> `clone`
- `devops self update` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_self.py` -> `update`
- `devops self status` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_self.py` -> `status`
- `devops self security scan` -> `src/stackops/jobs/installer/checks/security_cli.py` -> `scan`
- `devops self security list` -> `src/stackops/jobs/installer/checks/security_cli.py` -> `list_apps`
- `devops self security upload` -> `src/stackops/jobs/installer/checks/security_cli.py` -> `upload`
- `devops self security download` -> `src/stackops/jobs/installer/checks/security_cli.py` -> `download`
- `devops self security install` -> `src/stackops/jobs/installer/checks/security_cli.py` -> `install`
- `devops self security report` -> `src/stackops/jobs/installer/checks/security_cli.py` -> `report`
- `devops self explore search` -> `src/stackops/scripts/python/graph/visualize/cli_graph_app.py` -> `search`
- `devops self explore tree` -> `src/stackops/scripts/python/graph/visualize/cli_graph_app.py` -> `tree`
- `devops self explore dot` -> `src/stackops/scripts/python/graph/visualize/cli_graph_app.py` -> `dot`
- `devops self explore view` -> `src/stackops/scripts/python/graph/visualize/cli_graph_app.py` -> `chart`
- `devops self explore tui` -> `src/stackops/scripts/python/graph/visualize/cli_graph_app.py` -> `navigate`
- `devops self readme` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_self.py` -> `readme`
- `devops self docs` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_self.py` -> `docs`
- `devops self build-installer` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_self.py` -> `export`
- `devops self download-installer` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_self.py` -> `download_installer`
- `devops self build-docker` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_self.py` -> `build_docker`
- `devops self build-graph` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_self.py` -> `build_graph`
- `devops self build-assets update-cli-graph` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_self_assets.py` -> `update_cli_graph`
- `devops self build-assets regenerate-charts` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_self_assets.py` -> `regenerate_charts`
- `devops self build-assets update-skill-refs` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_self_assets.py` -> `update_stackops_skill_refs`
- `devops self workflows update-installer` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_self_ai/update_installer.py` -> `update_installer`
- `devops self workflows update-test` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_self_ai/update_test.py` -> `update_test`
- `devops self workflows update-docs` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_self_ai/update_docs.py` -> `update_docs`
- `devops self workflows update-logic` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_self_ai/update_logic.py` -> `update_logic`
- `cloud sync` -> `src/stackops/scripts/python/cloud.py` -> `sync`
- `cloud copy` -> `src/stackops/scripts/python/cloud.py` -> `copy`
- `cloud mount` -> `src/stackops/scripts/python/cloud.py` -> `mount`
- `cloud ftpx` -> `src/stackops/scripts/python/cloud.py` -> `ftpx`
- `terminal run` -> `src/stackops/scripts/python/terminal.py` -> `run`
- `terminal run-all` -> `src/stackops/scripts/python/terminal.py` -> `run_all`
- `terminal run-aoe` -> `src/stackops/scripts/python/terminal.py` -> `run_aoe`
- `terminal attach` -> `src/stackops/scripts/python/terminal.py` -> `attach_to_session`
- `terminal kill` -> `src/stackops/scripts/python/terminal.py` -> `kill_session_target`
- `terminal trace` -> `src/stackops/scripts/python/terminal.py` -> `trace`
- `terminal create-from-function` -> `src/stackops/scripts/python/terminal.py` -> `create_from_function`
- `terminal balance-load` -> `src/stackops/scripts/python/terminal.py` -> `balance_load`
- `terminal create-template` -> `src/stackops/scripts/python/terminal.py` -> `create_template`
- `terminal summarize` -> `src/stackops/scripts/python/terminal.py` -> `summarize`
- `agents parallel create` -> `src/stackops/scripts/python/agents_parallel_commands.py` -> `agents_create`
- `agents parallel create-context` -> `src/stackops/scripts/python/agents_parallel_commands.py` -> `create_context`
- `agents parallel run-parallel` -> `src/stackops/scripts/python/agents_parallel_run_command.py` -> `run_parallel`
- `agents parallel collect` -> `src/stackops/scripts/python/agents_parallel_commands.py` -> `collect`
- `agents parallel make-template` -> `src/stackops/scripts/python/agents_parallel_commands.py` -> `make_agents_command_template`
- `agents browser install-tech` -> `src/stackops/scripts/python/agents_browser.py` -> `install_tech`
- `agents browser launch-browser` -> `src/stackops/scripts/python/agents_browser.py` -> `launch_browser`
- `agents add-mcp` -> `src/stackops/scripts/python/agents.py` -> `add_mcp`
- `agents add-skill` -> `src/stackops/scripts/python/agents.py` -> `add_skill`
- `agents add-todo` -> `src/stackops/scripts/python/agents.py` -> `make_todo_files`
- `agents add-symlinks` -> `src/stackops/scripts/python/agents.py` -> `create_symlink_command`
- `agents add-config` -> `src/stackops/scripts/python/agents.py` -> `init_config`
- `agents run-prompt` -> `src/stackops/scripts/python/agents.py` -> `run_prompt`
- `agents run-interactive` -> `src/stackops/scripts/python/agents.py` -> `run_interactive`
- `agents ask` -> `src/stackops/scripts/python/agents.py` -> `ask`
- `utils machine kill-process` -> `src/stackops/scripts/python/helpers/helpers_utils/machine_utils_app.py` -> `kill_process`
- `utils machine environment` -> `src/stackops/scripts/python/helpers/helpers_utils/machine_utils_app.py` -> `tui_env`
- `utils machine get-machine-specs` -> `src/stackops/scripts/python/helpers/helpers_utils/machine_utils_app.py` -> `get_machine_specs`
- `utils machine list-devices` -> `src/stackops/scripts/python/helpers/helpers_utils/machine_utils_app.py` -> `list_devices`
- `utils machine mount` -> `src/stackops/scripts/python/helpers/helpers_utils/machine_utils_app.py` -> `mount_device`
- `utils pyproject init-project` -> `src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_app.py` -> `init_project`
- `utils pyproject upgrade-packages` -> `src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_app.py` -> `upgrade_packages`
- `utils pyproject type-hint` -> `src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_app.py` -> `type_hint`
- `utils pyproject type-check` -> `src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_app.py` -> `type_check`
- `utils pyproject test-reference` -> `src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_app.py` -> `reference_test`
- `utils file edit` -> `src/stackops/scripts/python/helpers/helpers_utils/file_utils_app.py` -> `edit_file_with_hx`
- `utils file download` -> `src/stackops/scripts/python/helpers/helpers_utils/file_utils_app.py` -> `download`
- `utils file scrape` -> `src/stackops/scripts/python/helpers/helpers_utils/file_utils_app.py` -> `scrape`
- `utils file pdf-merge` -> `src/stackops/scripts/python/helpers/helpers_utils/file_utils_app.py` -> `merge_pdfs`
- `utils file pdf-compress` -> `src/stackops/scripts/python/helpers/helpers_utils/file_utils_app.py` -> `compress_pdf`
- `utils file ocr` -> `src/stackops/scripts/python/helpers/helpers_utils/file_utils_app.py` -> `surya`
- `utils file read-db` -> `src/stackops/scripts/python/helpers/helpers_utils/file_utils_app.py` -> `read_db_cli_tui`
- `seek seek` -> `src/stackops/scripts/python/seek.py` -> `seek`
- `fire` -> `src/stackops/scripts/python/stackops_entry.py` -> `fire`
- `preview` -> `src/stackops/scripts/python/stackops_entry.py` -> `preview`

## Debugging and Validation Workflow

1. Confirm command registration in the nearest `get_app()` file from the group route above.
2. Trace leaf behavior from the command implementation line above.
3. Validate help surface locally with `UV_CACHE_DIR=/tmp/uv-cache uv run <command> --help` and then drill down one level at a time.
4. If command names change, run `UV_CACHE_DIR=/tmp/uv-cache uv run devops self build-assets update-skill-refs`.

# StackOps Python Module Intent Inventory

Generated first-pass report for deciding which Python modules are intended as downstream import API, CLI implementation, CLI helpers, or packaged assets.

This is intentionally a filter, not the final truth. Use the `Manual review queue` section to correct edge cases before adding source-level markers.

Scope: `src/stackops/**/*.py` only. This excludes `src/manual`, which is not part of the installed `stackops` package surface.

Snapshot: regenerated on 2026-11-28 from the working tree at commit `7386c014f` plus uncommitted changes. Every table and count below comes from that single pass; the `api-doc` signal reflects `docs/api` as it was on disk at that moment.

## Classification Rules

| Signal | Meaning |
| --- | --- |
| `pyproject.toml [project.scripts]` | Strong CLI entry point signal. |
| `stackops.scripts.python...` | CLI command tree. Direct Typer modules are CLI; non-Typer children are usually CLI helpers. |
| `stackops.utils.cli_utils` | Shared CLI plumbing. Treated as CLI helpers; queued for review when API docs reference it. |
| `docs/api` references and `::: stackops...` directives | Strong public API signal. |
| `stackops.cluster`, `stackops.utils`, `stackops.jobs.installer` | Candidate API roots unless they are script assets or show direct CLI behavior. The other library packages and top-level modules (`stackops.profile`, `stackops.secrets`, `stackops.architecture_graph`, `stackops.logger`, ...) are handled the same way. |
| `stackops.settings`, `stackops.scripts/setup`, installer script folders | Packaged assets or executable scripts, not dependency API by default. |
| `typer`, `get_app`, command registration, `main`, `if __name__ == "__main__"` | CLI/script signal; review if it appears outside the CLI tree. |

### Decision Order

Each module gets the first label whose condition matches. A CLI/script signal is any of `typer`, `typer-app`, `cli-registration`, `get_app`, `main`, `__main__`.

| Order | Condition | First-pass label | Suggested marker | Confidence |
| ---: | --- | --- | --- | --- |
| 1 | File is an `__init__.py` | `package-marker` | `package` | `high` |
| 2 | Target of a `[project.scripts]` entry | `cli-entrypoint` | `cli` | `high` |
| 3 | Under `stackops.scripts.python` or `stackops.utils.cli_utils`, with `api-doc` | `manual-review` | `api-or-cli-helper` | `low` |
| 4 | Under `stackops.scripts.python`, with `typer` | `cli-module` | `cli` | `high` |
| 5 | Anything else under `stackops.scripts.python` or `stackops.utils.cli_utils` | `cli-helper` | `cli-helper` | `medium` |
| 6 | Under `stackops.jobs.installer.python_scripts` | `installer-script-asset` | `script-asset` | `high` |
| 7 | Inside any other folder named `scripts`, `scripts_*` or `*_scripts` | `script-asset` | `script-asset` | `medium` |
| 8 | Anything else under `stackops.settings` | `config-asset` | `asset` | `high` |
| 9 | Remaining library module with `api-doc` and a CLI/script signal | `api-cli-bridge` | `api` | `medium` |
| 10 | Remaining library module with `api-doc` only | `python-api` | `api` | `high` |
| 11 | Remaining library module with a CLI/script signal only | `manual-review` | `api-or-script` | `medium` |
| 12 | Remaining library module with neither | `python-api-candidate` | `api` | `medium` |

### Signal Tokens

| Token in the `Signals` column | Set when |
| --- | --- |
| `entry:<name>` | The module is the target of the `<name>` console script in `pyproject.toml`. |
| `api-doc` | A dotted `stackops...` name in `docs/api/**/*.md` (prose, `package.*` wildcard or `:::` directive) points at the module or at something defined in it, or names a package at least three levels deep that contains the module. Naming a top-level package such as `stackops.utils` marks only that package. |
| `typer` | The module imports `typer`, at top level or inside a function. |
| `typer-app` | The module calls `typer.Typer(...)`. |
| `cli-registration` | The module calls `.command(...)`, `.add_typer(...)` or `typer.run(...)`. |
| `get_app`, `main` | The module defines a top-level function with that name. |
| `__main__` | The module has a top-level `if __name__ == "__main__":` block. |
| `__all__` | The module assigns `__all__` at top level. |
| `classes:N`, `funcs:N` | Number of top-level classes and functions. |

## Suggested Markers

These marker values are suggestions for a later source-level pass, for example `__stackops_module_intent__ = "api"`.

| Marker | Use |
| --- | --- |
| `api` | Stable or intended downstream import surface. |
| `cli` | Direct command/entrypoint module. |
| `cli-helper` | Implementation imported by CLI modules; not promised as dependency API. |
| `script-asset` | Packaged script or installer asset that may execute but is not an API. |
| `asset` | Config/settings package data. |
| `package` | `__init__.py` package marker. |
| `api-or-cli-helper`, `api-or-script`, `unknown` | Needs manual decision before marking. |

## Counts

Total installed `stackops` Python modules: **1380**

| First-pass label | Count |
| --- | ---: |
| `api-cli-bridge` | 23 |
| `cli-entrypoint` | 9 |
| `cli-helper` | 719 |
| `cli-module` | 159 |
| `config-asset` | 3 |
| `installer-script-asset` | 30 |
| `manual-review` | 55 |
| `package-marker` | 178 |
| `python-api` | 138 |
| `python-api-candidate` | 54 |
| `script-asset` | 12 |

| Suggested marker | Count |
| --- | ---: |
| `api` | 215 |
| `api-or-cli-helper` | 37 |
| `api-or-script` | 18 |
| `asset` | 3 |
| `cli` | 168 |
| `cli-helper` | 719 |
| `package` | 178 |
| `script-asset` | 42 |

| Confidence | Count |
| --- | ---: |
| `high` | 517 |
| `low` | 37 |
| `medium` | 826 |

## Manual Review Queue

These **78** modules need a human decision before source markers are added.

| Module | Suggested marker | Label | Signals | Reason | Notes |
| --- | --- | --- | --- | --- | --- |
| `stackops.cluster.sessions_managers.helpers.enhanced_command_runner` | `api` | `api-cli-bridge` | api-doc, __main__, funcs:1 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.cluster.sessions_managers.tmux.tmux_local` | `api` | `api-cli-bridge` | api-doc, __main__, classes:3, funcs:1 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.jobs.installer.checks.history_cli` | `api` | `api-cli-bridge` | api-doc, typer, funcs:4 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.jobs.installer.checks.scan_execution` | `api` | `api-cli-bridge` | api-doc, typer, funcs:1 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.jobs.installer.checks.security_cli` | `api` | `api-cli-bridge` | api-doc, typer, typer-app, cli-registration, get_app, funcs:7 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.jobs.installer.checks.status_cli` | `api` | `api-cli-bridge` | api-doc, typer, funcs:1 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.utils.cloud.onedrive.auth` | `api` | `api-cli-bridge` | api-doc, typer, classes:1, funcs:10 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.utils.cloud.onedrive.file_ops` | `api` | `api-cli-bridge` | api-doc, typer, funcs:3 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.utils.files.ascii_art` | `api` | `api-cli-bridge` | api-doc, __main__, classes:3, funcs:4 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.utils.files.read` | `api` | `api-cli-bridge` | api-doc, __main__, funcs:18 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.utils.installer_utils.installer_bulk_worker` | `api` | `api-cli-bridge` | api-doc, __main__, funcs:1 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.utils.installer_utils.installer_cli` | `api` | `api-cli-bridge` | api-doc, typer, funcs:9 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.utils.installer_utils.installer_explore` | `api` | `api-cli-bridge` | api-doc, typer, funcs:6 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.utils.installer_utils.installer_offline` | `api` | `api-cli-bridge` | api-doc, __main__, funcs:1 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.utils.installer_utils.linux_package_manager` | `api` | `api-cli-bridge` | api-doc, main, __main__, classes:5, funcs:12 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.utils.installer_utils.update_github_commit_dates` | `api` | `api-cli-bridge` | api-doc, main, __main__, classes:1, funcs:3 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.utils.meta` | `api` | `api-cli-bridge` | api-doc, __main__, funcs:3 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.utils.network.address` | `api` | `api-cli-bridge` | api-doc, __main__, classes:6, funcs:10 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.utils.options_utils.textual_options_form` | `api` | `api-cli-bridge` | api-doc, __main__, classes:5, funcs:14 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.utils.options_utils.tv_options` | `api` | `api-cli-bridge` | api-doc, __main__, funcs:3 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.utils.source_of_truth` | `api` | `api-cli-bridge` | api-doc, __main__, funcs:9 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.utils.ssh_utils.ssh` | `api` | `api-cli-bridge` | api-doc, __main__, classes:1 | Referenced by API docs but also has CLI/script signals; review marker wording. | Was `utils.ssh`; moved under `ssh_utils/`. |
| `stackops.utils.ssh_utils.wsl` | `api` | `api-cli-bridge` | api-doc, __main__, funcs:7 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.scripts.python.helpers.helpers_network.address_switch` | `api-or-cli-helper` | `manual-review` | api-doc, __main__, funcs:7 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.ftpx_impl` | `api-or-cli-helper` | `manual-review` | api-doc, funcs:7 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.onetimeshare` | `api-or-cli-helper` | `manual-review` | api-doc | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_add_key_posix` | `api-or-cli-helper` | `manual-review` | api-doc, funcs:1 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_add_key_windows` | `api-or-cli-helper` | `manual-review` | api-doc, funcs:4 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_add_ssh_key` | `api-or-cli-helper` | `manual-review` | api-doc, main, funcs:5 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_cloud_init` | `api-or-cli-helper` | `manual-review` | api-doc, funcs:2 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_common` | `api-or-cli-helper` | `manual-review` | api-doc, classes:4, funcs:4 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_darwin` | `api-or-cli-helper` | `manual-review` | api-doc, __main__, funcs:2 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_darwin_firewall` | `api-or-cli-helper` | `manual-review` | api-doc, funcs:2 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_darwin_network` | `api-or-cli-helper` | `manual-review` | api-doc, funcs:4 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_darwin_utils` | `api-or-cli-helper` | `manual-review` | api-doc, funcs:3 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_keys` | `api-or-cli-helper` | `manual-review` | api-doc, classes:1, funcs:3 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_linux` | `api-or-cli-helper` | `manual-review` | api-doc, __main__, funcs:2 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_linux_firewall` | `api-or-cli-helper` | `manual-review` | api-doc, funcs:5 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_linux_utils` | `api-or-cli-helper` | `manual-review` | api-doc, classes:1, funcs:6 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_models` | `api-or-cli-helper` | `manual-review` | api-doc, classes:3, funcs:2 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_windows` | `api-or-cli-helper` | `manual-review` | api-doc, __main__, funcs:2 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_windows_acl` | `api-or-cli-helper` | `manual-review` | api-doc, funcs:3 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_windows_firewall` | `api-or-cli-helper` | `manual-review` | api-doc, funcs:9 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_windows_network` | `api-or-cli-helper` | `manual-review` | api-doc, funcs:2 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_windows_utils` | `api-or-cli-helper` | `manual-review` | api-doc, classes:2, funcs:7 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_deploy_key_remote` | `api-or-cli-helper` | `manual-review` | api-doc, funcs:6 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_public_key_validation` | `api-or-cli-helper` | `manual-review` | api-doc, funcs:6 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_public_keys` | `api-or-cli-helper` | `manual-review` | api-doc, classes:1, funcs:7 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_remote_connection` | `api-or-cli-helper` | `manual-review` | api-doc, classes:2, funcs:5 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.warp_connect` | `api-or-cli-helper` | `manual-review` | api-doc, classes:3, funcs:7 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.warp_status` | `api-or-cli-helper` | `manual-review` | api-doc, classes:2, funcs:7 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.wifi_conn` | `api-or-cli-helper` | `manual-review` | api-doc, classes:1, funcs:10 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.wifi_conn_platforms.common` | `api-or-cli-helper` | `manual-review` | api-doc, classes:1, funcs:4 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.wifi_conn_platforms.darwin` | `api-or-cli-helper` | `manual-review` | api-doc, funcs:8 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.wifi_conn_platforms.linux` | `api-or-cli-helper` | `manual-review` | api-doc, classes:1, funcs:16 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.wifi_conn_platforms.unsupported` | `api-or-cli-helper` | `manual-review` | api-doc, funcs:7 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.wifi_conn_platforms.windows` | `api-or-cli-helper` | `manual-review` | api-doc, funcs:6 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_utils.python_env` | `api-or-cli-helper` | `manual-review` | api-doc, funcs:2 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.utils.cli_utils.interaction` | `api-or-cli-helper` | `manual-review` | api-doc, typer, funcs:4 | CLI plumbing module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.utils.cli_utils.terminal` | `api-or-cli-helper` | `manual-review` | api-doc, classes:2 | CLI plumbing module is referenced by API docs; decide whether it is stable public API. | Was `utils.terminal`; moved under `cli_utils/`. |
| `stackops.architecture_graph.__main__` | `api-or-script` | `manual-review` | __main__ | Library-tree module has CLI/script signals; decide if those are demos, probes, or user-facing CLI. |  |
| `stackops.architecture_graph.cli` | `api-or-script` | `manual-review` | main, classes:1, funcs:3 | Library-tree module has CLI/script signals; decide if those are demos, probes, or user-facing CLI. |  |
| `stackops.profile.create_links` | `api-or-script` | `manual-review` | __main__, classes:1, funcs:13 | Library-tree module has CLI/script signals; decide if those are demos, probes, or user-facing CLI. |  |
| `stackops.profile.create_links_export` | `api-or-script` | `manual-review` | typer, funcs:2 | Library-tree module has CLI/script signals; decide if those are demos, probes, or user-facing CLI. |  |
| `stackops.profile.create_shell_profile` | `api-or-script` | `manual-review` | __main__, funcs:5 | Library-tree module has CLI/script signals; decide if those are demos, probes, or user-facing CLI. |  |
| `stackops.secrets.passwords` | `api-or-script` | `manual-review` | typer, funcs:1 | Library-tree module has CLI/script signals; decide if those are demos, probes, or user-facing CLI. |  |
| `stackops.utils.cloud.onedrive.cli` | `api-or-script` | `manual-review` | typer, typer-app, cli-registration, get_app, funcs:12 | Library-tree module has CLI/script signals; decide if those are demos, probes, or user-facing CLI. |  |
| `stackops.utils.cloud.onedrive.errors` | `api-or-script` | `manual-review` | typer, classes:1, funcs:1 | Library-tree module has CLI/script signals; decide if those are demos, probes, or user-facing CLI. |  |
| `stackops.utils.cloud.onedrive.output` | `api-or-script` | `manual-review` | typer, funcs:2 | Library-tree module has CLI/script signals; decide if those are demos, probes, or user-facing CLI. |  |
| `stackops.utils.file_editor_cli` | `api-or-script` | `manual-review` | typer, funcs:2 | Library-tree module has CLI/script signals; decide if those are demos, probes, or user-facing CLI. |  |
| `stackops.utils.files.dbms` | `api-or-script` | `manual-review` | __main__, classes:1, funcs:3 | Library-tree module has CLI/script signals; decide if those are demos, probes, or user-facing CLI. |  |
| `stackops.utils.files.download` | `api-or-script` | `manual-review` | typer, __main__, funcs:1 | Library-tree module has CLI/script signals; decide if those are demos, probes, or user-facing CLI. |  |
| `stackops.utils.managed_file_cli` | `api-or-script` | `manual-review` | typer, funcs:2 | Library-tree module has CLI/script signals; decide if those are demos, probes, or user-facing CLI. |  |
| `stackops.utils.managed_file_commands` | `api-or-script` | `manual-review` | typer, cli-registration, funcs:1 | Library-tree module has CLI/script signals; decide if those are demos, probes, or user-facing CLI. |  |
| `stackops.utils.options_utils.options_tv_linux` | `api-or-script` | `manual-review` | __main__, funcs:9 | Library-tree module has CLI/script signals; decide if those are demos, probes, or user-facing CLI. |  |
| `stackops.utils.options_utils.options_tv_windows` | `api-or-script` | `manual-review` | __main__, funcs:5 | Library-tree module has CLI/script signals; decide if those are demos, probes, or user-facing CLI. |  |
| `stackops.utils.sandbox.openshell_run` | `api-or-script` | `manual-review` | main, __main__, funcs:2 | Library-tree module has CLI/script signals; decide if those are demos, probes, or user-facing CLI. |  |
| `stackops.utils.sandbox.windows_srt` | `api-or-script` | `manual-review` | main, __main__, funcs:4 | Library-tree module has CLI/script signals; decide if those are demos, probes, or user-facing CLI. |  |

## Clear API Candidates

These **192** modules are the strongest candidates for `api` markers after manual review of the queue above.

| Module | Label | Confidence | Signals | Path | Notes |
| --- | --- | --- | --- | --- | --- |
| `stackops.architecture_graph.graph` | `python-api-candidate` | `medium` | funcs:8 | src/stackops/architecture_graph/graph.py |  |
| `stackops.architecture_graph.models` | `python-api-candidate` | `medium` | classes:6 | src/stackops/architecture_graph/models.py |  |
| `stackops.architecture_graph.renderer` | `python-api-candidate` | `medium` | funcs:3 | src/stackops/architecture_graph/renderer.py |  |
| `stackops.architecture_graph.scanner` | `python-api-candidate` | `medium` | classes:1, funcs:8 | src/stackops/architecture_graph/scanner.py |  |
| `stackops.cluster.remote.cloud_manager` | `python-api` | `high` | api-doc, classes:2, funcs:9 | src/stackops/cluster/remote/cloud_manager.py |  |
| `stackops.cluster.remote.data_transfer` | `python-api` | `high` | api-doc, funcs:3 | src/stackops/cluster/remote/data_transfer.py |  |
| `stackops.cluster.remote.distribute` | `python-api` | `high` | api-doc, classes:5, funcs:6 | src/stackops/cluster/remote/distribute.py |  |
| `stackops.cluster.remote.execution_script` | `python-api` | `high` | api-doc, funcs:1 | src/stackops/cluster/remote/execution_script.py |  |
| `stackops.cluster.remote.file_manager` | `python-api` | `high` | api-doc, classes:1, funcs:6 | src/stackops/cluster/remote/file_manager.py |  |
| `stackops.cluster.remote.job_params` | `python-api` | `high` | api-doc, classes:1, funcs:2 | src/stackops/cluster/remote/job_params.py |  |
| `stackops.cluster.remote.models` | `python-api` | `high` | api-doc, classes:5, funcs:3 | src/stackops/cluster/remote/models.py |  |
| `stackops.cluster.remote.remote_machine` | `python-api` | `high` | api-doc, classes:1, funcs:1 | src/stackops/cluster/remote/remote_machine.py |  |
| `stackops.cluster.scheduler` | `python-api` | `high` | api-doc, classes:4, funcs:2 | src/stackops/cluster/scheduler.py | Was `utils.scheduler`; moved to `cluster/`. |
| `stackops.cluster.sessions_managers.helpers.load_balancer_helper` | `python-api` | `high` | api-doc, funcs:10 | src/stackops/cluster/sessions_managers/helpers/load_balancer_helper.py |  |
| `stackops.cluster.sessions_managers.monitoring_types` | `python-api` | `high` | api-doc, classes:4 | src/stackops/cluster/sessions_managers/monitoring_types.py |  |
| `stackops.cluster.sessions_managers.session_conflict` | `python-api` | `high` | api-doc, classes:2, funcs:8 | src/stackops/cluster/sessions_managers/session_conflict.py |  |
| `stackops.cluster.sessions_managers.session_exit_mode` | `python-api` | `high` | api-doc, funcs:3 | src/stackops/cluster/sessions_managers/session_exit_mode.py |  |
| `stackops.cluster.sessions_managers.session_launch_table` | `python-api` | `high` | api-doc, classes:2, funcs:2 | src/stackops/cluster/sessions_managers/session_launch_table.py |  |
| `stackops.cluster.sessions_managers.status_reporting` | `python-api` | `high` | api-doc, funcs:1 | src/stackops/cluster/sessions_managers/status_reporting.py |  |
| `stackops.cluster.sessions_managers.tmux.tmux_local_manager` | `python-api` | `high` | api-doc, classes:2 | src/stackops/cluster/sessions_managers/tmux/tmux_local_manager.py |  |
| `stackops.cluster.sessions_managers.tmux.tmux_utils.tmux_common` | `python-api` | `high` | api-doc, funcs:2 | src/stackops/cluster/sessions_managers/tmux/tmux_utils/tmux_common.py |  |
| `stackops.cluster.sessions_managers.tmux.tmux_utils.tmux_execution` | `python-api` | `high` | api-doc, funcs:21 | src/stackops/cluster/sessions_managers/tmux/tmux_utils/tmux_execution.py |  |
| `stackops.cluster.sessions_managers.tmux.tmux_utils.tmux_launch_table` | `python-api` | `high` | api-doc, funcs:2 | src/stackops/cluster/sessions_managers/tmux/tmux_utils/tmux_launch_table.py |  |
| `stackops.cluster.sessions_managers.tmux.tmux_utils.tmux_layout` | `python-api` | `high` | api-doc, funcs:12 | src/stackops/cluster/sessions_managers/tmux/tmux_utils/tmux_layout.py |  |
| `stackops.cluster.sessions_managers.tmux.tmux_utils.tmux_status` | `python-api` | `high` | api-doc, classes:1, funcs:2 | src/stackops/cluster/sessions_managers/tmux/tmux_utils/tmux_status.py |  |
| `stackops.cluster.sessions_managers.utils.load_balancer` | `python-api` | `high` | api-doc, classes:1, funcs:3 | src/stackops/cluster/sessions_managers/utils/load_balancer.py |  |
| `stackops.cluster.sessions_managers.utils.maker` | `python-api` | `high` | api-doc, funcs:5 | src/stackops/cluster/sessions_managers/utils/maker.py |  |
| `stackops.jobs.installer.checks.app_upload` | `python-api` | `high` | api-doc, funcs:1 | src/stackops/jobs/installer/checks/app_upload.py |  |
| `stackops.jobs.installer.checks.check_installations` | `python-api` | `high` | api-doc, funcs:1 | src/stackops/jobs/installer/checks/check_installations.py |  |
| `stackops.jobs.installer.checks.constants` | `python-api` | `high` | api-doc | src/stackops/jobs/installer/checks/constants.py |  |
| `stackops.jobs.installer.checks.install_utils` | `python-api` | `high` | api-doc, funcs:3 | src/stackops/jobs/installer/checks/install_utils.py |  |
| `stackops.jobs.installer.checks.report_utils` | `python-api` | `high` | api-doc, classes:4, funcs:16 | src/stackops/jobs/installer/checks/report_utils.py |  |
| `stackops.jobs.installer.checks.run_reports` | `python-api` | `high` | api-doc, funcs:2 | src/stackops/jobs/installer/checks/run_reports.py |  |
| `stackops.jobs.installer.checks.scan_history` | `python-api` | `high` | api-doc, classes:3, funcs:4 | src/stackops/jobs/installer/checks/scan_history.py |  |
| `stackops.jobs.installer.checks.scan_outcomes` | `python-api` | `high` | api-doc, classes:3, funcs:1 | src/stackops/jobs/installer/checks/scan_outcomes.py |  |
| `stackops.jobs.installer.checks.scan_overview` | `python-api` | `high` | api-doc, classes:5, funcs:4 | src/stackops/jobs/installer/checks/scan_overview.py |  |
| `stackops.jobs.installer.checks.scan_records` | `python-api` | `high` | api-doc, funcs:1 | src/stackops/jobs/installer/checks/scan_records.py |  |
| `stackops.jobs.installer.checks.security_helper` | `python-api` | `high` | api-doc, funcs:3 | src/stackops/jobs/installer/checks/security_helper.py |  |
| `stackops.jobs.installer.checks.vt_account_report` | `python-api` | `high` | api-doc, funcs:3 | src/stackops/jobs/installer/checks/vt_account_report.py |  |
| `stackops.jobs.installer.checks.vt_account_stats` | `python-api` | `high` | api-doc, classes:4 | src/stackops/jobs/installer/checks/vt_account_stats.py |  |
| `stackops.jobs.installer.checks.vt_accounts` | `python-api` | `high` | api-doc, classes:3, funcs:2 | src/stackops/jobs/installer/checks/vt_accounts.py |  |
| `stackops.jobs.installer.checks.vt_display` | `python-api` | `high` | api-doc, funcs:1 | src/stackops/jobs/installer/checks/vt_display.py |  |
| `stackops.jobs.installer.checks.vt_request_errors` | `python-api` | `high` | api-doc, classes:1, funcs:1 | src/stackops/jobs/installer/checks/vt_request_errors.py |  |
| `stackops.jobs.installer.checks.vt_requests` | `python-api` | `high` | api-doc, classes:4 | src/stackops/jobs/installer/checks/vt_requests.py |  |
| `stackops.jobs.installer.checks.vt_scanner` | `python-api` | `high` | api-doc, funcs:3 | src/stackops/jobs/installer/checks/vt_scanner.py |  |
| `stackops.jobs.installer.checks.vt_transport` | `python-api` | `high` | api-doc, classes:1, funcs:2 | src/stackops/jobs/installer/checks/vt_transport.py |  |
| `stackops.jobs.installer.checks.vt_utils` | `python-api` | `high` | api-doc, classes:2, funcs:5 | src/stackops/jobs/installer/checks/vt_utils.py |  |
| `stackops.jobs.installer.checks.vt_workers` | `python-api` | `high` | api-doc, classes:4, funcs:2 | src/stackops/jobs/installer/checks/vt_workers.py |  |
| `stackops.logger` | `python-api` | `high` | api-doc, funcs:2 | src/stackops/logger.py |  |
| `stackops.paths` | `python-api-candidate` | `medium` | - | src/stackops/paths.py |  |
| `stackops.profile.create_helper` | `python-api` | `high` | api-doc, funcs:4 | src/stackops/profile/create_helper.py |  |
| `stackops.profile.dotfiles_collect_plan` | `python-api-candidate` | `medium` | classes:1, funcs:9 | src/stackops/profile/dotfiles_collect_plan.py |  |
| `stackops.profile.dotfiles_constants` | `python-api-candidate` | `medium` | - | src/stackops/profile/dotfiles_constants.py |  |
| `stackops.profile.dotfiles_mapper` | `python-api` | `high` | api-doc, classes:1, funcs:12 | src/stackops/profile/dotfiles_mapper.py |  |
| `stackops.profile.linking.conflict` | `python-api-candidate` | `medium` | - | src/stackops/profile/linking/conflict.py |  |
| `stackops.profile.linking.display` | `python-api-candidate` | `medium` | funcs:6 | src/stackops/profile/linking/display.py |  |
| `stackops.profile.linking.operations` | `python-api-candidate` | `medium` | classes:2, funcs:4 | src/stackops/profile/linking/operations.py |  |
| `stackops.profile.linking.options` | `python-api-candidate` | `medium` | - | src/stackops/profile/linking/options.py |  |
| `stackops.profile.migration_until_2028_01_bash_zsh_hook` | `python-api-candidate` | `medium` | funcs:1 | src/stackops/profile/migration_until_2028_01_bash_zsh_hook.py |  |
| `stackops.profile.shell_profile_source` | `python-api-candidate` | `medium` | classes:1, funcs:1 | src/stackops/profile/shell_profile_source.py |  |
| `stackops.secrets.assets` | `python-api-candidate` | `medium` | - | src/stackops/secrets/assets.py |  |
| `stackops.secrets.constants` | `python-api-candidate` | `medium` | - | src/stackops/secrets/constants.py |  |
| `stackops.secrets.loader` | `python-api` | `high` | api-doc, classes:1, funcs:15 | src/stackops/secrets/loader.py |  |
| `stackops.secrets.models` | `python-api` | `high` | api-doc, classes:3 | src/stackops/secrets/models.py |  |
| `stackops.secrets.paths` | `python-api-candidate` | `medium` | - | src/stackops/secrets/paths.py |  |
| `stackops.secrets.readers` | `python-api-candidate` | `medium` | classes:1, funcs:2 | src/stackops/secrets/readers.py |  |
| `stackops.secrets.search` | `python-api` | `high` | api-doc, classes:2, funcs:7 | src/stackops/secrets/search.py |  |
| `stackops.secrets.writer` | `python-api` | `high` | api-doc, funcs:3 | src/stackops/secrets/writer.py |  |
| `stackops.utils.accessories` | `python-api` | `high` | api-doc, funcs:8 | src/stackops/utils/accessories.py |  |
| `stackops.utils.cloud.default_remote` | `python-api` | `high` | api-doc, classes:1, funcs:2 | src/stackops/utils/cloud/default_remote.py |  |
| `stackops.utils.cloud.defaults` | `python-api` | `high` | api-doc, classes:1, funcs:1 | src/stackops/utils/cloud/defaults.py | Was `utils.cloud_defaults`; moved under `cloud/`. |
| `stackops.utils.cloud.encryption` | `python-api` | `high` | api-doc, funcs:1 | src/stackops/utils/cloud/encryption.py | Was `utils.encryption`; moved under `cloud/`. |
| `stackops.utils.cloud.onedrive.accounts` | `python-api-candidate` | `medium` | classes:2, funcs:6 | src/stackops/utils/cloud/onedrive/accounts.py |  |
| `stackops.utils.cloud.onedrive.constants` | `python-api-candidate` | `medium` | - | src/stackops/utils/cloud/onedrive/constants.py |  |
| `stackops.utils.cloud.onedrive.credentials` | `python-api-candidate` | `medium` | classes:1, funcs:3 | src/stackops/utils/cloud/onedrive/credentials.py |  |
| `stackops.utils.cloud.onedrive.items` | `python-api-candidate` | `medium` | funcs:4 | src/stackops/utils/cloud/onedrive/items.py |  |
| `stackops.utils.cloud.rclone` | `python-api` | `high` | api-doc, classes:2, funcs:20 | src/stackops/utils/cloud/rclone.py | Was `utils.rclone`; moved under `cloud/`. |
| `stackops.utils.cloud.rclone_wrapper` | `python-api` | `high` | api-doc, funcs:8 | src/stackops/utils/cloud/rclone_wrapper.py | Was `utils.rclone_wrapper`; moved under `cloud/`. |
| `stackops.utils.cloud.share_models` | `python-api-candidate` | `medium` | classes:1 | src/stackops/utils/cloud/share_models.py |  |
| `stackops.utils.cloud.target_conflict` | `python-api-candidate` | `medium` | classes:1, funcs:9 | src/stackops/utils/cloud/target_conflict.py |  |
| `stackops.utils.code` | `python-api` | `high` | api-doc, funcs:10 | src/stackops/utils/code.py |  |
| `stackops.utils.constants` | `python-api-candidate` | `medium` | - | src/stackops/utils/constants.py |  |
| `stackops.utils.dashboards.constants` | `python-api-candidate` | `medium` | - | src/stackops/utils/dashboards/constants.py |  |
| `stackops.utils.dashboards.lifecycle` | `python-api-candidate` | `medium` | funcs:2 | src/stackops/utils/dashboards/lifecycle.py |  |
| `stackops.utils.dashboards.ownership` | `python-api-candidate` | `medium` | classes:1, funcs:4 | src/stackops/utils/dashboards/ownership.py |  |
| `stackops.utils.default_agent` | `python-api-candidate` | `medium` | funcs:1 | src/stackops/utils/default_agent.py |  |
| `stackops.utils.default_multiplexer` | `python-api-candidate` | `medium` | funcs:3 | src/stackops/utils/default_multiplexer.py |  |
| `stackops.utils.files.compression` | `python-api` | `high` | api-doc, __all__, funcs:19 | src/stackops/utils/files/compression.py |  |
| `stackops.utils.files.compression_constants` | `python-api-candidate` | `medium` | - | src/stackops/utils/files/compression_constants.py |  |
| `stackops.utils.files.f` | `python-api-candidate` | `medium` | classes:1, funcs:1 | src/stackops/utils/files/f.py |  |
| `stackops.utils.files.headers` | `python-api` | `high` | api-doc, funcs:6 | src/stackops/utils/files/headers.py |  |
| `stackops.utils.files.notebook` | `python-api` | `high` | api-doc, funcs:1 | src/stackops/utils/files/notebook.py |  |
| `stackops.utils.files.ouch.decompress` | `python-api` | `high` | api-doc, funcs:1 | src/stackops/utils/files/ouch/decompress.py |  |
| `stackops.utils.html_report` | `python-api-candidate` | `medium` | funcs:1 | src/stackops/utils/html_report.py |  |
| `stackops.utils.installer_utils.apt_archive_download` | `python-api` | `high` | api-doc, funcs:1 | src/stackops/utils/installer_utils/apt_archive_download.py |  |
| `stackops.utils.installer_utils.constants` | `python-api` | `high` | api-doc | src/stackops/utils/installer_utils/constants.py |  |
| `stackops.utils.installer_utils.github_commit_dates_constants` | `python-api` | `high` | api-doc | src/stackops/utils/installer_utils/github_commit_dates_constants.py |  |
| `stackops.utils.installer_utils.github_commit_dates_fetch` | `python-api` | `high` | api-doc, classes:1, funcs:2 | src/stackops/utils/installer_utils/github_commit_dates_fetch.py |  |
| `stackops.utils.installer_utils.github_commit_dates_output` | `python-api` | `high` | api-doc, classes:2, funcs:2 | src/stackops/utils/installer_utils/github_commit_dates_output.py |  |
| `stackops.utils.installer_utils.github_commit_dates_report` | `python-api` | `high` | api-doc, classes:2, funcs:6 | src/stackops/utils/installer_utils/github_commit_dates_report.py |  |
| `stackops.utils.installer_utils.github_release_bulk` | `python-api` | `high` | api-doc, classes:3, funcs:6 | src/stackops/utils/installer_utils/github_release_bulk.py |  |
| `stackops.utils.installer_utils.github_release_scraper` | `python-api` | `high` | api-doc, funcs:5 | src/stackops/utils/installer_utils/github_release_scraper.py |  |
| `stackops.utils.installer_utils.install_from_url` | `python-api` | `high` | api-doc, classes:1, funcs:7 | src/stackops/utils/installer_utils/install_from_url.py |  |
| `stackops.utils.installer_utils.install_request_logic` | `python-api` | `high` | api-doc, classes:2, funcs:12 | src/stackops/utils/installer_utils/install_request_logic.py |  |
| `stackops.utils.installer_utils.installer_bulk_display` | `python-api` | `high` | api-doc, funcs:10 | src/stackops/utils/installer_utils/installer_bulk_display.py |  |
| `stackops.utils.installer_utils.installer_bulk_models` | `python-api` | `high` | api-doc, classes:6 | src/stackops/utils/installer_utils/installer_bulk_models.py |  |
| `stackops.utils.installer_utils.installer_bulk_plan` | `python-api` | `high` | api-doc, funcs:3 | src/stackops/utils/installer_utils/installer_bulk_plan.py |  |
| `stackops.utils.installer_utils.installer_bulk_runner` | `python-api` | `high` | api-doc, funcs:4 | src/stackops/utils/installer_utils/installer_bulk_runner.py |  |
| `stackops.utils.installer_utils.installer_bulk_steps` | `python-api` | `high` | api-doc, funcs:3 | src/stackops/utils/installer_utils/installer_bulk_steps.py |  |
| `stackops.utils.installer_utils.installer_catalog` | `python-api` | `high` | api-doc, classes:1, funcs:12 | src/stackops/utils/installer_utils/installer_catalog.py |  |
| `stackops.utils.installer_utils.installer_class` | `python-api` | `high` | api-doc, classes:1 | src/stackops/utils/installer_utils/installer_class.py |  |
| `stackops.utils.installer_utils.installer_explore_preview` | `python-api` | `high` | api-doc, funcs:3 | src/stackops/utils/installer_utils/installer_explore_preview.py |  |
| `stackops.utils.installer_utils.installer_helper` | `python-api` | `high` | api-doc, funcs:6 | src/stackops/utils/installer_utils/installer_helper.py |  |
| `stackops.utils.installer_utils.installer_locator_utils` | `python-api` | `high` | api-doc, funcs:14 | src/stackops/utils/installer_utils/installer_locator_utils.py |  |
| `stackops.utils.installer_utils.installer_main_protocol` | `python-api` | `high` | api-doc, classes:1, funcs:2 | src/stackops/utils/installer_utils/installer_main_protocol.py |  |
| `stackops.utils.installer_utils.installer_offline_constants` | `python-api` | `high` | api-doc, funcs:2 | src/stackops/utils/installer_utils/installer_offline_constants.py |  |
| `stackops.utils.installer_utils.installer_offline_models` | `python-api` | `high` | api-doc, classes:4 | src/stackops/utils/installer_utils/installer_offline_models.py |  |
| `stackops.utils.installer_utils.installer_offline_publish` | `python-api` | `high` | api-doc, funcs:6 | src/stackops/utils/installer_utils/installer_offline_publish.py |  |
| `stackops.utils.installer_utils.installer_offline_render` | `python-api` | `high` | api-doc, funcs:3 | src/stackops/utils/installer_utils/installer_offline_render.py |  |
| `stackops.utils.installer_utils.installer_offline_scripts` | `python-api` | `high` | api-doc, funcs:1 | src/stackops/utils/installer_utils/installer_offline_scripts.py |  |
| `stackops.utils.installer_utils.installer_offline_steps` | `python-api` | `high` | api-doc, funcs:3 | src/stackops/utils/installer_utils/installer_offline_steps.py |  |
| `stackops.utils.installer_utils.installer_offline_uv` | `python-api` | `high` | api-doc, funcs:6 | src/stackops/utils/installer_utils/installer_offline_uv.py |  |
| `stackops.utils.installer_utils.installer_removal` | `python-api` | `high` | api-doc, classes:3, funcs:2 | src/stackops/utils/installer_utils/installer_removal.py |  |
| `stackops.utils.installer_utils.installer_runner` | `python-api` | `high` | api-doc, funcs:5 | src/stackops/utils/installer_utils/installer_runner.py |  |
| `stackops.utils.installer_utils.installer_scripts` | `python-api` | `high` | api-doc, funcs:3 | src/stackops/utils/installer_utils/installer_scripts.py |  |
| `stackops.utils.installer_utils.installer_summary` | `python-api` | `high` | api-doc, funcs:8 | src/stackops/utils/installer_utils/installer_summary.py |  |
| `stackops.utils.installer_utils.installer_uninstall_command` | `python-api` | `high` | api-doc, funcs:1 | src/stackops/utils/installer_utils/installer_uninstall_command.py |  |
| `stackops.utils.installer_utils.linux_package_file` | `python-api` | `high` | api-doc, classes:1, funcs:4 | src/stackops/utils/installer_utils/linux_package_file.py |  |
| `stackops.utils.installer_utils.package_manager_installation` | `python-api` | `high` | api-doc, funcs:3 | src/stackops/utils/installer_utils/package_manager_installation.py |  |
| `stackops.utils.io` | `python-api` | `high` | api-doc, classes:1, funcs:22 | src/stackops/utils/io.py |  |
| `stackops.utils.machine.specs` | `python-api-candidate` | `medium` | classes:1, funcs:1 | src/stackops/utils/machine/specs.py |  |
| `stackops.utils.managed_agent_files` | `python-api-candidate` | `medium` | funcs:4 | src/stackops/utils/managed_agent_files.py |  |
| `stackops.utils.managed_file_operations` | `python-api-candidate` | `medium` | funcs:5 | src/stackops/utils/managed_file_operations.py |  |
| `stackops.utils.managed_files` | `python-api-candidate` | `medium` | classes:1, funcs:4 | src/stackops/utils/managed_files.py |  |
| `stackops.utils.optional_dependencies` | `python-api-candidate` | `medium` | - | src/stackops/utils/optional_dependencies.py |  |
| `stackops.utils.options_utils.options` | `python-api` | `high` | api-doc, funcs:8 | src/stackops/utils/options_utils/options.py | Was `utils.options`; moved under `options_utils/`. |
| `stackops.utils.options_utils.textual_options_form_types` | `python-api` | `high` | api-doc, classes:2 | src/stackops/utils/options_utils/textual_options_form_types.py |  |
| `stackops.utils.path_core` | `python-api` | `high` | api-doc, __all__, funcs:22 | src/stackops/utils/path_core.py |  |
| `stackops.utils.path_reference` | `python-api` | `high` | api-doc, funcs:3 | src/stackops/utils/path_reference.py |  |
| `stackops.utils.python.imports` | `python-api-candidate` | `medium` | funcs:2 | src/stackops/utils/python/imports.py |  |
| `stackops.utils.repos.constants` | `python-api-candidate` | `medium` | - | src/stackops/utils/repos/constants.py |  |
| `stackops.utils.repos.project` | `python-api` | `high` | api-doc, funcs:1 | src/stackops/utils/repos/project.py |  |
| `stackops.utils.repos.stackops_paths` | `python-api` | `high` | api-doc, funcs:6 | src/stackops/utils/repos/stackops_paths.py |  |
| `stackops.utils.sandbox.containers` | `python-api-candidate` | `medium` | funcs:2 | src/stackops/utils/sandbox/containers.py |  |
| `stackops.utils.sandbox.host` | `python-api-candidate` | `medium` | funcs:1 | src/stackops/utils/sandbox/host.py |  |
| `stackops.utils.sandbox.launch` | `python-api-candidate` | `medium` | funcs:2 | src/stackops/utils/sandbox/launch.py |  |
| `stackops.utils.sandbox.openshell` | `python-api-candidate` | `medium` | funcs:1 | src/stackops/utils/sandbox/openshell.py |  |
| `stackops.utils.sandbox.openshell_transfer` | `python-api-candidate` | `medium` | funcs:1 | src/stackops/utils/sandbox/openshell_transfer.py |  |
| `stackops.utils.sandbox.openshell_workspace` | `python-api-candidate` | `medium` | funcs:2 | src/stackops/utils/sandbox/openshell_workspace.py |  |
| `stackops.utils.sandbox.openshell_workspace_entries` | `python-api-candidate` | `medium` | classes:1, funcs:4 | src/stackops/utils/sandbox/openshell_workspace_entries.py |  |
| `stackops.utils.sandbox.options` | `python-api-candidate` | `medium` | classes:4 | src/stackops/utils/sandbox/options.py |  |
| `stackops.utils.schemas.config.config_types` | `python-api` | `high` | api-doc, classes:2 | src/stackops/utils/schemas/config/config_types.py |  |
| `stackops.utils.schemas.config.constants` | `python-api-candidate` | `medium` | - | src/stackops/utils/schemas/config/constants.py |  |
| `stackops.utils.schemas.config.migration_until_2028_01_json_to_yaml` | `python-api-candidate` | `medium` | funcs:1 | src/stackops/utils/schemas/config/migration_until_2028_01_json_to_yaml.py |  |
| `stackops.utils.schemas.config.multiplexer_types` | `python-api` | `high` | api-doc | src/stackops/utils/schemas/config/multiplexer_types.py |  |
| `stackops.utils.schemas.fire_agents.fire_agents_types` | `python-api-candidate` | `medium` | classes:2 | src/stackops/utils/schemas/fire_agents/fire_agents_types.py |  |
| `stackops.utils.schemas.installer.installer_categories` | `python-api` | `high` | api-doc, classes:1, funcs:1 | src/stackops/utils/schemas/installer/installer_categories.py |  |
| `stackops.utils.schemas.installer.installer_types` | `python-api` | `high` | api-doc, classes:11, funcs:2 | src/stackops/utils/schemas/installer/installer_types.py |  |
| `stackops.utils.schemas.installer.package_groups` | `python-api` | `high` | api-doc | src/stackops/utils/schemas/installer/package_groups.py |  |
| `stackops.utils.schemas.json_schema` | `python-api` | `high` | api-doc, funcs:1 | src/stackops/utils/schemas/json_schema.py |  |
| `stackops.utils.schemas.layouts.layout_arrangement` | `python-api` | `high` | api-doc, funcs:1 | src/stackops/utils/schemas/layouts/layout_arrangement.py |  |
| `stackops.utils.schemas.layouts.layout_constants` | `python-api` | `high` | api-doc | src/stackops/utils/schemas/layouts/layout_constants.py |  |
| `stackops.utils.schemas.layouts.layout_enabled` | `python-api` | `high` | api-doc, funcs:2 | src/stackops/utils/schemas/layouts/layout_enabled.py |  |
| `stackops.utils.schemas.layouts.layout_enabled_edit` | `python-api` | `high` | api-doc, classes:2, funcs:1 | src/stackops/utils/schemas/layouts/layout_enabled_edit.py |  |
| `stackops.utils.schemas.layouts.layout_file` | `python-api` | `high` | api-doc, funcs:6 | src/stackops/utils/schemas/layouts/layout_file.py |  |
| `stackops.utils.schemas.layouts.layout_types` | `python-api` | `high` | api-doc, classes:4, funcs:3 | src/stackops/utils/schemas/layouts/layout_types.py |  |
| `stackops.utils.schemas.repos.repos_types` | `python-api` | `high` | api-doc, classes:5 | src/stackops/utils/schemas/repos/repos_types.py |  |
| `stackops.utils.schemas.startup.startup_constants` | `python-api-candidate` | `medium` | - | src/stackops/utils/schemas/startup/startup_constants.py |  |
| `stackops.utils.schemas.startup.startup_file` | `python-api-candidate` | `medium` | funcs:2 | src/stackops/utils/schemas/startup/startup_file.py |  |
| `stackops.utils.schemas.startup.startup_types` | `python-api-candidate` | `medium` | classes:2 | src/stackops/utils/schemas/startup/startup_types.py |  |
| `stackops.utils.schemas.yaml_document` | `python-api` | `high` | api-doc, classes:1, funcs:1 | src/stackops/utils/schemas/yaml_document.py |  |
| `stackops.utils.schemas.yaml_schema` | `python-api` | `high` | api-doc, funcs:4 | src/stackops/utils/schemas/yaml_schema.py | Was `utils.yaml_schema`; moved under `schemas/`. |
| `stackops.utils.ssh_utils.abc` | `python-api` | `high` | api-doc, classes:1 | src/stackops/utils/ssh_utils/abc.py |  |
| `stackops.utils.ssh_utils.connection_target` | `python-api` | `high` | api-doc, classes:2, funcs:9 | src/stackops/utils/ssh_utils/connection_target.py |  |
| `stackops.utils.ssh_utils.host_key_verification` | `python-api` | `high` | api-doc, classes:2, funcs:5 | src/stackops/utils/ssh_utils/host_key_verification.py |  |
| `stackops.utils.ssh_utils.open_ssh_command` | `python-api` | `high` | api-doc, classes:1, funcs:3 | src/stackops/utils/ssh_utils/open_ssh_command.py |  |
| `stackops.utils.ssh_utils.open_ssh_config` | `python-api` | `high` | api-doc, funcs:5 | src/stackops/utils/ssh_utils/open_ssh_config.py |  |
| `stackops.utils.ssh_utils.server_install` | `python-api` | `high` | api-doc, funcs:2 | src/stackops/utils/ssh_utils/server_install.py |  |
| `stackops.utils.ssh_utils.ssh_port_activation` | `python-api` | `high` | api-doc, funcs:1 | src/stackops/utils/ssh_utils/ssh_port_activation.py |  |
| `stackops.utils.ssh_utils.ssh_port_apply` | `python-api` | `high` | api-doc, classes:1, funcs:6 | src/stackops/utils/ssh_utils/ssh_port_apply.py |  |
| `stackops.utils.ssh_utils.ssh_port_change` | `python-api` | `high` | api-doc, funcs:2 | src/stackops/utils/ssh_utils/ssh_port_change.py |  |
| `stackops.utils.ssh_utils.ssh_port_commands` | `python-api` | `high` | api-doc, funcs:9 | src/stackops/utils/ssh_utils/ssh_port_commands.py |  |
| `stackops.utils.ssh_utils.ssh_port_firewall` | `python-api` | `high` | api-doc, funcs:6 | src/stackops/utils/ssh_utils/ssh_port_firewall.py |  |
| `stackops.utils.ssh_utils.ssh_port_packet_filter` | `python-api` | `high` | api-doc, funcs:2 | src/stackops/utils/ssh_utils/ssh_port_packet_filter.py |  |
| `stackops.utils.ssh_utils.ssh_port_preflight` | `python-api` | `high` | api-doc, classes:2, funcs:10 | src/stackops/utils/ssh_utils/ssh_port_preflight.py |  |
| `stackops.utils.ssh_utils.ssh_port_selinux` | `python-api` | `high` | api-doc, funcs:2 | src/stackops/utils/ssh_utils/ssh_port_selinux.py |  |
| `stackops.utils.ssh_utils.ssh_port_service` | `python-api` | `high` | api-doc, classes:1, funcs:5 | src/stackops/utils/ssh_utils/ssh_port_service.py |  |
| `stackops.utils.ssh_utils.ssh_port_wsl_firewall` | `python-api` | `high` | api-doc, funcs:1 | src/stackops/utils/ssh_utils/ssh_port_wsl_firewall.py |  |
| `stackops.utils.ssh_utils.transfer_archive` | `python-api` | `high` | api-doc, funcs:3 | src/stackops/utils/ssh_utils/transfer_archive.py |  |
| `stackops.utils.ssh_utils.windows_server_install` | `python-api` | `high` | api-doc, funcs:1 | src/stackops/utils/ssh_utils/windows_server_install.py |  |
| `stackops.utils.ssh_utils.wsl_helper` | `python-api` | `high` | api-doc, funcs:15 | src/stackops/utils/ssh_utils/wsl_helper.py |  |
| `stackops.version` | `python-api-candidate` | `medium` | funcs:1 | src/stackops/version.py |  |

## Clear CLI And CLI Helpers

These **887** modules are likely direct CLI modules or CLI-only implementation helpers.

| Module | Marker | Label | Confidence | Signals | Path | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `stackops.scripts.python.agents` | `cli` | `cli-entrypoint` | `high` | entry:agents, typer, typer-app, cli-registration, get_app, main, __main__, classes:1, funcs:21 | src/stackops/scripts/python/agents.py |  |
| `stackops.scripts.python.agents_browser` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:12 | src/stackops/scripts/python/agents_browser.py |  |
| `stackops.scripts.python.agents_computer` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:3 | src/stackops/scripts/python/agents_computer.py |  |
| `stackops.scripts.python.agents_config_files` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:4 | src/stackops/scripts/python/agents_config_files.py |  |
| `stackops.scripts.python.agents_depoison` | `cli` | `cli-module` | `high` | typer, funcs:2 | src/stackops/scripts/python/agents_depoison.py |  |
| `stackops.scripts.python.agents_followup` | `cli` | `cli-module` | `high` | typer, classes:1, funcs:3 | src/stackops/scripts/python/agents_followup.py |  |
| `stackops.scripts.python.agents_iter` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:5 | src/stackops/scripts/python/agents_iter.py |  |
| `stackops.scripts.python.agents_local` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:3 | src/stackops/scripts/python/agents_local.py |  |
| `stackops.scripts.python.agents_local_vllm` | `cli` | `cli-module` | `high` | typer, funcs:3 | src/stackops/scripts/python/agents_local_vllm.py |  |
| `stackops.scripts.python.agents_second_brain` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:6 | src/stackops/scripts/python/agents_second_brain.py |  |
| `stackops.scripts.python.agents_status` | `cli` | `cli-module` | `high` | typer, funcs:1 | src/stackops/scripts/python/agents_status.py |  |
| `stackops.scripts.python.agents_test_runtime` | `cli` | `cli-module` | `high` | typer, typer-app, get_app, classes:1, funcs:9 | src/stackops/scripts/python/agents_test_runtime.py |  |
| `stackops.scripts.python.agents_type_fix` | `cli` | `cli-module` | `high` | typer, typer-app, get_app, funcs:2 | src/stackops/scripts/python/agents_type_fix.py |  |
| `stackops.scripts.python.ai.constants` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/ai/constants.py |  |
| `stackops.scripts.python.ai.initai` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/ai/initai.py |  |
| `stackops.scripts.python.ai.initai_artifacts` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/ai/initai_artifacts.py |  |
| `stackops.scripts.python.ai.initai_frameworks` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/ai/initai_frameworks.py |  |
| `stackops.scripts.python.ai.initai_models` | `cli-helper` | `cli-helper` | `medium` | classes:3 | src/stackops/scripts/python/ai/initai_models.py |  |
| `stackops.scripts.python.ai.initai_rich_output` | `cli-helper` | `cli-helper` | `medium` | funcs:10 | src/stackops/scripts/python/ai/initai_rich_output.py |  |
| `stackops.scripts.python.ai.scripts.constants` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/ai/scripts/constants.py |  |
| `stackops.scripts.python.ai.scripts.dashboard` | `cli-helper` | `cli-helper` | `medium` | funcs:6 | src/stackops/scripts/python/ai/scripts/dashboard.py |  |
| `stackops.scripts.python.ai.scripts.lint_and_type_check` | `cli-helper` | `cli-helper` | `medium` | main, __main__, funcs:10 | src/stackops/scripts/python/ai/scripts/lint_and_type_check.py |  |
| `stackops.scripts.python.ai.scripts.models` | `cli-helper` | `cli-helper` | `medium` | __all__, classes:3 | src/stackops/scripts/python/ai/scripts/models.py |  |
| `stackops.scripts.python.ai.scripts.models_config` | `cli-helper` | `cli-helper` | `medium` | funcs:16 | src/stackops/scripts/python/ai/scripts/models_config.py |  |
| `stackops.scripts.python.ai.scripts.models_core` | `cli-helper` | `cli-helper` | `medium` | classes:2 | src/stackops/scripts/python/ai/scripts/models_core.py |  |
| `stackops.scripts.python.ai.scripts.models_diagnostics` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:8 | src/stackops/scripts/python/ai/scripts/models_diagnostics.py |  |
| `stackops.scripts.python.ai.scripts.models_json` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:5 | src/stackops/scripts/python/ai/scripts/models_json.py |  |
| `stackops.scripts.python.ai.scripts.models_reports` | `cli-helper` | `cli-helper` | `medium` | funcs:10 | src/stackops/scripts/python/ai/scripts/models_reports.py |  |
| `stackops.scripts.python.ai.scripts.paths` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/ai/scripts/paths.py |  |
| `stackops.scripts.python.ai.scripts.report_schema` | `cli-helper` | `cli-helper` | `medium` | classes:2 | src/stackops/scripts/python/ai/scripts/report_schema.py |  |
| `stackops.scripts.python.ai.scripts.run_reports` | `cli-helper` | `cli-helper` | `medium` | classes:8, funcs:1 | src/stackops/scripts/python/ai/scripts/run_reports.py |  |
| `stackops.scripts.python.ai.scripts.tool_versions` | `cli-helper` | `cli-helper` | `medium` | classes:3, funcs:5 | src/stackops/scripts/python/ai/scripts/tool_versions.py |  |
| `stackops.scripts.python.ai.solutions.antigravity.antigravity` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/ai/solutions/antigravity/antigravity.py |  |
| `stackops.scripts.python.ai.solutions.auggie.auggie` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/ai/solutions/auggie/auggie.py |  |
| `stackops.scripts.python.ai.solutions.claude.claude` | `cli-helper` | `cli-helper` | `medium` | funcs:5 | src/stackops/scripts/python/ai/solutions/claude/claude.py |  |
| `stackops.scripts.python.ai.solutions.cline.cline` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/ai/solutions/cline/cline.py |  |
| `stackops.scripts.python.ai.solutions.codex.codex` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/ai/solutions/codex/codex.py |  |
| `stackops.scripts.python.ai.solutions.copilot.github_copilot` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/ai/solutions/copilot/github_copilot.py |  |
| `stackops.scripts.python.ai.solutions.cortex.cortex` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/ai/solutions/cortex/cortex.py |  |
| `stackops.scripts.python.ai.solutions.crush.crush` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/ai/solutions/crush/crush.py |  |
| `stackops.scripts.python.ai.solutions.cursor.cursors` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/ai/solutions/cursor/cursors.py |  |
| `stackops.scripts.python.ai.solutions.deepseek.deepseek` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/ai/solutions/deepseek/deepseek.py |  |
| `stackops.scripts.python.ai.solutions.droid.droid` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/ai/solutions/droid/droid.py |  |
| `stackops.scripts.python.ai.solutions.forge.forge` | `cli-helper` | `cli-helper` | `medium` | funcs:4 | src/stackops/scripts/python/ai/solutions/forge/forge.py |  |
| `stackops.scripts.python.ai.solutions.kilocode.kilocode` | `cli-helper` | `cli-helper` | `medium` | funcs:4 | src/stackops/scripts/python/ai/solutions/kilocode/kilocode.py |  |
| `stackops.scripts.python.ai.solutions.maki.maki` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/ai/solutions/maki/maki.py |  |
| `stackops.scripts.python.ai.solutions.muse.muse` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/ai/solutions/muse/muse.py |  |
| `stackops.scripts.python.ai.solutions.omp.constants` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/ai/solutions/omp/constants.py |  |
| `stackops.scripts.python.ai.solutions.omp.omp` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/ai/solutions/omp/omp.py |  |
| `stackops.scripts.python.ai.solutions.opencode.opencode` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/ai/solutions/opencode/opencode.py |  |
| `stackops.scripts.python.ai.solutions.opencode.openrouter_config` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/ai/solutions/opencode/openrouter_config.py |  |
| `stackops.scripts.python.ai.solutions.oz.oz` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/ai/solutions/oz/oz.py |  |
| `stackops.scripts.python.ai.solutions.pi.constants` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/ai/solutions/pi/constants.py |  |
| `stackops.scripts.python.ai.solutions.pi.pi` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/ai/solutions/pi/pi.py |  |
| `stackops.scripts.python.ai.solutions.prime_agent.prime_agent` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/ai/solutions/prime_agent/prime_agent.py |  |
| `stackops.scripts.python.ai.solutions.q.amazon_q` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/ai/solutions/q/amazon_q.py |  |
| `stackops.scripts.python.ai.solutions.qwen_code.qwen_code` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/ai/solutions/qwen_code/qwen_code.py |  |
| `stackops.scripts.python.ai.solutions.warp.warp` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/ai/solutions/warp/warp.py |  |
| `stackops.scripts.python.ai.utils.generate_files` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, __main__, funcs:1 | src/stackops/scripts/python/ai/utils/generate_files.py |  |
| `stackops.scripts.python.ai.utils.generate_files_content` | `cli-helper` | `cli-helper` | `medium` | funcs:5 | src/stackops/scripts/python/ai/utils/generate_files_content.py |  |
| `stackops.scripts.python.ai.utils.generate_files_utils` | `cli-helper` | `cli-helper` | `medium` | funcs:8 | src/stackops/scripts/python/ai/utils/generate_files_utils.py |  |
| `stackops.scripts.python.ai.utils.generic` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/ai/utils/generic.py |  |
| `stackops.scripts.python.ai.utils.shared` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/ai/utils/shared.py |  |
| `stackops.scripts.python.ai.utils.vscode_tasks` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/ai/utils/vscode_tasks.py |  |
| `stackops.scripts.python.cloud` | `cli` | `cli-entrypoint` | `high` | entry:cloud, typer, typer-app, cli-registration, get_app, main, __main__, funcs:6 | src/stackops/scripts/python/cloud.py |  |
| `stackops.scripts.python.devops` | `cli` | `cli-entrypoint` | `high` | entry:devops, typer, typer-app, cli-registration, get_app, main, __main__, classes:1, funcs:14 | src/stackops/scripts/python/devops.py |  |
| `stackops.scripts.python.enums` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/enums.py |  |
| `stackops.scripts.python.fire_jobs` | `cli` | `cli-entrypoint` | `high` | entry:fire, typer, typer-app, cli-registration, get_app, main, __main__, funcs:7 | src/stackops/scripts/python/fire_jobs.py |  |
| `stackops.scripts.python.ftpx` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, main, __main__, funcs:4 | src/stackops/scripts/python/ftpx.py |  |
| `stackops.scripts.python.graph.cli_graph_apps` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:6 | src/stackops/scripts/python/graph/cli_graph_apps.py |  |
| `stackops.scripts.python.graph.cli_graph_eval` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/graph/cli_graph_eval.py |  |
| `stackops.scripts.python.graph.cli_graph_managed_files` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/graph/cli_graph_managed_files.py |  |
| `stackops.scripts.python.graph.cli_graph_node_utils` | `cli-helper` | `cli-helper` | `medium` | funcs:6 | src/stackops/scripts/python/graph/cli_graph_node_utils.py |  |
| `stackops.scripts.python.graph.cli_graph_nodes` | `cli-helper` | `cli-helper` | `medium` | funcs:5 | src/stackops/scripts/python/graph/cli_graph_nodes.py |  |
| `stackops.scripts.python.graph.cli_graph_policy` | `cli-helper` | `cli-helper` | `medium` | funcs:4 | src/stackops/scripts/python/graph/cli_graph_policy.py |  |
| `stackops.scripts.python.graph.cli_graph_registration` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/graph/cli_graph_registration.py |  |
| `stackops.scripts.python.graph.cli_graph_resolver` | `cli-helper` | `cli-helper` | `medium` | funcs:12 | src/stackops/scripts/python/graph/cli_graph_resolver.py |  |
| `stackops.scripts.python.graph.cli_graph_shared` | `cli-helper` | `cli-helper` | `medium` | classes:7 | src/stackops/scripts/python/graph/cli_graph_shared.py |  |
| `stackops.scripts.python.graph.cli_graph_signature` | `cli-helper` | `cli-helper` | `medium` | funcs:10 | src/stackops/scripts/python/graph/cli_graph_signature.py |  |
| `stackops.scripts.python.graph.cli_graph_targets` | `cli-helper` | `cli-helper` | `medium` | funcs:8 | src/stackops/scripts/python/graph/cli_graph_targets.py |  |
| `stackops.scripts.python.graph.cli_graph_tree` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/graph/cli_graph_tree.py |  |
| `stackops.scripts.python.graph.cli_graph_values` | `cli-helper` | `cli-helper` | `medium` | funcs:4 | src/stackops/scripts/python/graph/cli_graph_values.py |  |
| `stackops.scripts.python.graph.generate_cli_graph` | `cli-helper` | `cli-helper` | `medium` | main, __main__, funcs:1 | src/stackops/scripts/python/graph/generate_cli_graph.py |  |
| `stackops.scripts.python.graph.python_api_graph` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:28 | src/stackops/scripts/python/graph/python_api_graph.py |  |
| `stackops.scripts.python.graph.visualize.cli_graph_app` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, main, __main__, funcs:9 | src/stackops/scripts/python/graph/visualize/cli_graph_app.py |  |
| `stackops.scripts.python.graph.visualize.cli_graph_execute` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, funcs:6 | src/stackops/scripts/python/graph/visualize/cli_graph_execute.py |  |
| `stackops.scripts.python.graph.visualize.cli_graph_search` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:31 | src/stackops/scripts/python/graph/visualize/cli_graph_search.py |  |
| `stackops.scripts.python.graph.visualize.cli_graph_typer_app` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, funcs:1 | src/stackops/scripts/python/graph/visualize/cli_graph_typer_app.py |  |
| `stackops.scripts.python.graph.visualize.dot_export` | `cli-helper` | `cli-helper` | `medium` | funcs:5 | src/stackops/scripts/python/graph/visualize/dot_export.py |  |
| `stackops.scripts.python.graph.visualize.graph_data` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:8 | src/stackops/scripts/python/graph/visualize/graph_data.py |  |
| `stackops.scripts.python.graph.visualize.graph_paths` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/graph/visualize/graph_paths.py |  |
| `stackops.scripts.python.graph.visualize.helpers_navigator.cli_graph_loader` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:14 | src/stackops/scripts/python/graph/visualize/helpers_navigator/cli_graph_loader.py |  |
| `stackops.scripts.python.graph.visualize.helpers_navigator.command_builder` | `cli-helper` | `cli-helper` | `medium` | classes:1 | src/stackops/scripts/python/graph/visualize/helpers_navigator/command_builder.py |  |
| `stackops.scripts.python.graph.visualize.helpers_navigator.command_detail` | `cli-helper` | `cli-helper` | `medium` | classes:1 | src/stackops/scripts/python/graph/visualize/helpers_navigator/command_detail.py |  |
| `stackops.scripts.python.graph.visualize.helpers_navigator.command_tree` | `cli-helper` | `cli-helper` | `medium` | classes:1 | src/stackops/scripts/python/graph/visualize/helpers_navigator/command_tree.py |  |
| `stackops.scripts.python.graph.visualize.helpers_navigator.data_models` | `cli-helper` | `cli-helper` | `medium` | classes:2 | src/stackops/scripts/python/graph/visualize/helpers_navigator/data_models.py |  |
| `stackops.scripts.python.graph.visualize.helpers_navigator.devops_navigator` | `cli-helper` | `cli-helper` | `medium` | main, __main__, funcs:1 | src/stackops/scripts/python/graph/visualize/helpers_navigator/devops_navigator.py |  |
| `stackops.scripts.python.graph.visualize.helpers_navigator.main_app` | `cli-helper` | `cli-helper` | `medium` | classes:1 | src/stackops/scripts/python/graph/visualize/helpers_navigator/main_app.py |  |
| `stackops.scripts.python.graph.visualize.helpers_navigator.search_bar` | `cli-helper` | `cli-helper` | `medium` | classes:1 | src/stackops/scripts/python/graph/visualize/helpers_navigator/search_bar.py |  |
| `stackops.scripts.python.graph.visualize.plotly_browser` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:11 | src/stackops/scripts/python/graph/visualize/plotly_browser.py |  |
| `stackops.scripts.python.graph.visualize.plotly_views` | `cli` | `cli-module` | `high` | typer, __main__, funcs:2 | src/stackops/scripts/python/graph/visualize/plotly_views.py |  |
| `stackops.scripts.python.graph.visualize.python_api_graph_app` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, main, __main__, funcs:10 | src/stackops/scripts/python/graph/visualize/python_api_graph_app.py |  |
| `stackops.scripts.python.graph.visualize.python_api_graph_search` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:15 | src/stackops/scripts/python/graph/visualize/python_api_graph_search.py |  |
| `stackops.scripts.python.graph.visualize.rich_tree` | `cli-helper` | `cli-helper` | `medium` | funcs:4 | src/stackops/scripts/python/graph/visualize/rich_tree.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_codex` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agentic_frameworks/fire_codex.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_copilot` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agentic_frameworks/fire_copilot.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_cortex` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agentic_frameworks/fire_cortex.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_crush` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agentic_frameworks/fire_crush.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_cursor_agents` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agentic_frameworks/fire_cursor_agents.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_deepseek` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agentic_frameworks/fire_deepseek.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_maki` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agentic_frameworks/fire_maki.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_pi` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agentic_frameworks/fire_pi.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_prime_agent` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agentic_frameworks/fire_prime_agent.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_qwen` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agentic_frameworks/fire_qwen.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_agent_ops_cache` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:5 | src/stackops/scripts/python/helpers/helpers_agents/agents_agent_ops_cache.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_ask_impl` | `cli-helper` | `cli-helper` | `medium` | funcs:10 | src/stackops/scripts/python/helpers/helpers_agents/agents_ask_impl.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_app_window_models` | `cli-helper` | `cli-helper` | `medium` | classes:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_app_window_models.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_app_windows` | `cli-helper` | `cli-helper` | `medium` | funcs:5 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_app_windows.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_apple_events_windows` | `cli-helper` | `cli-helper` | `medium` | classes:3, funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_apple_events_windows.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_batch` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_batch.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_bidi_windows` | `cli-helper` | `cli-helper` | `medium` | classes:3, funcs:7 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_bidi_windows.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_cdp_windows` | `cli-helper` | `cli-helper` | `medium` | classes:3, funcs:6 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_cdp_windows.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_close` | `cli-helper` | `cli-helper` | `medium` | classes:5, funcs:9 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_close.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_constants` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_constants.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_detached_launch` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_detached_launch.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_detached_processes` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:17 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_detached_processes.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_endpoint_rpc` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_endpoint_rpc.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_guides` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_guides.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_hosts` | `cli-helper` | `cli-helper` | `medium` | funcs:5 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_hosts.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_impl` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:8 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_impl.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_json` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_json.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_launch` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_launch.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_details` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_launch_details.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_identity` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_launch_identity.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_lock` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_launch_lock.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_models` | `cli-helper` | `cli-helper` | `medium` | classes:4, funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_launch_models.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_records` | `cli-helper` | `cli-helper` | `medium` | classes:4, funcs:5 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_launch_records.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_runtime` | `cli-helper` | `cli-helper` | `medium` | funcs:12 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_launch_runtime.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_lifecycle` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_lifecycle.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_multiplexed_launch` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_multiplexed_launch.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_native_profiles` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_native_profiles.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_native_replication` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_native_replication.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_native_selection` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_native_selection.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_process_scan` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_process_scan.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_profile_filesystem` | `cli-helper` | `cli-helper` | `medium` | funcs:7 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_profile_filesystem.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_profile_inventory` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_profile_inventory.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_profile_inventory_output` | `cli-helper` | `cli-helper` | `medium` | funcs:5 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_profile_inventory_output.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_profile_listing` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_profile_listing.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_profile_sign_in` | `cli-helper` | `cli-helper` | `medium` | classes:4, funcs:7 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_profile_sign_in.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_profiles` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:9 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_profiles.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_resolution` | `cli-helper` | `cli-helper` | `medium` | funcs:9 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_resolution.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_reuse` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_reuse.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_rich_output` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_rich_output.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_status` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:6 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_status.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_tabs` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_tabs.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_temporary_profiles` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_temporary_profiles.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_tmux_common` | `cli-helper` | `cli-helper` | `medium` | funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_tmux_common.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_tmux_host` | `cli-helper` | `cli-helper` | `medium` | funcs:6 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_tmux_host.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_tuios_host` | `cli-helper` | `cli-helper` | `medium` | funcs:6 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_tuios_host.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_windows_desktop` | `cli-helper` | `cli-helper` | `medium` | funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_windows_desktop.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_zellij_host` | `cli-helper` | `cli-helper` | `medium` | funcs:5 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_zellij_host.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_computer_constants` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_agents/agents_computer_constants.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_computer_status` | `cli-helper` | `cli-helper` | `medium` | classes:3, funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_computer_status.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_create_artifacts` | `cli-helper` | `cli-helper` | `medium` | classes:4, funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_create_artifacts.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_create_inputs` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:7 | src/stackops/scripts/python/helpers/helpers_agents/agents_create_inputs.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_create_replacement` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_create_replacement.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.agy` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/agy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.amazon_q` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/amazon_q.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.auggie` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/auggie.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.claude` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/claude.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.cline` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/cline.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.codex` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/codex.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.codex_config` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/codex_config.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.codex_context` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/codex_context.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.codex_plugin_cache` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/codex_plugin_cache.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.codex_plugins` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/codex_plugins.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.copilot` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/copilot.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.cortex` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/cortex.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.crush` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/crush.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.cursor_agent` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/cursor_agent.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.deepseek` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/deepseek.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.deepseek_cleanup` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/deepseek_cleanup.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.deepseek_config` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/deepseek_config.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.droid` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/droid.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.forge` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/forge.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.kilocode` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/kilocode.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.maki` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/maki.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.muse` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/muse.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.omp` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/omp.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.omp_config` | `cli-helper` | `cli-helper` | `medium` | funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/omp_config.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.omp_context` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/omp_context.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.omp_plugin_state` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:7 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/omp_plugin_state.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.omp_plugins` | `cli-helper` | `cli-helper` | `medium` | funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/omp_plugins.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.opencode` | `cli-helper` | `cli-helper` | `medium` | funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/opencode.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.opencode_config` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/opencode_config.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.oz` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/oz.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.pi` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/pi.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.pi_context` | `cli-helper` | `cli-helper` | `medium` | funcs:5 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/pi_context.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.pi_settings` | `cli-helper` | `cli-helper` | `medium` | funcs:7 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/pi_settings.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.prime_agent` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/prime_agent.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.qwen` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/qwen.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_apply` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/cleanup_apply.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_configuration` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/cleanup_configuration.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_documents` | `cli-helper` | `cli-helper` | `medium` | funcs:5 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/cleanup_documents.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_html` | `cli-helper` | `cli-helper` | `medium` | classes:4, funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/cleanup_html.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_interactive` | `cli` | `cli-module` | `high` | typer, classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/cleanup_interactive.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_models` | `cli-helper` | `cli-helper` | `medium` | classes:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/cleanup_models.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_output` | `cli-helper` | `cli-helper` | `medium` | funcs:5 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/cleanup_output.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_paths` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/cleanup_paths.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_plan` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/cleanup_plan.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_resource_roots` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/cleanup_resource_roots.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_resources` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/cleanup_resources.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_scope` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/cleanup_scope.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_sizes` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/cleanup_sizes.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_workspace` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/cleanup_workspace.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.command` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/command.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.constants` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/constants.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.context_estimate` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:5 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/context_estimate.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.extra_configuration` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/extra_configuration.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.claude_plugins` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/hooks/claude_plugins.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.cline` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/hooks/cline.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.codex_hooks` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/hooks/codex_hooks.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.codex_plugin_hooks` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/hooks/codex_plugin_hooks.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.discovery` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/hooks/discovery.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.extended_constants` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/hooks/extended_constants.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.extension_sources` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/hooks/extension_sources.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.extensions` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/hooks/extensions.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.json_inventory` | `cli-helper` | `cli-helper` | `medium` | funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/hooks/json_inventory.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.models` | `cli-helper` | `cli-helper` | `medium` | classes:5 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/hooks/models.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.omp_hooks` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/hooks/omp_hooks.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.paths` | `cli-helper` | `cli-helper` | `medium` | funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/hooks/paths.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.sources` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/hooks/sources.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.html_report` | `cli-helper` | `cli-helper` | `medium` | classes:4, funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/html_report.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.mcp_servers` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/mcp_servers.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.models` | `cli-helper` | `cli-helper` | `medium` | classes:6 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/models.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.registry` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/registry.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.resource_inventory` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/resource_inventory.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.rich_output` | `cli-helper` | `cli-helper` | `medium` | funcs:10 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/rich_output.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.scanning` | `cli-helper` | `cli-helper` | `medium` | funcs:11 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/scanning.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.standard` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/standard.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.tui_cleanup` | `cli-helper` | `cli-helper` | `medium` | funcs:6 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/tui_cleanup.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.tui_cleanup_browser` | `cli-helper` | `cli-helper` | `medium` | classes:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/tui_cleanup_browser.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.tui_cleanup_review` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/tui_cleanup_review.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.tui_depoison` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/tui_depoison.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.tui_doctor` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/tui_doctor.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.tui_doctor_data` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/tui_doctor_data.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.tui_doctor_widgets` | `cli-helper` | `cli-helper` | `medium` | classes:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/tui_doctor_widgets.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.tui_launch` | `cli` | `cli-module` | `high` | typer, funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/tui_launch.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_edit_source` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_edit_source.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_impl` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_impl.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_iter_constants` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_agents/agents_iter_constants.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_iter_contract` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_iter_contract.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_iter_herdr` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_iter_herdr.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_iter_herdr_protocol` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:18 | src/stackops/scripts/python/helpers/helpers_agents/agents_iter_herdr_protocol.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_iter_json` | `cli` | `cli-module` | `high` | typer, funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_iter_json.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_iter_models` | `cli-helper` | `cli-helper` | `medium` | classes:11 | src/stackops/scripts/python/helpers/helpers_agents/agents_iter_models.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_iter_plan` | `cli-helper` | `cli-helper` | `medium` | funcs:9 | src/stackops/scripts/python/helpers/helpers_agents/agents_iter_plan.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_iter_records` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:12 | src/stackops/scripts/python/helpers/helpers_agents/agents_iter_records.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_iter_render` | `cli-helper` | `cli-helper` | `medium` | funcs:12 | src/stackops/scripts/python/helpers/helpers_agents/agents_iter_render.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_iter_rich_output` | `cli-helper` | `cli-helper` | `medium` | funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_iter_rich_output.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_iter_selection` | `cli-helper` | `cli-helper` | `medium` | funcs:6 | src/stackops/scripts/python/helpers/helpers_agents/agents_iter_selection.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_iter_service` | `cli-helper` | `cli-helper` | `medium` | funcs:8 | src/stackops/scripts/python/helpers/helpers_agents/agents_iter_service.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_iter_workspace_records` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_iter_workspace_records.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_json` | `cli` | `cli-module` | `high` | typer, funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_json.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_local.catalog` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_local/catalog.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_local.catalog_downloads` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_local/catalog_downloads.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_local.catalog_report` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_local/catalog_report.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_local.constants` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_agents/agents_local/constants.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_local.ollama` | `cli-helper` | `cli-helper` | `medium` | classes:3, funcs:5 | src/stackops/scripts/python/helpers/helpers_agents/agents_local/ollama.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_local.report` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_local/report.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_local.server` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_local/server.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_local.vllm` | `cli-helper` | `cli-helper` | `medium` | classes:3, funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_local/vllm.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_local.vllm_catalog` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_local/vllm_catalog.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_local.vllm_catalog_report` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_local/vllm_catalog_report.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_local.vllm_report` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_local/vllm_report.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_mcp_impl` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_mcp_impl.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_rich_output` | `cli-helper` | `cli-helper` | `medium` | funcs:12 | src/stackops/scripts/python/helpers/helpers_agents/agents_rich_output.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_run_context` | `cli` | `cli-module` | `high` | typer, funcs:18 | src/stackops/scripts/python/helpers/helpers_agents/agents_run_context.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_run_impl` | `cli` | `cli-module` | `high` | typer, funcs:12 | src/stackops/scripts/python/helpers/helpers_agents/agents_run_impl.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_run_interactive` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_run_interactive.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_run_interactive_script` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_run_interactive_script.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_run_pi_monitor` | `cli-helper` | `cli-helper` | `medium` | main, __main__, classes:1, funcs:12 | src/stackops/scripts/python/helpers/helpers_agents/agents_run_pi_monitor.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_run_prompt_catalog` | `cli-helper` | `cli-helper` | `medium` | classes:3, funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_run_prompt_catalog.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_run_sandbox` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_run_sandbox.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_run_skill` | `cli-helper` | `cli-helper` | `medium` | funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_run_skill.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_run_types` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_agents/agents_run_types.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_sandbox` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_sandbox.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_sandbox_prompt_access` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_sandbox_prompt_access.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_second_brain_activity` | `cli-helper` | `cli-helper` | `medium` | classes:3, funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_second_brain_activity.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_second_brain_constants` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_agents/agents_second_brain_constants.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_second_brain_progress` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_second_brain_progress.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_second_brain_records` | `cli-helper` | `cli-helper` | `medium` | classes:3, funcs:6 | src/stackops/scripts/python/helpers/helpers_agents/agents_second_brain_records.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_second_brain_report` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_second_brain_report.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_shell` | `cli-helper` | `cli-helper` | `medium` | funcs:13 | src/stackops/scripts/python/helpers/helpers_agents/agents_shell.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_skill_impl` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:16 | src/stackops/scripts/python/helpers/helpers_agents/agents_skill_impl.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_skill_stackops_backend` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:9 | src/stackops/scripts/python/helpers/helpers_agents/agents_skill_stackops_backend.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_skill_types` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_agents/agents_skill_types.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_aoe` | `cli-helper` | `cli-helper` | `medium` | funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_aoe.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_aoe_acp` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_aoe_acp.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_aoe_inspect` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_aoe_inspect.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_assessment` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_assessment.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_btw` | `cli-helper` | `cli-helper` | `medium` | funcs:7 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_btw.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_collect` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_collect.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_filters` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_filters.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_herdr` | `cli-helper` | `cli-helper` | `medium` | funcs:5 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_herdr.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_herdr_inspect` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_herdr_inspect.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_history` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_history.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_history_claude` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_history_claude.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_history_codex` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_history_codex.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_history_common` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_history_common.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_inspect` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_inspect.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_links` | `cli-helper` | `cli-helper` | `medium` | funcs:7 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_links.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_models` | `cli-helper` | `cli-helper` | `medium` | classes:7 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_models.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_processes` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_processes.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_render` | `cli-helper` | `cli-helper` | `medium` | funcs:10 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_render.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_rich_output` | `cli-helper` | `cli-helper` | `medium` | funcs:5 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_rich_output.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_t3` | `cli-helper` | `cli-helper` | `medium` | funcs:5 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_t3.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_tuios` | `cli-helper` | `cli-helper` | `medium` | funcs:7 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_tuios.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_t3_launch` | `cli` | `cli-module` | `high` | typer, classes:4, funcs:5 | src/stackops/scripts/python/helpers/helpers_agents/agents_t3_launch.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_t3_mcp` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:11 | src/stackops/scripts/python/helpers/helpers_agents/agents_t3_mcp.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_yaml_schemas` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_yaml_schemas.py |  |
| `stackops.scripts.python.helpers.helpers_agents.browser_cdp_relay` | `cli-helper` | `cli-helper` | `medium` | main, __main__, classes:1, funcs:7 | src/stackops/scripts/python/helpers/helpers_agents/browser_cdp_relay.py |  |
| `stackops.scripts.python.helpers.helpers_agents.browser_launchers.brave` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/browser_launchers/brave.py |  |
| `stackops.scripts.python.helpers.helpers_agents.browser_launchers.chrome` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/browser_launchers/chrome.py |  |
| `stackops.scripts.python.helpers.helpers_agents.browser_launchers.common` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/browser_launchers/common.py |  |
| `stackops.scripts.python.helpers.helpers_agents.browser_launchers.edge` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/browser_launchers/edge.py |  |
| `stackops.scripts.python.helpers.helpers_agents.browser_launchers.firefox` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/browser_launchers/firefox.py |  |
| `stackops.scripts.python.helpers.helpers_agents.browser_launchers.models` | `cli-helper` | `cli-helper` | `medium` | classes:3 | src/stackops/scripts/python/helpers/helpers_agents/browser_launchers/models.py |  |
| `stackops.scripts.python.helpers.helpers_agents.browser_launchers.registry` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/browser_launchers/registry.py |  |
| `stackops.scripts.python.helpers.helpers_agents.browser_launchers.safari` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/browser_launchers/safari.py |  |
| `stackops.scripts.python.helpers.helpers_agents.constants` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_agents/constants.py |  |
| `stackops.scripts.python.helpers.helpers_agents.cortex_launch` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/cortex_launch.py |  |
| `stackops.scripts.python.helpers.helpers_agents.cortex_paths` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/cortex_paths.py |  |
| `stackops.scripts.python.helpers.helpers_agents.deepseek_launch` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/deepseek_launch.py |  |
| `stackops.scripts.python.helpers.helpers_agents.deepseek_mcp` | `cli-helper` | `cli-helper` | `medium` | funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/deepseek_mcp.py |  |
| `stackops.scripts.python.helpers.helpers_agents.fire_agents_help_launch` | `cli-helper` | `cli-helper` | `medium` | funcs:10 | src/stackops/scripts/python/helpers/helpers_agents/fire_agents_help_launch.py |  |
| `stackops.scripts.python.helpers.helpers_agents.maki_launch` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/maki_launch.py |  |
| `stackops.scripts.python.helpers.helpers_agents.maki_mcp` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/maki_mcp.py |  |
| `stackops.scripts.python.helpers.helpers_agents.maki_paths` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/maki_paths.py |  |
| `stackops.scripts.python.helpers.helpers_agents.mcp_catalog` | `cli-helper` | `cli-helper` | `medium` | funcs:16 | src/stackops/scripts/python/helpers/helpers_agents/mcp_catalog.py |  |
| `stackops.scripts.python.helpers.helpers_agents.mcp_install` | `cli-helper` | `cli-helper` | `medium` | funcs:37 | src/stackops/scripts/python/helpers/helpers_agents/mcp_install.py |  |
| `stackops.scripts.python.helpers.helpers_agents.mcp_types` | `cli-helper` | `cli-helper` | `medium` | classes:5 | src/stackops/scripts/python/helpers/helpers_agents/mcp_types.py |  |
| `stackops.scripts.python.helpers.helpers_agents.prime_agent_launch` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/prime_agent_launch.py |  |
| `stackops.scripts.python.helpers.helpers_agents.prime_agent_mcp` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/prime_agent_mcp.py |  |
| `stackops.scripts.python.helpers.helpers_agents.prime_agent_paths` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/prime_agent_paths.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.auggie.auggie_privacy` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/auggie/auggie_privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.chatgpt.chatgpt_privacy` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/chatgpt/chatgpt_privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.cline.cline_privacy` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/cline/cline_privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.codex.codex_privacy` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/codex/codex_privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.common.json_settings` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/common/json_settings.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.common.privacy_orchestrator` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/common/privacy_orchestrator.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.cursor.cursor_privacy` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/cursor/cursor_privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.droid.droid_privacy` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/droid/droid_privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.kilocode.kilocode_privacy` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/kilocode/kilocode_privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.mods.mods_privacy` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/mods/mods_privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.q.q_privacy` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/q/q_privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.qwen.qwen_privacy` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/qwen/qwen_privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.privacy` | `cli-helper` | `cli-helper` | `medium` | __main__, __all__ | src/stackops/scripts/python/helpers/helpers_agents/privacy/privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.reasoning_capabilities` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:6 | src/stackops/scripts/python/helpers/helpers_agents/reasoning_capabilities.py |  |
| `stackops.scripts.python.helpers.helpers_agents.type_check_context` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/type_check_context.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.backup_config` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:22 | src/stackops/scripts/python/helpers/helpers_cloud/backup_config.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.backup_registration` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:5 | src/stackops/scripts/python/helpers/helpers_cloud/backup_registration.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.backup_remote` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_cloud/backup_remote.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.backup_selection` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:2 | src/stackops/scripts/python/helpers/helpers_cloud/backup_selection.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.cloud_copy` | `cli-helper` | `cli-helper` | `medium` | main, classes:1, funcs:10 | src/stackops/scripts/python/helpers/helpers_cloud/cloud_copy.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.cloud_copy_artifacts` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:6 | src/stackops/scripts/python/helpers/helpers_cloud/cloud_copy_artifacts.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.cloud_copy_summary` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_cloud/cloud_copy_summary.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.cloud_helpers` | `cli-helper` | `cli-helper` | `medium` | funcs:8 | src/stackops/scripts/python/helpers/helpers_cloud/cloud_helpers.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.cloud_mount` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, __main__, funcs:4 | src/stackops/scripts/python/helpers/helpers_cloud/cloud_mount.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.cloud_mount_background` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:1 | src/stackops/scripts/python/helpers/helpers_cloud/cloud_mount_background.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.cloud_mount_directory` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_cloud/cloud_mount_directory.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.cloud_mount_tmux` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_cloud/cloud_mount_tmux.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.cloud_mount_tuios` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_cloud/cloud_mount_tuios.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.cloud_path_resolver` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_cloud/cloud_path_resolver.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.cloud_sync` | `cli-helper` | `cli-helper` | `medium` | main, funcs:1 | src/stackops/scripts/python/helpers/helpers_cloud/cloud_sync.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_backup_retrieve` | `cli-helper` | `cli-helper` | `medium` | __main__, funcs:6 | src/stackops/scripts/python/helpers/helpers_devops/cli_backup_retrieve.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_cloudflare` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:6 | src/stackops/scripts/python/helpers/helpers_devops/cli_cloudflare.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_cloudflare_tunnel` | `cli` | `cli-module` | `high` | typer, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/cli_cloudflare_tunnel.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/cli_config.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_collect` | `cli` | `cli-module` | `high` | typer, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_dotfile_collect.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_mapper` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, __main__, funcs:15 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_dotfile_mapper.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_status` | `cli` | `cli-module` | `high` | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_dotfile_status.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_status_data` | `cli-helper` | `cli-helper` | `medium` | classes:7, funcs:9 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_dotfile_status_data.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_status_render` | `cli-helper` | `cli-helper` | `medium` | funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_dotfile_status_render.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_status_render_radar` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_dotfile_status_render_radar.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_transfer` | `cli` | `cli-module` | `high` | typer, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_dotfile_transfer.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_dotfiles` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_dotfiles.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_dump` | `cli` | `cli-module` | `high` | typer, funcs:2 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_dump.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_edit` | `cli` | `cli-module` | `high` | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_edit.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_files` | `cli` | `cli-module` | `high` | typer, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_files.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_init_script` | `cli` | `cli-module` | `high` | typer, funcs:2 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_init_script.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_mount` | `cli` | `cli-module` | `high` | typer, funcs:5 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_mount.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_actions` | `cli` | `cli-module` | `high` | typer, classes:1, funcs:22 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets_actions.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_add` | `cli` | `cli-module` | `high` | typer, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets_add.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_candidates` | `cli` | `cli-module` | `high` | typer, __all__, classes:2, funcs:21 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets_candidates.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_constants` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets_constants.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_delete` | `cli` | `cli-module` | `high` | typer, classes:2, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets_delete.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_errors` | `cli` | `cli-module` | `high` | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets_errors.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_files` | `cli` | `cli-module` | `high` | typer, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets_files.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_json` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets_json.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_prompts` | `cli` | `cli-module` | `high` | typer, funcs:10 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets_prompts.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_rotate` | `cli` | `cli-module` | `high` | typer, classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets_rotate.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_search` | `cli` | `cli-module` | `high` | typer, funcs:2 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets_search.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_selection` | `cli` | `cli-module` | `high` | typer, classes:2, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets_selection.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_subset_selection` | `cli` | `cli-module` | `high` | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets_subset_selection.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_support` | `cli` | `cli-module` | `high` | typer, classes:2, funcs:31 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets_support.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_validation` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets_validation.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_setup` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_setup.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_setup_config` | `cli` | `cli-module` | `high` | typer, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_setup_config.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_setup_domains` | `cli` | `cli-module` | `high` | typer, funcs:5 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_setup_domains.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_setup_multiplexer` | `cli` | `cli-module` | `high` | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_setup_multiplexer.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_terminal` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:8 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_terminal.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_tmux` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, classes:1, funcs:19 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_tmux.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_data` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:7 | src/stackops/scripts/python/helpers/helpers_devops/cli_data.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_data_display` | `cli` | `cli-module` | `high` | typer, funcs:2 | src/stackops/scripts/python/helpers/helpers_devops/cli_data_display.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_data_edit` | `cli` | `cli-module` | `high` | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/cli_data_edit.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_data_encrypt` | `cli` | `cli-module` | `high` | typer, funcs:12 | src/stackops/scripts/python/helpers/helpers_devops/cli_data_encrypt.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_data_encrypt_output` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/cli_data_encrypt_output.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_data_subset` | `cli` | `cli-module` | `high` | typer, funcs:8 | src/stackops/scripts/python/helpers/helpers_devops/cli_data_subset.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_data_subset_io` | `cli` | `cli-module` | `high` | typer, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/cli_data_subset_io.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_device` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:5 | src/stackops/scripts/python/helpers/helpers_devops/cli_device.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_interactive_picker` | `cli` | `cli-module` | `high` | typer, classes:1, funcs:7 | src/stackops/scripts/python/helpers/helpers_devops/cli_interactive_picker.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_nw` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/cli_nw.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_nw_vscode_share` | `cli` | `cli-module` | `high` | typer, funcs:8 | src/stackops/scripts/python/helpers/helpers_devops/cli_nw_vscode_share.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_repos` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:9 | src/stackops/scripts/python/helpers/helpers_devops/cli_repos.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_repos_edit` | `cli` | `cli-module` | `high` | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/cli_repos_edit.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_repos_files` | `cli` | `cli-module` | `high` | typer, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/cli_repos_files.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_repos_list` | `cli` | `cli-module` | `high` | typer, classes:1, funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/cli_repos_list.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_repos_selection` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/cli_repos_selection.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_repos_version` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:10 | src/stackops/scripts/python/helpers/helpers_devops/cli_repos_version.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_scripts` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:5 | src/stackops/scripts/python/helpers/helpers_devops/cli_scripts.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:8 | src/stackops/scripts/python/helpers/helpers_devops/cli_self.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self_assets` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/cli_self_assets.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self_clone` | `cli` | `cli-module` | `high` | typer, funcs:5 | src/stackops/scripts/python/helpers/helpers_devops/cli_self_clone.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self_docker` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:9 | src/stackops/scripts/python/helpers/helpers_devops/cli_self_docker.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self_docs` | `cli` | `cli-module` | `high` | typer, classes:1, funcs:9 | src/stackops/scripts/python/helpers/helpers_devops/cli_self_docs.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self_export` | `cli` | `cli-module` | `high` | typer, funcs:2 | src/stackops/scripts/python/helpers/helpers_devops/cli_self_export.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self_info` | `cli` | `cli-module` | `high` | typer, funcs:6 | src/stackops/scripts/python/helpers/helpers_devops/cli_self_info.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self_release` | `cli` | `cli-module` | `high` | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/cli_self_release.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self_repo` | `cli` | `cli-module` | `high` | typer, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/cli_self_repo.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_share_file` | `cli` | `cli-module` | `high` | typer, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/cli_share_file.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_share_server` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, __main__, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/cli_share_server.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_share_temp` | `cli` | `cli-module` | `high` | typer, classes:1, funcs:5 | src/stackops/scripts/python/helpers/helpers_devops/cli_share_temp.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_share_terminal` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, __main__, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/cli_share_terminal.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_software` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:2 | src/stackops/scripts/python/helpers/helpers_devops/cli_software.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_software_attrs` | `cli` | `cli-module` | `high` | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/cli_software_attrs.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_software_files` | `cli` | `cli-module` | `high` | typer, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/cli_software_files.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_software_install` | `cli` | `cli-module` | `high` | typer, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/cli_software_install.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_software_report` | `cli` | `cli-module` | `high` | typer, funcs:2 | src/stackops/scripts/python/helpers/helpers_devops/cli_software_report.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_ssh` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:6 | src/stackops/scripts/python/helpers/helpers_devops/cli_ssh.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_ssh_port` | `cli` | `cli-module` | `high` | typer, funcs:6 | src/stackops/scripts/python/helpers/helpers_devops/cli_ssh_port.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_status` | `cli` | `cli-module` | `high` | typer, funcs:2 | src/stackops/scripts/python/helpers/helpers_devops/cli_status.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_subset_support` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/cli_subset_support.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_vault` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:8 | src/stackops/scripts/python/helpers/helpers_devops/cli_vault.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cloudflare_tunnel_config` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/cloudflare_tunnel_config.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cloudflare_tunnel_maintenance` | `cli-helper` | `cli-helper` | `medium` | funcs:6 | src/stackops/scripts/python/helpers/helpers_devops/cloudflare_tunnel_maintenance.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cloudflare_tunnel_runtime` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:10 | src/stackops/scripts/python/helpers/helpers_devops/cloudflare_tunnel_runtime.py |  |
| `stackops.scripts.python.helpers.helpers_devops.devops_status` | `cli-helper` | `cli-helper` | `medium` | main, __main__, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/devops_status.py |  |
| `stackops.scripts.python.helpers.helpers_devops.devops_status_apps` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_devops/devops_status_apps.py |  |
| `stackops.scripts.python.helpers.helpers_devops.devops_status_backup` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:2 | src/stackops/scripts/python/helpers/helpers_devops/devops_status_backup.py |  |
| `stackops.scripts.python.helpers.helpers_devops.devops_status_checks` | `cli-helper` | `cli-helper` | `medium` | classes:3, funcs:2 | src/stackops/scripts/python/helpers/helpers_devops/devops_status_checks.py |  |
| `stackops.scripts.python.helpers.helpers_devops.devops_status_config` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:5 | src/stackops/scripts/python/helpers/helpers_devops/devops_status_config.py |  |
| `stackops.scripts.python.helpers.helpers_devops.devops_status_constants` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_devops/devops_status_constants.py |  |
| `stackops.scripts.python.helpers.helpers_devops.devops_status_data` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:2 | src/stackops/scripts/python/helpers/helpers_devops/devops_status_data.py |  |
| `stackops.scripts.python.helpers.helpers_devops.devops_status_display` | `cli-helper` | `cli-helper` | `medium` | funcs:11 | src/stackops/scripts/python/helpers/helpers_devops/devops_status_display.py |  |
| `stackops.scripts.python.helpers.helpers_devops.devops_status_managed` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:2 | src/stackops/scripts/python/helpers/helpers_devops/devops_status_managed.py |  |
| `stackops.scripts.python.helpers.helpers_devops.devops_status_repos` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/devops_status_repos.py |  |
| `stackops.scripts.python.helpers.helpers_devops.devops_status_tui` | `cli-helper` | `cli-helper` | `medium` | classes:1 | src/stackops/scripts/python/helpers/helpers_devops/devops_status_tui.py |  |
| `stackops.scripts.python.helpers.helpers_devops.devops_update_repos` | `cli-helper` | `cli-helper` | `medium` | main, __main__, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/devops_update_repos.py |  |
| `stackops.scripts.python.helpers.helpers_devops.file_receive_proposal` | `cli` | `cli-module` | `high` | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/file_receive_proposal.py |  |
| `stackops.scripts.python.helpers.helpers_devops.file_send_encryption` | `cli` | `cli-module` | `high` | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/file_send_encryption.py |  |
| `stackops.scripts.python.helpers.helpers_devops.file_send_runtime` | `cli` | `cli-module` | `high` | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/file_send_runtime.py |  |
| `stackops.scripts.python.helpers.helpers_devops.interactive` | `cli-helper` | `cli-helper` | `medium` | main, __main__, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/interactive.py |  |
| `stackops.scripts.python.helpers.helpers_devops.mount_helpers.commands` | `cli-helper` | `cli-helper` | `medium` | funcs:5 | src/stackops/scripts/python/helpers/helpers_devops/mount_helpers/commands.py |  |
| `stackops.scripts.python.helpers.helpers_devops.mount_helpers.device_entry` | `cli-helper` | `cli-helper` | `medium` | classes:1 | src/stackops/scripts/python/helpers/helpers_devops/mount_helpers/device_entry.py |  |
| `stackops.scripts.python.helpers.helpers_devops.mount_helpers.devices` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/mount_helpers/devices.py |  |
| `stackops.scripts.python.helpers.helpers_devops.mount_helpers.linux` | `cli-helper` | `cli-helper` | `medium` | funcs:10 | src/stackops/scripts/python/helpers/helpers_devops/mount_helpers/linux.py |  |
| `stackops.scripts.python.helpers.helpers_devops.mount_helpers.macos` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/mount_helpers/macos.py |  |
| `stackops.scripts.python.helpers.helpers_devops.mount_helpers.selection` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_devops/mount_helpers/selection.py |  |
| `stackops.scripts.python.helpers.helpers_devops.mount_helpers.utils` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/mount_helpers/utils.py |  |
| `stackops.scripts.python.helpers.helpers_devops.mount_helpers.windows` | `cli-helper` | `cli-helper` | `medium` | funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/mount_helpers/windows.py |  |
| `stackops.scripts.python.helpers.helpers_devops.network_service` | `cli` | `cli-module` | `high` | typer, classes:1, funcs:8 | src/stackops/scripts/python/helpers/helpers_devops/network_service.py |  |
| `stackops.scripts.python.helpers.helpers_devops.register_interactive` | `cli` | `cli-module` | `high` | typer, funcs:7 | src/stackops/scripts/python/helpers/helpers_devops/register_interactive.py |  |
| `stackops.scripts.python.helpers.helpers_devops.run_script` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:9 | src/stackops/scripts/python/helpers/helpers_devops/run_script.py |  |
| `stackops.scripts.python.helpers.helpers_devops.script_discovery` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_devops/script_discovery.py |  |
| `stackops.scripts.python.helpers.helpers_devops.script_resolution` | `cli` | `cli-module` | `high` | typer, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/script_resolution.py |  |
| `stackops.scripts.python.helpers.helpers_devops.script_sources` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/script_sources.py |  |
| `stackops.scripts.python.helpers.helpers_devops.share_server_filebrowser` | `cli` | `cli-module` | `high` | typer, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/share_server_filebrowser.py |  |
| `stackops.scripts.python.helpers.helpers_devops.stackops_publish` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/stackops_publish.py |  |
| `stackops.scripts.python.helpers.helpers_devops.stackops_release` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/stackops_release.py |  |
| `stackops.scripts.python.helpers.helpers_devops.stackops_release_constants` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_devops/stackops_release_constants.py |  |
| `stackops.scripts.python.helpers.helpers_devops.stackops_skill_refs` | `cli-helper` | `cli-helper` | `medium` | funcs:12 | src/stackops/scripts/python/helpers/helpers_devops/stackops_skill_refs.py |  |
| `stackops.scripts.python.helpers.helpers_devops.stackops_versioning` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/stackops_versioning.py |  |
| `stackops.scripts.python.helpers.helpers_devops.themes.choose_wezterm_theme` | `cli-helper` | `cli-helper` | `medium` | main, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/themes/choose_wezterm_theme.py |  |
| `stackops.scripts.python.helpers.helpers_devops.themes.theme_commands` | `cli` | `cli-module` | `high` | typer, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/themes/theme_commands.py |  |
| `stackops.scripts.python.helpers.helpers_devops.vault` | `cli-helper` | `cli-helper` | `medium` | classes:4, funcs:26 | src/stackops/scripts/python/helpers/helpers_devops/vault.py |  |
| `stackops.scripts.python.helpers.helpers_devops.vault_clipboard` | `cli` | `cli-module` | `high` | typer, classes:3, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/vault_clipboard.py |  |
| `stackops.scripts.python.helpers.helpers_devops.vault_clipboard_clear` | `cli-helper` | `cli-helper` | `medium` | main, __main__, classes:1, funcs:2 | src/stackops/scripts/python/helpers/helpers_devops/vault_clipboard_clear.py |  |
| `stackops.scripts.python.helpers.helpers_devops.vault_constants` | `cli-helper` | `cli-helper` | `medium` | classes:1 | src/stackops/scripts/python/helpers/helpers_devops/vault_constants.py |  |
| `stackops.scripts.python.helpers.helpers_devops.vault_environment` | `cli` | `cli-module` | `high` | typer, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/vault_environment.py |  |
| `stackops.scripts.python.helpers.helpers_devops.vault_search` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:7 | src/stackops/scripts/python/helpers/helpers_devops/vault_search.py |  |
| `stackops.scripts.python.helpers.helpers_devops.vault_search_output` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:8 | src/stackops/scripts/python/helpers/helpers_devops/vault_search_output.py |  |
| `stackops.scripts.python.helpers.helpers_devops.vscode_share_runtime` | `cli` | `cli-module` | `high` | typer, funcs:2 | src/stackops/scripts/python/helpers/helpers_devops/vscode_share_runtime.py |  |
| `stackops.scripts.python.helpers.helpers_devops.vscode_tunnel_auth` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_devops/vscode_tunnel_auth.py |  |
| `stackops.scripts.python.helpers.helpers_env.env_manager_tui` | `cli-helper` | `cli-helper` | `medium` | main, __main__, classes:4, funcs:4 | src/stackops/scripts/python/helpers/helpers_env/env_manager_tui.py |  |
| `stackops.scripts.python.helpers.helpers_env.path_manager_backend` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_env/path_manager_backend.py |  |
| `stackops.scripts.python.helpers.helpers_env.path_manager_tui` | `cli-helper` | `cli-helper` | `medium` | main, __main__, classes:3, funcs:1 | src/stackops/scripts/python/helpers/helpers_env/path_manager_tui.py |  |
| `stackops.scripts.python.helpers.helpers_fire_command.cloud_manager` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_fire_command/cloud_manager.py |  |
| `stackops.scripts.python.helpers.helpers_fire_command.f` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_fire_command/f.py |  |
| `stackops.scripts.python.helpers.helpers_fire_command.file_wrangler` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_fire_command/file_wrangler.py |  |
| `stackops.scripts.python.helpers.helpers_fire_command.fire_jobs_args_helper` | `cli` | `cli-module` | `high` | typer, classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_fire_command/fire_jobs_args_helper.py |  |
| `stackops.scripts.python.helpers.helpers_fire_command.fire_jobs_environment` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:3 | src/stackops/scripts/python/helpers/helpers_fire_command/fire_jobs_environment.py |  |
| `stackops.scripts.python.helpers.helpers_fire_command.fire_jobs_impl` | `cli-helper` | `cli-helper` | `medium` | funcs:13 | src/stackops/scripts/python/helpers/helpers_fire_command/fire_jobs_impl.py |  |
| `stackops.scripts.python.helpers.helpers_fire_command.fire_jobs_route_helper` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_fire_command/fire_jobs_route_helper.py |  |
| `stackops.scripts.python.helpers.helpers_fire_command.fire_jobs_streamlit_helper` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_fire_command/fire_jobs_streamlit_helper.py |  |
| `stackops.scripts.python.helpers.helpers_preview.pomodoro` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_preview/pomodoro.py |  |
| `stackops.scripts.python.helpers.helpers_preview.preview_impl` | `cli-helper` | `cli-helper` | `medium` | funcs:7 | src/stackops/scripts/python/helpers/helpers_preview/preview_impl.py |  |
| `stackops.scripts.python.helpers.helpers_preview.preview_read` | `cli-helper` | `cli-helper` | `medium` | funcs:6 | src/stackops/scripts/python/helpers/helpers_preview/preview_read.py |  |
| `stackops.scripts.python.helpers.helpers_preview.scheduler` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_preview/scheduler.py |  |
| `stackops.scripts.python.helpers.helpers_preview.start_slidev` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, main, __main__, funcs:6 | src/stackops/scripts/python/helpers/helpers_preview/start_slidev.py |  |
| `stackops.scripts.python.helpers.helpers_preview.viewer` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_preview/viewer.py |  |
| `stackops.scripts.python.helpers.helpers_preview.viewer_template` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_preview/viewer_template.py |  |
| `stackops.scripts.python.helpers.helpers_repos.action` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_repos/action.py |  |
| `stackops.scripts.python.helpers.helpers_repos.action_helper` | `cli-helper` | `cli-helper` | `medium` | classes:3, funcs:3 | src/stackops/scripts/python/helpers/helpers_repos/action_helper.py |  |
| `stackops.scripts.python.helpers.helpers_repos.clone` | `cli-helper` | `cli-helper` | `medium` | funcs:6 | src/stackops/scripts/python/helpers/helpers_repos/clone.py |  |
| `stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync` | `cli` | `cli-module` | `high` | typer, main, funcs:2 | src/stackops/scripts/python/helpers/helpers_repos/cloud_repo_sync.py |  |
| `stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_actions` | `cli` | `cli-module` | `high` | typer, funcs:6 | src/stackops/scripts/python/helpers/helpers_repos/cloud_repo_sync_actions.py |  |
| `stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_archive` | `cli-helper` | `cli-helper` | `medium` | funcs:4 | src/stackops/scripts/python/helpers/helpers_repos/cloud_repo_sync_archive.py |  |
| `stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_conflicts` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_repos/cloud_repo_sync_conflicts.py |  |
| `stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_git` | `cli` | `cli-module` | `high` | typer, classes:3, funcs:7 | src/stackops/scripts/python/helpers/helpers_repos/cloud_repo_sync_git.py |  |
| `stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_gpg` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_repos/cloud_repo_sync_gpg.py |  |
| `stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_integration` | `cli` | `cli-module` | `high` | typer, classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_repos/cloud_repo_sync_integration.py |  |
| `stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_replacement` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_repos/cloud_repo_sync_replacement.py |  |
| `stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_status` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_repos/cloud_repo_sync_status.py |  |
| `stackops.scripts.python.helpers.helpers_repos.discovery` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_repos/discovery.py |  |
| `stackops.scripts.python.helpers.helpers_repos.git_action` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:6 | src/stackops/scripts/python/helpers/helpers_repos/git_action.py |  |
| `stackops.scripts.python.helpers.helpers_repos.guard_transport` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_repos/guard_transport.py |  |
| `stackops.scripts.python.helpers.helpers_repos.local_status` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:1 | src/stackops/scripts/python/helpers/helpers_repos/local_status.py |  |
| `stackops.scripts.python.helpers.helpers_repos.record` | `cli` | `cli-module` | `high` | typer, funcs:12 | src/stackops/scripts/python/helpers/helpers_repos/record.py |  |
| `stackops.scripts.python.helpers.helpers_repos.registration_sync` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_repos/registration_sync.py |  |
| `stackops.scripts.python.helpers.helpers_repos.spec_store` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:12 | src/stackops/scripts/python/helpers/helpers_repos/spec_store.py |  |
| `stackops.scripts.python.helpers.helpers_repos.sync` | `cli-helper` | `cli-helper` | `medium` | funcs:4 | src/stackops/scripts/python/helpers/helpers_repos/sync.py |  |
| `stackops.scripts.python.helpers.helpers_repos.sync_settings` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_repos/sync_settings.py |  |
| `stackops.scripts.python.helpers.helpers_repos.update` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_repos/update.py |  |
| `stackops.scripts.python.helpers.helpers_repos.version_capture` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:5 | src/stackops/scripts/python/helpers/helpers_repos/version_capture.py |  |
| `stackops.scripts.python.helpers.helpers_repos.version_checkout` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:9 | src/stackops/scripts/python/helpers/helpers_repos/version_checkout.py |  |
| `stackops.scripts.python.helpers.helpers_repos.version_constants` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_repos/version_constants.py |  |
| `stackops.scripts.python.helpers.helpers_repos.version_models` | `cli-helper` | `cli-helper` | `medium` | classes:8 | src/stackops/scripts/python/helpers/helpers_repos/version_models.py |  |
| `stackops.scripts.python.helpers.helpers_repos.version_paths` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_repos/version_paths.py |  |
| `stackops.scripts.python.helpers.helpers_repos.version_status` | `cli-helper` | `cli-helper` | `medium` | funcs:4 | src/stackops/scripts/python/helpers/helpers_repos/version_status.py |  |
| `stackops.scripts.python.helpers.helpers_repos.version_store` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:14 | src/stackops/scripts/python/helpers/helpers_repos/version_store.py |  |
| `stackops.scripts.python.helpers.helpers_search.ast_search` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:9 | src/stackops/scripts/python/helpers/helpers_search/ast_search.py |  |
| `stackops.scripts.python.helpers.helpers_search.qr_code` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_search/qr_code.py |  |
| `stackops.scripts.python.helpers.helpers_search.repo_rag` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_search/repo_rag.py |  |
| `stackops.scripts.python.helpers.helpers_search.script_help` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_search/script_help.py |  |
| `stackops.scripts.python.helpers.helpers_search.semantic_search` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_search/semantic_search.py |  |
| `stackops.scripts.python.helpers.helpers_seek.json_search` | `cli-helper` | `cli-helper` | `medium` | classes:6, funcs:6 | src/stackops/scripts/python/helpers/helpers_seek/json_search.py |  |
| `stackops.scripts.python.helpers.helpers_seek.seek_impl` | `cli-helper` | `cli-helper` | `medium` | funcs:16 | src/stackops/scripts/python/helpers/helpers_seek/seek_impl.py |  |
| `stackops.scripts.python.helpers.helpers_seek.semantic.backend_ck` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:2 | src/stackops/scripts/python/helpers/helpers_seek/semantic/backend_ck.py |  |
| `stackops.scripts.python.helpers.helpers_seek.semantic.backend_grepai` | `cli-helper` | `cli-helper` | `medium` | classes:5, funcs:4 | src/stackops/scripts/python/helpers/helpers_seek/semantic/backend_grepai.py |  |
| `stackops.scripts.python.helpers.helpers_seek.semantic.backend_names` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_seek/semantic/backend_names.py |  |
| `stackops.scripts.python.helpers.helpers_seek.semantic.backend_qmd` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:3 | src/stackops/scripts/python/helpers/helpers_seek/semantic/backend_qmd.py |  |
| `stackops.scripts.python.helpers.helpers_seek.semantic.backend_semtools` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:3 | src/stackops/scripts/python/helpers/helpers_seek/semantic/backend_semtools.py |  |
| `stackops.scripts.python.helpers.helpers_seek.semantic.command_runner` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_seek/semantic/command_runner.py |  |
| `stackops.scripts.python.helpers.helpers_seek.semantic.constants` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_seek/semantic/constants.py |  |
| `stackops.scripts.python.helpers.helpers_seek.semantic.hit_selection` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_seek/semantic/hit_selection.py |  |
| `stackops.scripts.python.helpers.helpers_seek.semantic.index_dirs` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_seek/semantic/index_dirs.py |  |
| `stackops.scripts.python.helpers.helpers_seek.semantic.json_search` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_seek/semantic/json_search.py |  |
| `stackops.scripts.python.helpers.helpers_seek.semantic.run_semantic_search` | `cli-helper` | `cli-helper` | `medium` | funcs:4 | src/stackops/scripts/python/helpers/helpers_seek/semantic/run_semantic_search.py |  |
| `stackops.scripts.python.helpers.helpers_seek.semantic.semantic_models` | `cli-helper` | `cli-helper` | `medium` | classes:3 | src/stackops/scripts/python/helpers/helpers_seek/semantic/semantic_models.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._aoe_backend` | `cli-helper` | `cli-helper` | `medium` | funcs:23 | src/stackops/scripts/python/helpers/helpers_sessions/_aoe_backend.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._attach_common` | `cli-helper` | `cli-helper` | `medium` | funcs:9 | src/stackops/scripts/python/helpers/helpers_sessions/_attach_common.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._herdr_backend` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:43 | src/stackops/scripts/python/helpers/helpers_sessions/_herdr_backend.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._herdr_backend_idle` | `cli-helper` | `cli-helper` | `medium` | funcs:8 | src/stackops/scripts/python/helpers/helpers_sessions/_herdr_backend_idle.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._tmux_backend` | `cli-helper` | `cli-helper` | `medium` | funcs:12 | src/stackops/scripts/python/helpers/helpers_sessions/_tmux_backend.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._tmux_backend_options` | `cli-helper` | `cli-helper` | `medium` | funcs:10 | src/stackops/scripts/python/helpers/helpers_sessions/_tmux_backend_options.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._tmux_backend_preview` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:15 | src/stackops/scripts/python/helpers/helpers_sessions/_tmux_backend_preview.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._tmux_backend_process_commands` | `cli-helper` | `cli-helper` | `medium` | funcs:5 | src/stackops/scripts/python/helpers/helpers_sessions/_tmux_backend_process_commands.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._tmux_backend_processes` | `cli-helper` | `cli-helper` | `medium` | funcs:4 | src/stackops/scripts/python/helpers/helpers_sessions/_tmux_backend_processes.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._tmux_process_inspection` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:11 | src/stackops/scripts/python/helpers/helpers_sessions/_tmux_process_inspection.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._tuios_backend` | `cli-helper` | `cli-helper` | `medium` | funcs:7 | src/stackops/scripts/python/helpers/helpers_sessions/_tuios_backend.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._tuios_backend_idle` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_sessions/_tuios_backend_idle.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._tuios_backend_kill` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_sessions/_tuios_backend_kill.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._tuios_backend_models` | `cli-helper` | `cli-helper` | `medium` | classes:4 | src/stackops/scripts/python/helpers/helpers_sessions/_tuios_backend_models.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._tuios_backend_preview` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_sessions/_tuios_backend_preview.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._tuios_backend_state` | `cli-helper` | `cli-helper` | `medium` | funcs:9 | src/stackops/scripts/python/helpers/helpers_sessions/_tuios_backend_state.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._zellij_backend` | `cli-helper` | `cli-helper` | `medium` | funcs:5 | src/stackops/scripts/python/helpers/helpers_sessions/_zellij_backend.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._zellij_backend_idle` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_sessions/_zellij_backend_idle.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._zellij_backend_kill` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_sessions/_zellij_backend_kill.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._zellij_backend_models` | `cli-helper` | `cli-helper` | `medium` | classes:3 | src/stackops/scripts/python/helpers/helpers_sessions/_zellij_backend_models.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._zellij_backend_preview` | `cli-helper` | `cli-helper` | `medium` | funcs:4 | src/stackops/scripts/python/helpers/helpers_sessions/_zellij_backend_preview.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._zellij_backend_state` | `cli-helper` | `cli-helper` | `medium` | funcs:9 | src/stackops/scripts/python/helpers/helpers_sessions/_zellij_backend_state.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.attach_impl` | `cli-helper` | `cli-helper` | `medium` | funcs:9 | src/stackops/scripts/python/helpers/helpers_sessions/attach_impl.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.herdr_export` | `cli-helper` | `cli-helper` | `medium` | funcs:9 | src/stackops/scripts/python/helpers/helpers_sessions/herdr_export.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.herdr_export_selection` | `cli-helper` | `cli-helper` | `medium` | funcs:8 | src/stackops/scripts/python/helpers/helpers_sessions/herdr_export_selection.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.herdr_export_source` | `cli-helper` | `cli-helper` | `medium` | funcs:16 | src/stackops/scripts/python/helpers/helpers_sessions/herdr_export_source.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.kill_exact_target` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_sessions/kill_exact_target.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.kill_impl` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_sessions/kill_impl.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.kill_models` | `cli-helper` | `cli-helper` | `medium` | classes:1 | src/stackops/scripts/python/helpers/helpers_sessions/kill_models.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.session_trace_aoe` | `cli-helper` | `cli-helper` | `medium` | funcs:18 | src/stackops/scripts/python/helpers/helpers_sessions/session_trace_aoe.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.session_trace_herdr` | `cli-helper` | `cli-helper` | `medium` | funcs:27 | src/stackops/scripts/python/helpers/helpers_sessions/session_trace_herdr.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.session_trace_json` | `cli` | `cli-module` | `high` | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_sessions/session_trace_json.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.session_trace_kill` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:3 | src/stackops/scripts/python/helpers/helpers_sessions/session_trace_kill.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.session_trace_models` | `cli-helper` | `cli-helper` | `medium` | classes:3, funcs:2 | src/stackops/scripts/python/helpers/helpers_sessions/session_trace_models.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.session_trace_runner` | `cli` | `cli-module` | `high` | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_sessions/session_trace_runner.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.session_trace_selection` | `cli-helper` | `cli-helper` | `medium` | funcs:5 | src/stackops/scripts/python/helpers/helpers_sessions/session_trace_selection.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.session_trace_tmux` | `cli-helper` | `cli-helper` | `medium` | funcs:4 | src/stackops/scripts/python/helpers/helpers_sessions/session_trace_tmux.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.session_trace_tuios` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_sessions/session_trace_tuios.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.session_trace_zellij` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_sessions/session_trace_zellij.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_aoe_impl` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:7 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_aoe_impl.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_cli_common` | `cli` | `cli-module` | `high` | typer, funcs:5 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_cli_common.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_cli_run` | `cli` | `cli-module` | `high` | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_cli_run.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_cli_run_all` | `cli` | `cli-module` | `high` | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_cli_run_all.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_dynamic` | `cli-helper` | `cli-helper` | `medium` | funcs:7 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_dynamic.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_dynamic_display` | `cli-helper` | `cli-helper` | `medium` | classes:3, funcs:11 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_dynamic_display.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_dynamic_tmux` | `cli-helper` | `cli-helper` | `medium` | funcs:9 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_dynamic_tmux.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_dynamic_tuios` | `cli-helper` | `cli-helper` | `medium` | funcs:5 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_dynamic_tuios.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_dynamic_zellij` | `cli-helper` | `cli-helper` | `medium` | funcs:4 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_dynamic_zellij.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_herdr` | `cli` | `cli-module` | `high` | typer, classes:3, funcs:10 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_herdr.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_impl` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_impl.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_layout_source` | `cli` | `cli-module` | `high` | typer, classes:1, funcs:3 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_layout_source.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_layout_tabs` | `cli` | `cli-module` | `high` | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_layout_tabs.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_multiprocess` | `cli` | `cli-module` | `high` | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_multiprocess.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_test_layouts` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:5 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_test_layouts.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_trace` | `cli` | `cli-module` | `high` | typer, __all__, funcs:7 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_trace.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_trace_layout` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:2 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_trace_layout.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_trace_render` | `cli-helper` | `cli-helper` | `medium` | funcs:16 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_trace_render.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_tuios` | `cli` | `cli-module` | `high` | typer, funcs:2 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_tuios.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_tuios_commands` | `cli-helper` | `cli-helper` | `medium` | funcs:4 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_tuios_commands.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_zellij` | `cli` | `cli-module` | `high` | typer, funcs:3 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_zellij.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_zellij_commands` | `cli-helper` | `cli-helper` | `medium` | funcs:4 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_zellij_commands.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_zellij_constants` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_sessions/sessions_zellij_constants.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_zellij_layout` | `cli-helper` | `cli-helper` | `medium` | funcs:6 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_zellij_layout.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.terminal_cli_helpers` | `cli` | `cli-module` | `high` | typer, funcs:4 | src/stackops/scripts/python/helpers/helpers_sessions/terminal_cli_helpers.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.terminal_export` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_sessions/terminal_export.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.terminal_export_settings` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:5 | src/stackops/scripts/python/helpers/helpers_sessions/terminal_export_settings.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.terminal_run_command` | `cli` | `cli-module` | `high` | typer, classes:1 | src/stackops/scripts/python/helpers/helpers_sessions/terminal_run_command.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.terminal_summary_json` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_sessions/terminal_summary_json.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.tmux_export` | `cli-helper` | `cli-helper` | `medium` | funcs:12 | src/stackops/scripts/python/helpers/helpers_sessions/tmux_export.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.tmux_export_constants` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_sessions/tmux_export_constants.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.tuios_export` | `cli-helper` | `cli-helper` | `medium` | funcs:4 | src/stackops/scripts/python/helpers/helpers_sessions/tuios_export.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.tuios_summary` | `cli` | `cli-module` | `high` | typer, funcs:2 | src/stackops/scripts/python/helpers/helpers_sessions/tuios_summary.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.utils` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_sessions/utils.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.zellij_attach` | `cli-helper` | `cli-helper` | `medium` | main, __main__, funcs:3 | src/stackops/scripts/python/helpers/helpers_sessions/zellij_attach.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.zellij_export` | `cli-helper` | `cli-helper` | `medium` | funcs:4 | src/stackops/scripts/python/helpers/helpers_sessions/zellij_export.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.zellij_summary` | `cli` | `cli-module` | `high` | typer, funcs:3 | src/stackops/scripts/python/helpers/helpers_sessions/zellij_summary.py |  |
| `stackops.scripts.python.helpers.helpers_utils.autostart` | `cli` | `cli-module` | `high` | typer, funcs:3 | src/stackops/scripts/python/helpers/helpers_utils/autostart.py |  |
| `stackops.scripts.python.helpers.helpers_utils.autostart_apply` | `cli-helper` | `cli-helper` | `medium` | classes:3, funcs:2 | src/stackops/scripts/python/helpers/helpers_utils/autostart_apply.py |  |
| `stackops.scripts.python.helpers.helpers_utils.autostart_common` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:2 | src/stackops/scripts/python/helpers/helpers_utils/autostart_common.py |  |
| `stackops.scripts.python.helpers.helpers_utils.autostart_entry` | `cli-helper` | `cli-helper` | `medium` | classes:3, funcs:4 | src/stackops/scripts/python/helpers/helpers_utils/autostart_entry.py |  |
| `stackops.scripts.python.helpers.helpers_utils.autostart_layout` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_utils/autostart_layout.py |  |
| `stackops.scripts.python.helpers.helpers_utils.autostart_linux` | `cli-helper` | `cli-helper` | `medium` | funcs:9 | src/stackops/scripts/python/helpers/helpers_utils/autostart_linux.py |  |
| `stackops.scripts.python.helpers.helpers_utils.autostart_macos` | `cli-helper` | `cli-helper` | `medium` | funcs:4 | src/stackops/scripts/python/helpers/helpers_utils/autostart_macos.py |  |
| `stackops.scripts.python.helpers.helpers_utils.autostart_macos_login` | `cli` | `cli-module` | `high` | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_utils/autostart_macos_login.py |  |
| `stackops.scripts.python.helpers.helpers_utils.autostart_remembered` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:5 | src/stackops/scripts/python/helpers/helpers_utils/autostart_remembered.py |  |
| `stackops.scripts.python.helpers.helpers_utils.autostart_script` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_utils/autostart_script.py |  |
| `stackops.scripts.python.helpers.helpers_utils.autostart_script_cli` | `cli` | `cli-module` | `high` | typer, funcs:3 | src/stackops/scripts/python/helpers/helpers_utils/autostart_script_cli.py |  |
| `stackops.scripts.python.helpers.helpers_utils.autostart_script_constants` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_utils/autostart_script_constants.py |  |
| `stackops.scripts.python.helpers.helpers_utils.autostart_script_entries` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_utils/autostart_script_entries.py |  |
| `stackops.scripts.python.helpers.helpers_utils.autostart_windows` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:1 | src/stackops/scripts/python/helpers/helpers_utils/autostart_windows.py |  |
| `stackops.scripts.python.helpers.helpers_utils.clean_drive_catalog` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_utils/clean_drive_catalog.py |  |
| `stackops.scripts.python.helpers.helpers_utils.clean_drive_catalog_dev` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_utils/clean_drive_catalog_dev.py |  |
| `stackops.scripts.python.helpers.helpers_utils.clean_drive_catalog_stackops` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_utils/clean_drive_catalog_stackops.py |  |
| `stackops.scripts.python.helpers.helpers_utils.clean_drive_catalog_system` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_utils/clean_drive_catalog_system.py |  |
| `stackops.scripts.python.helpers.helpers_utils.clean_drive_cli` | `cli` | `cli-module` | `high` | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_utils/clean_drive_cli.py |  |
| `stackops.scripts.python.helpers.helpers_utils.clean_drive_constants` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_utils/clean_drive_constants.py |  |
| `stackops.scripts.python.helpers.helpers_utils.clean_drive_details` | `cli-helper` | `cli-helper` | `medium` | classes:7, funcs:5 | src/stackops/scripts/python/helpers/helpers_utils/clean_drive_details.py |  |
| `stackops.scripts.python.helpers.helpers_utils.clean_drive_execute` | `cli-helper` | `cli-helper` | `medium` | funcs:5 | src/stackops/scripts/python/helpers/helpers_utils/clean_drive_execute.py |  |
| `stackops.scripts.python.helpers.helpers_utils.clean_drive_interactive` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_utils/clean_drive_interactive.py |  |
| `stackops.scripts.python.helpers.helpers_utils.clean_drive_models` | `cli-helper` | `cli-helper` | `medium` | classes:18 | src/stackops/scripts/python/helpers/helpers_utils/clean_drive_models.py |  |
| `stackops.scripts.python.helpers.helpers_utils.clean_drive_paths` | `cli-helper` | `cli-helper` | `medium` | funcs:4 | src/stackops/scripts/python/helpers/helpers_utils/clean_drive_paths.py |  |
| `stackops.scripts.python.helpers.helpers_utils.clean_drive_plans` | `cli-helper` | `cli-helper` | `medium` | funcs:10 | src/stackops/scripts/python/helpers/helpers_utils/clean_drive_plans.py |  |
| `stackops.scripts.python.helpers.helpers_utils.clean_drive_projects` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_utils/clean_drive_projects.py |  |
| `stackops.scripts.python.helpers.helpers_utils.clean_drive_render` | `cli-helper` | `cli-helper` | `medium` | classes:5, funcs:10 | src/stackops/scripts/python/helpers/helpers_utils/clean_drive_render.py |  |
| `stackops.scripts.python.helpers.helpers_utils.clean_drive_scan` | `cli-helper` | `cli-helper` | `medium` | funcs:10 | src/stackops/scripts/python/helpers/helpers_utils/clean_drive_scan.py |  |
| `stackops.scripts.python.helpers.helpers_utils.clean_drive_usage` | `cli-helper` | `cli-helper` | `medium` | funcs:7 | src/stackops/scripts/python/helpers/helpers_utils/clean_drive_usage.py |  |
| `stackops.scripts.python.helpers.helpers_utils.environment_html` | `cli-helper` | `cli-helper` | `medium` | classes:3, funcs:3 | src/stackops/scripts/python/helpers/helpers_utils/environment_html.py |  |
| `stackops.scripts.python.helpers.helpers_utils.file_utils_app` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:8 | src/stackops/scripts/python/helpers/helpers_utils/file_utils_app.py |  |
| `stackops.scripts.python.helpers.helpers_utils.machine_utils_app` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, classes:1, funcs:7 | src/stackops/scripts/python/helpers/helpers_utils/machine_utils_app.py |  |
| `stackops.scripts.python.helpers.helpers_utils.path_helper` | `cli` | `cli-module` | `high` | typer, funcs:9 | src/stackops/scripts/python/helpers/helpers_utils/path_helper.py |  |
| `stackops.scripts.python.helpers.helpers_utils.path_reference_validation` | `cli-helper` | `cli-helper` | `medium` | classes:5, funcs:14 | src/stackops/scripts/python/helpers/helpers_utils/path_reference_validation.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pdf` | `cli` | `cli-module` | `high` | typer, funcs:2 | src/stackops/scripts/python/helpers/helpers_utils/pdf.py |  |
| `stackops.scripts.python.helpers.helpers_utils.process_models` | `cli-helper` | `cli-helper` | `medium` | classes:4, funcs:2 | src/stackops/scripts/python/helpers/helpers_utils/process_models.py |  |
| `stackops.scripts.python.helpers.helpers_utils.process_termination` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:2 | src/stackops/scripts/python/helpers/helpers_utils/process_termination.py |  |
| `stackops.scripts.python.helpers.helpers_utils.processes` | `cli-helper` | `cli-helper` | `medium` | __main__, classes:2, funcs:3 | src/stackops/scripts/python/helpers/helpers_utils/processes.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_app` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:1 | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_app.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_commands_check` | `cli` | `cli-module` | `high` | typer, funcs:2 | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_commands_check.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_commands_deps` | `cli` | `cli-module` | `high` | typer, funcs:6 | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_commands_deps.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_commands_maintenance` | `cli` | `cli-module` | `high` | typer, funcs:2 | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_commands_maintenance.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_commands_setup` | `cli` | `cli-module` | `high` | typer, funcs:2 | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_commands_setup.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps` | `cli-helper` | `cli-helper` | `medium` | funcs:11 | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_deps.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_graph` | `cli-helper` | `cli-helper` | `medium` | funcs:6 | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_deps_graph.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_models` | `cli-helper` | `cli-helper` | `medium` | classes:6 | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_deps_models.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_options` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_deps_options.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_parse` | `cli-helper` | `cli-helper` | `medium` | funcs:5 | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_deps_parse.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_render` | `cli-helper` | `cli-helper` | `medium` | funcs:8 | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_deps_render.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_render_css` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_deps_render_css.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_render_graph_css` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_deps_render_graph_css.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_render_js` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_deps_render_js.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_render_js_bootstrap` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_deps_render_js_bootstrap.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_render_js_interaction` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_deps_render_js_interaction.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_render_js_layout` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_deps_render_js_layout.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_render_js_shared` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_deps_render_js_shared.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_render_js_svg` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_deps_render_js_svg.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_runner` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_deps_runner.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_helpers` | `cli-helper` | `cli-helper` | `medium` | funcs:6 | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_helpers.py |  |
| `stackops.scripts.python.helpers.helpers_utils.python` | `cli` | `cli-module` | `high` | typer, __main__, funcs:10 | src/stackops/scripts/python/helpers/helpers_utils/python.py |  |
| `stackops.scripts.python.helpers.helpers_utils.python_init` | `cli` | `cli-module` | `high` | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_utils/python_init.py |  |
| `stackops.scripts.python.helpers.helpers_utils.read_db_cli_tui` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_utils/read_db_cli_tui.py |  |
| `stackops.scripts.python.helpers.helpers_utils.read_db_cli_tui_backend` | `cli` | `cli-module` | `high` | typer, funcs:22 | src/stackops/scripts/python/helpers/helpers_utils/read_db_cli_tui_backend.py |  |
| `stackops.scripts.python.helpers.helpers_utils.scrape` | `cli` | `cli-module` | `high` | typer, funcs:3 | src/stackops/scripts/python/helpers/helpers_utils/scrape.py |  |
| `stackops.scripts.python.helpers.helpers_utils.specs` | `cli-helper` | `cli-helper` | `medium` | main, __main__, funcs:8 | src/stackops/scripts/python/helpers/helpers_utils/specs.py |  |
| `stackops.scripts.python.helpers.helpers_utils.surya` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_utils/surya.py |  |
| `stackops.scripts.python.helpers.helpers_utils.upgrade_packages` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:14 | src/stackops/scripts/python/helpers/helpers_utils/upgrade_packages.py |  |
| `stackops.scripts.python.helpers.helpers_utils.window` | `cli` | `cli-module` | `high` | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_utils/window.py |  |
| `stackops.scripts.python.helpers.helpers_webui.access_guard` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/access_guard.py |  |
| `stackops.scripts.python.helpers.helpers_webui.capture` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:3 | src/stackops/scripts/python/helpers/helpers_webui/capture.py |  |
| `stackops.scripts.python.helpers.helpers_webui.catalog` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, classes:3, funcs:2 | src/stackops/scripts/python/helpers/helpers_webui/catalog.py |  |
| `stackops.scripts.python.helpers.helpers_webui.cli_webui` | `cli` | `cli-module` | `high` | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/cli_webui.py |  |
| `stackops.scripts.python.helpers.helpers_webui.constants` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_webui/constants.py |  |
| `stackops.scripts.python.helpers.helpers_webui.dotfiles_constants` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_webui/dotfiles_constants.py |  |
| `stackops.scripts.python.helpers.helpers_webui.dotfiles_export_plan` | `cli-helper` | `cli-helper` | `medium` | classes:4, funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/dotfiles_export_plan.py |  |
| `stackops.scripts.python.helpers.helpers_webui.dotfiles_import_inspect` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:3 | src/stackops/scripts/python/helpers/helpers_webui/dotfiles_import_inspect.py |  |
| `stackops.scripts.python.helpers.helpers_webui.dotfiles_import_state` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/dotfiles_import_state.py |  |
| `stackops.scripts.python.helpers.helpers_webui.dotfiles_model` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:2 | src/stackops/scripts/python/helpers/helpers_webui/dotfiles_model.py |  |
| `stackops.scripts.python.helpers.helpers_webui.dotfiles_register_check` | `cli-helper` | `cli-helper` | `medium` | classes:4, funcs:3 | src/stackops/scripts/python/helpers/helpers_webui/dotfiles_register_check.py |  |
| `stackops.scripts.python.helpers.helpers_webui.dotfiles_routes` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/dotfiles_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.feature_routes` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/feature_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.field_choice_keywords` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/field_choice_keywords.py |  |
| `stackops.scripts.python.helpers.helpers_webui.field_choices` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:8 | src/stackops/scripts/python/helpers/helpers_webui/field_choices.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_autostart_actions` | `cli-helper` | `cli-helper` | `medium` | funcs:7 | src/stackops/scripts/python/helpers/helpers_webui/machine_autostart_actions.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_autostart_constants` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_webui/machine_autostart_constants.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_autostart_detail` | `cli-helper` | `cli-helper` | `medium` | funcs:5 | src/stackops/scripts/python/helpers/helpers_webui/machine_autostart_detail.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_autostart_launchd` | `cli-helper` | `cli-helper` | `medium` | classes:3, funcs:7 | src/stackops/scripts/python/helpers/helpers_webui/machine_autostart_launchd.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_autostart_linux` | `cli-helper` | `cli-helper` | `medium` | funcs:7 | src/stackops/scripts/python/helpers/helpers_webui/machine_autostart_linux.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_autostart_linux_actions` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_webui/machine_autostart_linux_actions.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_autostart_login_items` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_webui/machine_autostart_login_items.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_autostart_macos` | `cli-helper` | `cli-helper` | `medium` | funcs:6 | src/stackops/scripts/python/helpers/helpers_webui/machine_autostart_macos.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_autostart_model` | `cli-helper` | `cli-helper` | `medium` | classes:6 | src/stackops/scripts/python/helpers/helpers_webui/machine_autostart_model.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_autostart_naming` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_webui/machine_autostart_naming.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_autostart_read` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_webui/machine_autostart_read.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_autostart_routes` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_webui/machine_autostart_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_autostart_scripts` | `cli-helper` | `cli-helper` | `medium` | classes:6, funcs:7 | src/stackops/scripts/python/helpers/helpers_webui/machine_autostart_scripts.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_autostart_windows` | `cli-helper` | `cli-helper` | `medium` | funcs:5 | src/stackops/scripts/python/helpers/helpers_webui/machine_autostart_windows.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_devices_actions` | `cli-helper` | `cli-helper` | `medium` | funcs:5 | src/stackops/scripts/python/helpers/helpers_webui/machine_devices_actions.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_devices_linux` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_webui/machine_devices_linux.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_devices_macos` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_webui/machine_devices_macos.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_devices_model` | `cli-helper` | `cli-helper` | `medium` | classes:5 | src/stackops/scripts/python/helpers/helpers_webui/machine_devices_model.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_devices_mounts` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:5 | src/stackops/scripts/python/helpers/helpers_webui/machine_devices_mounts.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_devices_read` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/machine_devices_read.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_devices_records` | `cli-helper` | `cli-helper` | `medium` | funcs:5 | src/stackops/scripts/python/helpers/helpers_webui/machine_devices_records.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_devices_routes` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/machine_devices_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_devices_windows` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/machine_devices_windows.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_environment_routes` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/machine_environment_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_mount_constants` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_webui/machine_mount_constants.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_mount_devices` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_webui/machine_mount_devices.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_mount_linux` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:3 | src/stackops/scripts/python/helpers/helpers_webui/machine_mount_linux.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_mount_macos` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:3 | src/stackops/scripts/python/helpers/helpers_webui/machine_mount_macos.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_mount_model` | `cli-helper` | `cli-helper` | `medium` | classes:4, funcs:3 | src/stackops/scripts/python/helpers/helpers_webui/machine_mount_model.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_mount_places` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:2 | src/stackops/scripts/python/helpers/helpers_webui/machine_mount_places.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_mount_routes` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/machine_mount_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_mount_windows` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_webui/machine_mount_windows.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_processes_detail` | `cli-helper` | `cli-helper` | `medium` | classes:3, funcs:3 | src/stackops/scripts/python/helpers/helpers_webui/machine_processes_detail.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_processes_routes` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/machine_processes_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_processes_rows` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_webui/machine_processes_rows.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_processes_scan` | `cli-helper` | `cli-helper` | `medium` | classes:3, funcs:5 | src/stackops/scripts/python/helpers/helpers_webui/machine_processes_scan.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_processes_stop` | `cli-helper` | `cli-helper` | `medium` | classes:3, funcs:4 | src/stackops/scripts/python/helpers/helpers_webui/machine_processes_stop.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_update_checkout` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:5 | src/stackops/scripts/python/helpers/helpers_webui/machine_update_checkout.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_update_constants` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_webui/machine_update_constants.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_update_effects` | `cli-helper` | `cli-helper` | `medium` | classes:3, funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/machine_update_effects.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_update_install` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:6 | src/stackops/scripts/python/helpers/helpers_webui/machine_update_install.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_update_latest` | `cli-helper` | `cli-helper` | `medium` | classes:6, funcs:6 | src/stackops/scripts/python/helpers/helpers_webui/machine_update_latest.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_update_routes` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/machine_update_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_update_state` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:2 | src/stackops/scripts/python/helpers/helpers_webui/machine_update_state.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_windows_actions` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_webui/machine_windows_actions.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_windows_constants` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_webui/machine_windows_constants.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_windows_listing` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_webui/machine_windows_listing.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_windows_macos` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_webui/machine_windows_macos.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_windows_models` | `cli-helper` | `cli-helper` | `medium` | classes:8 | src/stackops/scripts/python/helpers/helpers_webui/machine_windows_models.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_windows_routes` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/machine_windows_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.network_constants` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_webui/network_constants.py |  |
| `stackops.scripts.python.helpers.helpers_webui.network_forwards` | `cli-helper` | `cli-helper` | `medium` | classes:6, funcs:6 | src/stackops/scripts/python/helpers/helpers_webui/network_forwards.py |  |
| `stackops.scripts.python.helpers.helpers_webui.network_glance` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/network_glance.py |  |
| `stackops.scripts.python.helpers.helpers_webui.network_routes` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/network_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.network_ssh_keys` | `cli-helper` | `cli-helper` | `medium` | classes:6, funcs:11 | src/stackops/scripts/python/helpers/helpers_webui/network_ssh_keys.py |  |
| `stackops.scripts.python.helpers.helpers_webui.network_ssh_setup` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/network_ssh_setup.py |  |
| `stackops.scripts.python.helpers.helpers_webui.network_system` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/network_system.py |  |
| `stackops.scripts.python.helpers.helpers_webui.network_tunnels` | `cli-helper` | `cli-helper` | `medium` | classes:4, funcs:5 | src/stackops/scripts/python/helpers/helpers_webui/network_tunnels.py |  |
| `stackops.scripts.python.helpers.helpers_webui.network_tunnels_account` | `cli-helper` | `cli-helper` | `medium` | classes:3, funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/network_tunnels_account.py |  |
| `stackops.scripts.python.helpers.helpers_webui.network_warp` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/network_warp.py |  |
| `stackops.scripts.python.helpers.helpers_webui.network_wifi` | `cli-helper` | `cli-helper` | `medium` | classes:3, funcs:6 | src/stackops/scripts/python/helpers/helpers_webui/network_wifi.py |  |
| `stackops.scripts.python.helpers.helpers_webui.network_wifi_linux` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_webui/network_wifi_linux.py |  |
| `stackops.scripts.python.helpers.helpers_webui.network_wifi_macos` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_webui/network_wifi_macos.py |  |
| `stackops.scripts.python.helpers.helpers_webui.network_wifi_model` | `cli-helper` | `cli-helper` | `medium` | classes:5, funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/network_wifi_model.py |  |
| `stackops.scripts.python.helpers.helpers_webui.network_wifi_windows` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/network_wifi_windows.py |  |
| `stackops.scripts.python.helpers.helpers_webui.other_machines_hosts` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/other_machines_hosts.py |  |
| `stackops.scripts.python.helpers.helpers_webui.other_machines_links` | `cli-helper` | `cli-helper` | `medium` | classes:3, funcs:8 | src/stackops/scripts/python/helpers/helpers_webui/other_machines_links.py |  |
| `stackops.scripts.python.helpers.helpers_webui.other_machines_marker` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/other_machines_marker.py |  |
| `stackops.scripts.python.helpers.helpers_webui.other_machines_prepare` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/other_machines_prepare.py |  |
| `stackops.scripts.python.helpers.helpers_webui.other_machines_routes` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:2 | src/stackops/scripts/python/helpers/helpers_webui/other_machines_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.pages` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/pages.py |  |
| `stackops.scripts.python.helpers.helpers_webui.pty_process` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:3 | src/stackops/scripts/python/helpers/helpers_webui/pty_process.py |  |
| `stackops.scripts.python.helpers.helpers_webui.run_requests` | `cli-helper` | `cli-helper` | `medium` | classes:3, funcs:4 | src/stackops/scripts/python/helpers/helpers_webui/run_requests.py |  |
| `stackops.scripts.python.helpers.helpers_webui.run_socket` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/run_socket.py |  |
| `stackops.scripts.python.helpers.helpers_webui.runs` | `cli-helper` | `cli-helper` | `medium` | classes:4, funcs:9 | src/stackops/scripts/python/helpers/helpers_webui/runs.py |  |
| `stackops.scripts.python.helpers.helpers_webui.scripts_files` | `cli-helper` | `cli-helper` | `medium` | classes:6, funcs:6 | src/stackops/scripts/python/helpers/helpers_webui/scripts_files.py |  |
| `stackops.scripts.python.helpers.helpers_webui.scripts_online` | `cli-helper` | `cli-helper` | `medium` | classes:3, funcs:2 | src/stackops/scripts/python/helpers/helpers_webui/scripts_online.py |  |
| `stackops.scripts.python.helpers.helpers_webui.scripts_routes` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/scripts_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.security_cloud_routes` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/security_cloud_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.security_cloud_state` | `cli-helper` | `cli-helper` | `medium` | classes:3, funcs:5 | src/stackops/scripts/python/helpers/helpers_webui/security_cloud_state.py |  |
| `stackops.scripts.python.helpers.helpers_webui.security_constants` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_webui/security_constants.py |  |
| `stackops.scripts.python.helpers.helpers_webui.security_drive_link` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:6 | src/stackops/scripts/python/helpers/helpers_webui/security_drive_link.py |  |
| `stackops.scripts.python.helpers.helpers_webui.security_locker_keys` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:6 | src/stackops/scripts/python/helpers/helpers_webui/security_locker_keys.py |  |
| `stackops.scripts.python.helpers.helpers_webui.security_locker_look` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:5 | src/stackops/scripts/python/helpers/helpers_webui/security_locker_look.py |  |
| `stackops.scripts.python.helpers.helpers_webui.security_locker_routes` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/security_locker_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.security_locker_run` | `cli-helper` | `cli-helper` | `medium` | classes:3, funcs:4 | src/stackops/scripts/python/helpers/helpers_webui/security_locker_run.py |  |
| `stackops.scripts.python.helpers.helpers_webui.security_paths` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:2 | src/stackops/scripts/python/helpers/helpers_webui/security_paths.py |  |
| `stackops.scripts.python.helpers.helpers_webui.security_routes` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/security_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.security_scan_export` | `cli-helper` | `cli-helper` | `medium` | classes:4, funcs:5 | src/stackops/scripts/python/helpers/helpers_webui/security_scan_export.py |  |
| `stackops.scripts.python.helpers.helpers_webui.security_scan_plans` | `cli-helper` | `cli-helper` | `medium` | classes:5, funcs:6 | src/stackops/scripts/python/helpers/helpers_webui/security_scan_plans.py |  |
| `stackops.scripts.python.helpers.helpers_webui.security_scan_routes` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/security_scan_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.server_app` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/server_app.py |  |
| `stackops.scripts.python.helpers.helpers_webui.server_main` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/server_main.py |  |
| `stackops.scripts.python.helpers.helpers_webui.settings_assets` | `cli-helper` | `cli-helper` | `medium` | classes:3, funcs:7 | src/stackops/scripts/python/helpers/helpers_webui/settings_assets.py |  |
| `stackops.scripts.python.helpers.helpers_webui.settings_constants` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_webui/settings_constants.py |  |
| `stackops.scripts.python.helpers.helpers_webui.settings_files` | `cli-helper` | `cli-helper` | `medium` | classes:6, funcs:11 | src/stackops/scripts/python/helpers/helpers_webui/settings_files.py |  |
| `stackops.scripts.python.helpers.helpers_webui.settings_routes` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/settings_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.settings_setup` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:3 | src/stackops/scripts/python/helpers/helpers_webui/settings_setup.py |  |
| `stackops.scripts.python.helpers.helpers_webui.software_catalog` | `cli-helper` | `cli-helper` | `medium` | classes:5, funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/software_catalog.py |  |
| `stackops.scripts.python.helpers.helpers_webui.software_versions` | `cli-helper` | `cli-helper` | `medium` | classes:3, funcs:5 | src/stackops/scripts/python/helpers/helpers_webui/software_versions.py |  |
| `stackops.scripts.python.helpers.helpers_webui.terminal_ghostty_constants` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_webui/terminal_ghostty_constants.py |  |
| `stackops.scripts.python.helpers.helpers_webui.terminal_ghostty_routes` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/terminal_ghostty_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.terminal_ghostty_status` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/terminal_ghostty_status.py |  |
| `stackops.scripts.python.helpers.helpers_webui.terminal_layouts_routes` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/terminal_layouts_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.terminal_multiplexer_constants` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_webui/terminal_multiplexer_constants.py |  |
| `stackops.scripts.python.helpers.helpers_webui.terminal_multiplexer_routes` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/terminal_multiplexer_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.terminal_multiplexer_sessions` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:2 | src/stackops/scripts/python/helpers/helpers_webui/terminal_multiplexer_sessions.py |  |
| `stackops.scripts.python.helpers.helpers_webui.terminal_multiplexer_store` | `cli` | `cli-module` | `high` | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/terminal_multiplexer_store.py |  |
| `stackops.scripts.python.helpers.helpers_webui.terminal_multiplexer_views` | `cli-helper` | `cli-helper` | `medium` | classes:4, funcs:6 | src/stackops/scripts/python/helpers/helpers_webui/terminal_multiplexer_views.py |  |
| `stackops.scripts.python.helpers.helpers_webui.terminal_shell_profile_constants` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_webui/terminal_shell_profile_constants.py |  |
| `stackops.scripts.python.helpers.helpers_webui.terminal_shell_profile_gives` | `cli-helper` | `cli-helper` | `medium` | classes:4, funcs:4 | src/stackops/scripts/python/helpers/helpers_webui/terminal_shell_profile_gives.py |  |
| `stackops.scripts.python.helpers.helpers_webui.terminal_shell_profile_routes` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/terminal_shell_profile_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.terminal_shell_profile_state` | `cli-helper` | `cli-helper` | `medium` | classes:4, funcs:7 | src/stackops/scripts/python/helpers/helpers_webui/terminal_shell_profile_state.py |  |
| `stackops.scripts.python.helpers.helpers_webui.terminal_starship_constants` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_webui/terminal_starship_constants.py |  |
| `stackops.scripts.python.helpers.helpers_webui.terminal_starship_routes` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:2 | src/stackops/scripts/python/helpers/helpers_webui/terminal_starship_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.terminal_wezterm_routes` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/terminal_wezterm_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.terminal_wezterm_settings` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:2 | src/stackops/scripts/python/helpers/helpers_webui/terminal_wezterm_settings.py |  |
| `stackops.scripts.python.helpers.helpers_webui.text_files` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:2 | src/stackops/scripts/python/helpers/helpers_webui/text_files.py |  |
| `stackops.scripts.python.helpers.helpers_webui.vault_bitwarden_items` | `cli-helper` | `cli-helper` | `medium` | classes:4, funcs:3 | src/stackops/scripts/python/helpers/helpers_webui/vault_bitwarden_items.py |  |
| `stackops.scripts.python.helpers.helpers_webui.vault_bitwarden_routes` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/vault_bitwarden_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.vault_bitwarden_state` | `cli-helper` | `cli-helper` | `medium` | classes:4, funcs:4 | src/stackops/scripts/python/helpers/helpers_webui/vault_bitwarden_state.py |  |
| `stackops.scripts.python.helpers.helpers_webui.vault_file_constants` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_webui/vault_file_constants.py |  |
| `stackops.scripts.python.helpers.helpers_webui.vault_file_copy` | `cli` | `cli-module` | `high` | typer, classes:2, funcs:2 | src/stackops/scripts/python/helpers/helpers_webui/vault_file_copy.py |  |
| `stackops.scripts.python.helpers.helpers_webui.vault_file_fixes` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:6 | src/stackops/scripts/python/helpers/helpers_webui/vault_file_fixes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.vault_file_health` | `cli` | `cli-module` | `high` | typer, classes:5, funcs:5 | src/stackops/scripts/python/helpers/helpers_webui/vault_file_health.py |  |
| `stackops.scripts.python.helpers.helpers_webui.vault_file_problem` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_webui/vault_file_problem.py |  |
| `stackops.scripts.python.helpers.helpers_webui.vault_file_routes` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/vault_file_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.vault_form` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:2 | src/stackops/scripts/python/helpers/helpers_webui/vault_form.py |  |
| `stackops.scripts.python.helpers.helpers_webui.vault_routes` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/vault_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.vault_store` | `cli-helper` | `cli-helper` | `medium` | classes:3, funcs:4 | src/stackops/scripts/python/helpers/helpers_webui/vault_store.py |  |
| `stackops.scripts.python.helpers.helpers_webui.vault_views` | `cli-helper` | `cli-helper` | `medium` | classes:3, funcs:4 | src/stackops/scripts/python/helpers/helpers_webui/vault_views.py |  |
| `stackops.scripts.python.helpers.helpers_webui.vendor_assets` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/vendor_assets.py |  |
| `stackops.scripts.python.helpers.helpers_window.constants` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_window/constants.py |  |
| `stackops.scripts.python.helpers.helpers_window.window_linux` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_window/window_linux.py |  |
| `stackops.scripts.python.helpers.helpers_window.window_macos` | `cli` | `cli-module` | `high` | typer, classes:3, funcs:4 | src/stackops/scripts/python/helpers/helpers_window/window_macos.py |  |
| `stackops.scripts.python.helpers.helpers_window.window_macos_api` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:7 | src/stackops/scripts/python/helpers/helpers_window/window_macos_api.py |  |
| `stackops.scripts.python.helpers.helpers_window.window_models` | `cli-helper` | `cli-helper` | `medium` | classes:1 | src/stackops/scripts/python/helpers/helpers_window/window_models.py |  |
| `stackops.scripts.python.helpers.helpers_window.window_windows` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:3 | src/stackops/scripts/python/helpers/helpers_window/window_windows.py |  |
| `stackops.scripts.python.preview` | `cli` | `cli-entrypoint` | `high` | entry:preview, typer, typer-app, cli-registration, main, __main__, funcs:6 | src/stackops/scripts/python/preview.py |  |
| `stackops.scripts.python.seek` | `cli` | `cli-entrypoint` | `high` | entry:seek, typer, typer-app, cli-registration, get_app, main, funcs:4 | src/stackops/scripts/python/seek.py |  |
| `stackops.scripts.python.stackops_entry` | `cli` | `cli-entrypoint` | `high` | entry:stackops, typer, typer-app, cli-registration, get_app, main, __main__, classes:1, funcs:13 | src/stackops/scripts/python/stackops_entry.py |  |
| `stackops.scripts.python.terminal` | `cli` | `cli-entrypoint` | `high` | entry:terminal, typer, typer-app, cli-registration, get_app, main, __main__, funcs:12 | src/stackops/scripts/python/terminal.py |  |
| `stackops.scripts.python.terminal_layout_commands` | `cli` | `cli-module` | `high` | typer, funcs:2 | src/stackops/scripts/python/terminal_layout_commands.py |  |
| `stackops.scripts.python.terminal_layout_files` | `cli` | `cli-module` | `high` | typer, funcs:5 | src/stackops/scripts/python/terminal_layout_files.py |  |
| `stackops.scripts.python.terminal_summary` | `cli` | `cli-module` | `high` | typer, classes:3, funcs:29 | src/stackops/scripts/python/terminal_summary.py |  |
| `stackops.scripts.python.terminal_summary_commands` | `cli` | `cli-module` | `high` | typer, funcs:1 | src/stackops/scripts/python/terminal_summary_commands.py |  |
| `stackops.scripts.python.terminal_summary_models` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/terminal_summary_models.py |  |
| `stackops.scripts.python.utils` | `cli` | `cli-entrypoint` | `high` | entry:utils, typer, typer-app, cli-registration, get_app, main, __main__, funcs:3 | src/stackops/scripts/python/utils.py |  |
| `stackops.utils.cli_utils.alias_markers` | `cli-helper` | `cli-helper` | `medium` | typer, funcs:5 | src/stackops/utils/cli_utils/alias_markers.py |  |
| `stackops.utils.cli_utils.command_lookup` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/utils/cli_utils/command_lookup.py |  |
| `stackops.utils.cli_utils.hierarchy` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/utils/cli_utils/hierarchy.py |  |
| `stackops.utils.cli_utils.hierarchy_types` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/utils/cli_utils/hierarchy_types.py |  |
| `stackops.utils.cli_utils.lazy_group` | `cli-helper` | `cli-helper` | `medium` | typer, funcs:8 | src/stackops/utils/cli_utils/lazy_group.py |  |
| `stackops.utils.cli_utils.ordered_group` | `cli-helper` | `cli-helper` | `medium` | typer, funcs:1 | src/stackops/utils/cli_utils/ordered_group.py |  |
| `stackops.utils.cli_utils.secret_input` | `cli-helper` | `cli-helper` | `medium` | typer, funcs:1 | src/stackops/utils/cli_utils/secret_input.py |  |
| `stackops.utils.cli_utils.standard_streams` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/utils/cli_utils/standard_streams.py |  |

## Assets And Package Markers

These **223** modules are package markers, settings/config packages, or executable assets.

| Module | Marker | Label | Confidence | Signals | Path | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `stackops` | `package` | `package-marker` | `high` | - | src/stackops/__init__.py |  |
| `stackops.architecture_graph` | `package` | `package-marker` | `high` | - | src/stackops/architecture_graph/__init__.py |  |
| `stackops.cluster` | `package` | `package-marker` | `high` | api-doc | src/stackops/cluster/__init__.py |  |
| `stackops.cluster.remote` | `package` | `package-marker` | `high` | api-doc | src/stackops/cluster/remote/__init__.py |  |
| `stackops.cluster.sessions_managers` | `package` | `package-marker` | `high` | api-doc | src/stackops/cluster/sessions_managers/__init__.py |  |
| `stackops.cluster.sessions_managers.helpers` | `package` | `package-marker` | `high` | api-doc | src/stackops/cluster/sessions_managers/helpers/__init__.py |  |
| `stackops.cluster.sessions_managers.tmux` | `package` | `package-marker` | `high` | api-doc | src/stackops/cluster/sessions_managers/tmux/__init__.py |  |
| `stackops.cluster.sessions_managers.tmux.tmux_utils` | `package` | `package-marker` | `high` | api-doc | src/stackops/cluster/sessions_managers/tmux/tmux_utils/__init__.py |  |
| `stackops.cluster.sessions_managers.utils` | `package` | `package-marker` | `high` | api-doc | src/stackops/cluster/sessions_managers/utils/__init__.py |  |
| `stackops.jobs` | `package` | `package-marker` | `high` | api-doc | src/stackops/jobs/__init__.py |  |
| `stackops.jobs.agents.mcps` | `package` | `package-marker` | `high` | - | src/stackops/jobs/agents/mcps/__init__.py |  |
| `stackops.jobs.installer` | `package` | `package-marker` | `high` | api-doc | src/stackops/jobs/installer/__init__.py |  |
| `stackops.jobs.installer.checks` | `package` | `package-marker` | `high` | api-doc | src/stackops/jobs/installer/checks/__init__.py |  |
| `stackops.jobs.installer.linux_scripts` | `package` | `package-marker` | `high` | api-doc | src/stackops/jobs/installer/linux_scripts/__init__.py |  |
| `stackops.jobs.installer.macos_scripts` | `package` | `package-marker` | `high` | api-doc | src/stackops/jobs/installer/macos_scripts/__init__.py |  |
| `stackops.jobs.installer.powershell_scripts` | `package` | `package-marker` | `high` | api-doc | src/stackops/jobs/installer/powershell_scripts/__init__.py |  |
| `stackops.jobs.installer.python_scripts` | `package` | `package-marker` | `high` | api-doc | src/stackops/jobs/installer/python_scripts/__init__.py |  |
| `stackops.jobs.installer.python_scripts.alacritty` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:1 | src/stackops/jobs/installer/python_scripts/alacritty.py |  |
| `stackops.jobs.installer.python_scripts.boxes` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:1 | src/stackops/jobs/installer/python_scripts/boxes.py |  |
| `stackops.jobs.installer.python_scripts.brave` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:2 | src/stackops/jobs/installer/python_scripts/brave.py |  |
| `stackops.jobs.installer.python_scripts.bypass_paywall` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:1 | src/stackops/jobs/installer/python_scripts/bypass_paywall.py |  |
| `stackops.jobs.installer.python_scripts.cloudflare_warp_cli` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:2 | src/stackops/jobs/installer/python_scripts/cloudflare_warp_cli.py |  |
| `stackops.jobs.installer.python_scripts.code` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:2 | src/stackops/jobs/installer/python_scripts/code.py |  |
| `stackops.jobs.installer.python_scripts.cursor` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:3 | src/stackops/jobs/installer/python_scripts/cursor.py |  |
| `stackops.jobs.installer.python_scripts.deer_flow` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, funcs:1 | src/stackops/jobs/installer/python_scripts/deer_flow.py |  |
| `stackops.jobs.installer.python_scripts.docker` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:3 | src/stackops/jobs/installer/python_scripts/docker.py |  |
| `stackops.jobs.installer.python_scripts.dubdb_adbc` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:1 | src/stackops/jobs/installer/python_scripts/dubdb_adbc.py |  |
| `stackops.jobs.installer.python_scripts.espanso` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:4 | src/stackops/jobs/installer/python_scripts/espanso.py |  |
| `stackops.jobs.installer.python_scripts.freellmapi` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:7 | src/stackops/jobs/installer/python_scripts/freellmapi.py |  |
| `stackops.jobs.installer.python_scripts.goes` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, funcs:1 | src/stackops/jobs/installer/python_scripts/goes.py |  |
| `stackops.jobs.installer.python_scripts.hx` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:1 | src/stackops/jobs/installer/python_scripts/hx.py |  |
| `stackops.jobs.installer.python_scripts.lvim` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:1 | src/stackops/jobs/installer/python_scripts/lvim.py |  |
| `stackops.jobs.installer.python_scripts.nerdfont` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:17 | src/stackops/jobs/installer/python_scripts/nerdfont.py |  |
| `stackops.jobs.installer.python_scripts.orca` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:12 | src/stackops/jobs/installer/python_scripts/orca.py |  |
| `stackops.jobs.installer.python_scripts.oz` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:2 | src/stackops/jobs/installer/python_scripts/oz.py |  |
| `stackops.jobs.installer.python_scripts.poppler` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:2 | src/stackops/jobs/installer/python_scripts/poppler.py |  |
| `stackops.jobs.installer.python_scripts.psmux` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, funcs:1 | src/stackops/jobs/installer/python_scripts/psmux.py |  |
| `stackops.jobs.installer.python_scripts.redis` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:2 | src/stackops/jobs/installer/python_scripts/redis.py |  |
| `stackops.jobs.installer.python_scripts.rmpc` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:25 | src/stackops/jobs/installer/python_scripts/rmpc.py |  |
| `stackops.jobs.installer.python_scripts.rustdesk_server` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, funcs:3 | src/stackops/jobs/installer/python_scripts/rustdesk_server.py |  |
| `stackops.jobs.installer.python_scripts.sysabc` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:2 | src/stackops/jobs/installer/python_scripts/sysabc.py |  |
| `stackops.jobs.installer.python_scripts.termusic` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:19 | src/stackops/jobs/installer/python_scripts/termusic.py |  |
| `stackops.jobs.installer.python_scripts.wezterm` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:2 | src/stackops/jobs/installer/python_scripts/wezterm.py |  |
| `stackops.jobs.installer.python_scripts.winget` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:5 | src/stackops/jobs/installer/python_scripts/winget.py |  |
| `stackops.jobs.installer.python_scripts.yazi` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:2 | src/stackops/jobs/installer/python_scripts/yazi.py |  |
| `stackops.jobs.installer.python_scripts.youtube_tui` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:14 | src/stackops/jobs/installer/python_scripts/youtube_tui.py |  |
| `stackops.jobs.installer.python_scripts.ytui_music` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:23 | src/stackops/jobs/installer/python_scripts/ytui_music.py |  |
| `stackops.jobs.scripts.bash_scripts` | `package` | `package-marker` | `high` | - | src/stackops/jobs/scripts/bash_scripts/__init__.py |  |
| `stackops.jobs.scripts.powershell_scripts` | `package` | `package-marker` | `high` | - | src/stackops/jobs/scripts/powershell_scripts/__init__.py |  |
| `stackops.jobs.scripts.python_scripts.chatgpt_random_questions` | `script-asset` | `script-asset` | `medium` | typer, typer-app, cli-registration, main, __main__, classes:1, funcs:10 | src/stackops/jobs/scripts/python_scripts/chatgpt_random_questions.py |  |
| `stackops.jobs.scripts.python_scripts.gh` | `script-asset` | `script-asset` | `medium` | typer, typer-app, cli-registration, main, __main__, classes:9, funcs:73 | src/stackops/jobs/scripts/python_scripts/gh.py |  |
| `stackops.jobs.scripts_dynamic` | `package` | `package-marker` | `high` | - | src/stackops/jobs/scripts_dynamic/__init__.py |  |
| `stackops.jobs.scripts_dynamic.download_stackops_offline_installer` | `script-asset` | `script-asset` | `medium` | main, __main__, classes:1, funcs:10 | src/stackops/jobs/scripts_dynamic/download_stackops_offline_installer.py |  |
| `stackops.jobs.scripts_dynamic.system_compute_analyzer` | `script-asset` | `script-asset` | `medium` | main, __main__, classes:4, funcs:2 | src/stackops/jobs/scripts_dynamic/system_compute_analyzer.py |  |
| `stackops.profile` | `package` | `package-marker` | `high` | - | src/stackops/profile/__init__.py |  |
| `stackops.profile.linking` | `package` | `package-marker` | `high` | - | src/stackops/profile/linking/__init__.py |  |
| `stackops.scripts` | `package` | `package-marker` | `high` | - | src/stackops/scripts/__init__.py |  |
| `stackops.scripts.linux` | `package` | `package-marker` | `high` | - | src/stackops/scripts/linux/__init__.py |  |
| `stackops.scripts.nu` | `package` | `package-marker` | `high` | - | src/stackops/scripts/nu/__init__.py |  |
| `stackops.scripts.python` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/__init__.py |  |
| `stackops.scripts.python.ai` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/ai/__init__.py |  |
| `stackops.scripts.python.ai.scripts` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/ai/scripts/__init__.py |  |
| `stackops.scripts.python.ai.solutions` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/ai/solutions/__init__.py |  |
| `stackops.scripts.python.ai.solutions.antigravity` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/ai/solutions/antigravity/__init__.py |  |
| `stackops.scripts.python.ai.solutions.auggie` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/ai/solutions/auggie/__init__.py |  |
| `stackops.scripts.python.ai.solutions.codex` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/ai/solutions/codex/__init__.py |  |
| `stackops.scripts.python.ai.solutions.copilot` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/ai/solutions/copilot/__init__.py |  |
| `stackops.scripts.python.ai.solutions.copilot.agents` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/ai/solutions/copilot/agents/__init__.py |  |
| `stackops.scripts.python.ai.solutions.copilot.instructions.archive` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/ai/solutions/copilot/instructions/archive/__init__.py |  |
| `stackops.scripts.python.ai.solutions.copilot.instructions.python` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/ai/solutions/copilot/instructions/python/__init__.py |  |
| `stackops.scripts.python.ai.solutions.copilot.prompts` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/ai/solutions/copilot/prompts/__init__.py |  |
| `stackops.scripts.python.ai.solutions.crush` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/ai/solutions/crush/__init__.py |  |
| `stackops.scripts.python.ai.solutions.deepseek` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/ai/solutions/deepseek/__init__.py |  |
| `stackops.scripts.python.ai.solutions.droid` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/ai/solutions/droid/__init__.py |  |
| `stackops.scripts.python.ai.solutions.forge` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/ai/solutions/forge/__init__.py |  |
| `stackops.scripts.python.ai.solutions.kilocode` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/ai/solutions/kilocode/__init__.py |  |
| `stackops.scripts.python.ai.solutions.maki` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/ai/solutions/maki/__init__.py |  |
| `stackops.scripts.python.ai.solutions.muse` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/ai/solutions/muse/__init__.py |  |
| `stackops.scripts.python.ai.solutions.omp` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/ai/solutions/omp/__init__.py |  |
| `stackops.scripts.python.ai.solutions.opencode` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/ai/solutions/opencode/__init__.py |  |
| `stackops.scripts.python.ai.solutions.oz` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/ai/solutions/oz/__init__.py |  |
| `stackops.scripts.python.ai.solutions.pi` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/ai/solutions/pi/__init__.py |  |
| `stackops.scripts.python.ai.solutions.prime_agent` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/ai/solutions/prime_agent/__init__.py |  |
| `stackops.scripts.python.ai.solutions.q` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/ai/solutions/q/__init__.py |  |
| `stackops.scripts.python.ai.solutions.qwen_code` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/ai/solutions/qwen_code/__init__.py |  |
| `stackops.scripts.python.ai.solutions.warp` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/ai/solutions/warp/__init__.py |  |
| `stackops.scripts.python.ai.utils` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/ai/utils/__init__.py |  |
| `stackops.scripts.python.graph` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/graph/__init__.py |  |
| `stackops.scripts.python.graph.visualize` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/graph/visualize/__init__.py |  |
| `stackops.scripts.python.graph.visualize.helpers_navigator` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/graph/visualize/helpers_navigator/__init__.py |  |
| `stackops.scripts.python.helpers` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_agents/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agentic_frameworks` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_agents/agentic_frameworks/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.browser_guides` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_agents/browser_guides/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.browser_launchers` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_agents/browser_launchers/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.aichat` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/aichat/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.auggie` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/auggie/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.chatgpt` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/chatgpt/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.cline` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/cline/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.codex` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/codex/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.common` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/common/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.copilot` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/copilot/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.crush` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/crush/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.cursor` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/cursor/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.droid` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/droid/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.kilocode` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/kilocode/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.mods` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/mods/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.opencode` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/opencode/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.q` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/q/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.qwen` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/qwen/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_cloud` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_cloud/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_devops` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_devops/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_devops.mount_helpers` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_devops/mount_helpers/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_devops.themes` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_devops/themes/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_env` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_env/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_fire_command` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_fire_command/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_network` | `package` | `package-marker` | `high` | api-doc | src/stackops/scripts/python/helpers/helpers_network/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_network.ssh` | `package` | `package-marker` | `high` | api-doc | src/stackops/scripts/python/helpers/helpers_network/ssh/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_preview` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_preview/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_seek` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_seek/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_seek.scripts_linux` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_seek/scripts_linux/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_seek.scripts_macos` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_seek/scripts_macos/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_seek.scripts_windows` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_seek/scripts_windows/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_seek.semantic` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_seek/semantic/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_sessions` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_sessions/__init__.py |  |
| `stackops.scripts.setup.linux` | `package` | `package-marker` | `high` | - | src/stackops/scripts/setup/linux/__init__.py |  |
| `stackops.scripts.setup.macos` | `package` | `package-marker` | `high` | - | src/stackops/scripts/setup/macos/__init__.py |  |
| `stackops.scripts.setup.windows` | `package` | `package-marker` | `high` | - | src/stackops/scripts/setup/windows/__init__.py |  |
| `stackops.scripts.windows` | `package` | `package-marker` | `high` | - | src/stackops/scripts/windows/__init__.py |  |
| `stackops.secrets` | `package` | `package-marker` | `high` | api-doc | src/stackops/secrets/__init__.py | Was `secrets.py`; now a package with submodules. |
| `stackops.settings` | `package` | `package-marker` | `high` | - | src/stackops/settings/__init__.py |  |
| `stackops.settings.atuin` | `package` | `package-marker` | `high` | - | src/stackops/settings/atuin/__init__.py |  |
| `stackops.settings.atuin.themes` | `package` | `package-marker` | `high` | - | src/stackops/settings/atuin/themes/__init__.py |  |
| `stackops.settings.broot` | `package` | `package-marker` | `high` | - | src/stackops/settings/broot/__init__.py |  |
| `stackops.settings.glow` | `package` | `package-marker` | `high` | - | src/stackops/settings/glow/__init__.py |  |
| `stackops.settings.gromit-mpx` | `package` | `package-marker` | `high` | - | src/stackops/settings/gromit-mpx/__init__.py |  |
| `stackops.settings.helix` | `package` | `package-marker` | `high` | - | src/stackops/settings/helix/__init__.py |  |
| `stackops.settings.herdr` | `package` | `package-marker` | `high` | - | src/stackops/settings/herdr/__init__.py |  |
| `stackops.settings.keras` | `package` | `package-marker` | `high` | - | src/stackops/settings/keras/__init__.py |  |
| `stackops.settings.keyboard.espanso.config` | `package` | `package-marker` | `high` | - | src/stackops/settings/keyboard/espanso/config/__init__.py |  |
| `stackops.settings.keyboard.espanso.match` | `package` | `package-marker` | `high` | - | src/stackops/settings/keyboard/espanso/match/__init__.py |  |
| `stackops.settings.keyboard.kanata` | `package` | `package-marker` | `high` | - | src/stackops/settings/keyboard/kanata/__init__.py |  |
| `stackops.settings.lf.linux` | `package` | `package-marker` | `high` | - | src/stackops/settings/lf/linux/__init__.py |  |
| `stackops.settings.lf.linux.autocall` | `package` | `package-marker` | `high` | - | src/stackops/settings/lf/linux/autocall/__init__.py |  |
| `stackops.settings.lf.linux.exe` | `package` | `package-marker` | `high` | - | src/stackops/settings/lf/linux/exe/__init__.py |  |
| `stackops.settings.lf.windows` | `package` | `package-marker` | `high` | - | src/stackops/settings/lf/windows/__init__.py |  |
| `stackops.settings.lf.windows.autocall` | `package` | `package-marker` | `high` | - | src/stackops/settings/lf/windows/autocall/__init__.py |  |
| `stackops.settings.linters` | `package` | `package-marker` | `high` | - | src/stackops/settings/linters/__init__.py |  |
| `stackops.settings.lvim.linux` | `package` | `package-marker` | `high` | - | src/stackops/settings/lvim/linux/__init__.py |  |
| `stackops.settings.lvim.windows` | `package` | `package-marker` | `high` | - | src/stackops/settings/lvim/windows/__init__.py |  |
| `stackops.settings.lvim.windows.archive` | `package` | `package-marker` | `high` | - | src/stackops/settings/lvim/windows/archive/__init__.py |  |
| `stackops.settings.lvim.windows.lua.user` | `package` | `package-marker` | `high` | - | src/stackops/settings/lvim/windows/lua/user/__init__.py |  |
| `stackops.settings.marimo` | `package` | `package-marker` | `high` | - | src/stackops/settings/marimo/__init__.py |  |
| `stackops.settings.marimo.snippets.globalize` | `asset` | `config-asset` | `high` | __main__, funcs:3 | src/stackops/settings/marimo/snippets/globalize.py |  |
| `stackops.settings.mprocs.windows` | `package` | `package-marker` | `high` | - | src/stackops/settings/mprocs/windows/__init__.py |  |
| `stackops.settings.ollama` | `package` | `package-marker` | `high` | - | src/stackops/settings/ollama/__init__.py |  |
| `stackops.settings.pistol` | `package` | `package-marker` | `high` | - | src/stackops/settings/pistol/__init__.py |  |
| `stackops.settings.presenterm` | `package` | `package-marker` | `high` | - | src/stackops/settings/presenterm/__init__.py |  |
| `stackops.settings.psmux` | `package` | `package-marker` | `high` | - | src/stackops/settings/psmux/__init__.py |  |
| `stackops.settings.pudb` | `package` | `package-marker` | `high` | - | src/stackops/settings/pudb/__init__.py |  |
| `stackops.settings.rofi` | `package` | `package-marker` | `high` | - | src/stackops/settings/rofi/__init__.py |  |
| `stackops.settings.shells.alacritty` | `package` | `package-marker` | `high` | - | src/stackops/settings/shells/alacritty/__init__.py |  |
| `stackops.settings.shells.bash_zsh` | `package` | `package-marker` | `high` | - | src/stackops/settings/shells/bash_zsh/__init__.py |  |
| `stackops.settings.shells.ghostty` | `package` | `package-marker` | `high` | - | src/stackops/settings/shells/ghostty/__init__.py |  |
| `stackops.settings.shells.ipy.profiles.default` | `package` | `package-marker` | `high` | - | src/stackops/settings/shells/ipy/profiles/default/__init__.py |  |
| `stackops.settings.shells.ipy.profiles.default.startup` | `package` | `package-marker` | `high` | - | src/stackops/settings/shells/ipy/profiles/default/startup/__init__.py |  |
| `stackops.settings.shells.ipy.profiles.default.startup.playext` | `asset` | `config-asset` | `high` | - | src/stackops/settings/shells/ipy/profiles/default/startup/playext.py |  |
| `stackops.settings.shells.kitty` | `package` | `package-marker` | `high` | - | src/stackops/settings/shells/kitty/__init__.py |  |
| `stackops.settings.shells.nushell` | `package` | `package-marker` | `high` | - | src/stackops/settings/shells/nushell/__init__.py |  |
| `stackops.settings.shells.pwsh` | `package` | `package-marker` | `high` | - | src/stackops/settings/shells/pwsh/__init__.py |  |
| `stackops.settings.shells.starship` | `package` | `package-marker` | `high` | - | src/stackops/settings/shells/starship/__init__.py |  |
| `stackops.settings.shells.vtm` | `package` | `package-marker` | `high` | - | src/stackops/settings/shells/vtm/__init__.py |  |
| `stackops.settings.shells.wezterm` | `package` | `package-marker` | `high` | - | src/stackops/settings/shells/wezterm/__init__.py |  |
| `stackops.settings.shells.wt` | `package` | `package-marker` | `high` | - | src/stackops/settings/shells/wt/__init__.py |  |
| `stackops.settings.streamlit` | `package` | `package-marker` | `high` | - | src/stackops/settings/streamlit/__init__.py |  |
| `stackops.settings.svim.linux` | `package` | `package-marker` | `high` | - | src/stackops/settings/svim/linux/__init__.py |  |
| `stackops.settings.svim.windows` | `package` | `package-marker` | `high` | - | src/stackops/settings/svim/windows/__init__.py |  |
| `stackops.settings.television.cable_unix` | `package` | `package-marker` | `high` | - | src/stackops/settings/television/cable_unix/__init__.py |  |
| `stackops.settings.television.cable_windows` | `package` | `package-marker` | `high` | - | src/stackops/settings/television/cable_windows/__init__.py |  |
| `stackops.settings.tere` | `package` | `package-marker` | `high` | - | src/stackops/settings/tere/__init__.py |  |
| `stackops.settings.tmux` | `package` | `package-marker` | `high` | - | src/stackops/settings/tmux/__init__.py |  |
| `stackops.settings.tv` | `package` | `package-marker` | `high` | - | src/stackops/settings/tv/__init__.py |  |
| `stackops.settings.tv.themes` | `package` | `package-marker` | `high` | - | src/stackops/settings/tv/themes/__init__.py |  |
| `stackops.settings.wt` | `package` | `package-marker` | `high` | - | src/stackops/settings/wt/__init__.py |  |
| `stackops.settings.wt.set_wt_settings` | `asset` | `config-asset` | `high` | main, __main__, funcs:3 | src/stackops/settings/wt/set_wt_settings.py |  |
| `stackops.settings.yazi` | `package` | `package-marker` | `high` | - | src/stackops/settings/yazi/__init__.py |  |
| `stackops.settings.yazi.scripts` | `package` | `package-marker` | `high` | - | src/stackops/settings/yazi/scripts/__init__.py |  |
| `stackops.settings.yazi.scripts.compress_selected` | `script-asset` | `script-asset` | `medium` | main, __main__, funcs:6 | src/stackops/settings/yazi/scripts/compress_selected.py |  |
| `stackops.settings.yazi.scripts.copy_file_content` | `script-asset` | `script-asset` | `medium` | main, __main__, funcs:4 | src/stackops/settings/yazi/scripts/copy_file_content.py |  |
| `stackops.settings.yazi.scripts.fullscreen_preview` | `script-asset` | `script-asset` | `medium` | main, __main__, funcs:26 | src/stackops/settings/yazi/scripts/fullscreen_preview.py |  |
| `stackops.settings.yazi.scripts.interactive_view` | `script-asset` | `script-asset` | `medium` | main, __main__, funcs:10 | src/stackops/settings/yazi/scripts/interactive_view.py |  |
| `stackops.settings.yazi.scripts.open_db_readonly` | `script-asset` | `script-asset` | `medium` | main, __main__, funcs:7 | src/stackops/settings/yazi/scripts/open_db_readonly.py |  |
| `stackops.settings.yazi.scripts.open_default_app` | `script-asset` | `script-asset` | `medium` | main, __main__, classes:1, funcs:16 | src/stackops/settings/yazi/scripts/open_default_app.py |  |
| `stackops.settings.yazi.scripts.serve_browser_file` | `script-asset` | `script-asset` | `medium` | main, __main__, classes:1, funcs:12 | src/stackops/settings/yazi/scripts/serve_browser_file.py |  |
| `stackops.settings.yazi.scripts.serve_directory` | `script-asset` | `script-asset` | `medium` | typer, main, __main__, classes:1, funcs:3 | src/stackops/settings/yazi/scripts/serve_directory.py |  |
| `stackops.settings.yazi.shell` | `package` | `package-marker` | `high` | - | src/stackops/settings/yazi/shell/__init__.py |  |
| `stackops.settings.zed` | `package` | `package-marker` | `high` | - | src/stackops/settings/zed/__init__.py |  |
| `stackops.utils` | `package` | `package-marker` | `high` | api-doc | src/stackops/utils/__init__.py |  |
| `stackops.utils.cli_utils` | `package` | `package-marker` | `high` | - | src/stackops/utils/cli_utils/__init__.py |  |
| `stackops.utils.cloud` | `package` | `package-marker` | `high` | - | src/stackops/utils/cloud/__init__.py |  |
| `stackops.utils.cloud.onedrive` | `package` | `package-marker` | `high` | - | src/stackops/utils/cloud/onedrive/__init__.py |  |
| `stackops.utils.dashboards` | `package` | `package-marker` | `high` | - | src/stackops/utils/dashboards/__init__.py |  |
| `stackops.utils.files` | `package` | `package-marker` | `high` | - | src/stackops/utils/files/__init__.py |  |
| `stackops.utils.files.art` | `package` | `package-marker` | `high` | - | src/stackops/utils/files/art/__init__.py |  |
| `stackops.utils.files.ouch` | `package` | `package-marker` | `high` | - | src/stackops/utils/files/ouch/__init__.py |  |
| `stackops.utils.installer_utils` | `package` | `package-marker` | `high` | api-doc | src/stackops/utils/installer_utils/__init__.py |  |
| `stackops.utils.machine` | `package` | `package-marker` | `high` | - | src/stackops/utils/machine/__init__.py |  |
| `stackops.utils.network` | `package` | `package-marker` | `high` | - | src/stackops/utils/network/__init__.py |  |
| `stackops.utils.options_utils` | `package` | `package-marker` | `high` | - | src/stackops/utils/options_utils/__init__.py |  |
| `stackops.utils.python` | `package` | `package-marker` | `high` | - | src/stackops/utils/python/__init__.py |  |
| `stackops.utils.repos` | `package` | `package-marker` | `high` | - | src/stackops/utils/repos/__init__.py |  |
| `stackops.utils.schemas` | `package` | `package-marker` | `high` | - | src/stackops/utils/schemas/__init__.py |  |
| `stackops.utils.schemas.agents` | `package` | `package-marker` | `high` | - | src/stackops/utils/schemas/agents/__init__.py |  |
| `stackops.utils.schemas.config` | `package` | `package-marker` | `high` | __all__ | src/stackops/utils/schemas/config/__init__.py |  |
| `stackops.utils.schemas.fire_agents` | `package` | `package-marker` | `high` | - | src/stackops/utils/schemas/fire_agents/__init__.py |  |
| `stackops.utils.schemas.installer` | `package` | `package-marker` | `high` | api-doc | src/stackops/utils/schemas/installer/__init__.py |  |
| `stackops.utils.schemas.layouts` | `package` | `package-marker` | `high` | api-doc | src/stackops/utils/schemas/layouts/__init__.py |  |
| `stackops.utils.schemas.mapper` | `package` | `package-marker` | `high` | - | src/stackops/utils/schemas/mapper/__init__.py |  |
| `stackops.utils.schemas.repos` | `package` | `package-marker` | `high` | - | src/stackops/utils/schemas/repos/__init__.py |  |
| `stackops.utils.schemas.startup` | `package` | `package-marker` | `high` | - | src/stackops/utils/schemas/startup/__init__.py |  |
| `stackops.utils.ssh_utils` | `package` | `package-marker` | `high` | api-doc | src/stackops/utils/ssh_utils/__init__.py |  |

## Full Inventory

`Imported by` is the number of other modules in scope that import the module (`import x`, `from x import ...` or `from package import x`). `LOC` is the number of lines in the file.

| Module | Marker | Label | Confidence | Imported by | LOC | Signals | Path | Notes |
| --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| `stackops` | `package` | `package-marker` | `high` | 2 | 0 | - | src/stackops/__init__.py |  |
| `stackops.architecture_graph` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/architecture_graph/__init__.py |  |
| `stackops.architecture_graph.__main__` | `api-or-script` | `manual-review` | `medium` | 0 | 5 | __main__ | src/stackops/architecture_graph/__main__.py |  |
| `stackops.architecture_graph.cli` | `api-or-script` | `manual-review` | `medium` | 2 | 70 | main, classes:1, funcs:3 | src/stackops/architecture_graph/cli.py |  |
| `stackops.architecture_graph.graph` | `api` | `python-api-candidate` | `medium` | 2 | 148 | funcs:8 | src/stackops/architecture_graph/graph.py |  |
| `stackops.architecture_graph.models` | `api` | `python-api-candidate` | `medium` | 3 | 54 | classes:6 | src/stackops/architecture_graph/models.py |  |
| `stackops.architecture_graph.renderer` | `api` | `python-api-candidate` | `medium` | 2 | 90 | funcs:3 | src/stackops/architecture_graph/renderer.py |  |
| `stackops.architecture_graph.scanner` | `api` | `python-api-candidate` | `medium` | 1 | 106 | classes:1, funcs:8 | src/stackops/architecture_graph/scanner.py |  |
| `stackops.cluster` | `package` | `package-marker` | `high` | 0 | 0 | api-doc | src/stackops/cluster/__init__.py |  |
| `stackops.cluster.remote` | `package` | `package-marker` | `high` | 0 | 0 | api-doc | src/stackops/cluster/remote/__init__.py |  |
| `stackops.cluster.remote.cloud_manager` | `api` | `python-api` | `high` | 0 | 377 | api-doc, classes:2, funcs:9 | src/stackops/cluster/remote/cloud_manager.py |  |
| `stackops.cluster.remote.data_transfer` | `api` | `python-api` | `high` | 1 | 45 | api-doc, funcs:3 | src/stackops/cluster/remote/data_transfer.py |  |
| `stackops.cluster.remote.distribute` | `api` | `python-api` | `high` | 0 | 303 | api-doc, classes:5, funcs:6 | src/stackops/cluster/remote/distribute.py |  |
| `stackops.cluster.remote.execution_script` | `api` | `python-api` | `high` | 1 | 91 | api-doc, funcs:1 | src/stackops/cluster/remote/execution_script.py |  |
| `stackops.cluster.remote.file_manager` | `api` | `python-api` | `high` | 2 | 243 | api-doc, classes:1, funcs:6 | src/stackops/cluster/remote/file_manager.py |  |
| `stackops.cluster.remote.job_params` | `api` | `python-api` | `high` | 2 | 132 | api-doc, classes:1, funcs:2 | src/stackops/cluster/remote/job_params.py |  |
| `stackops.cluster.remote.models` | `api` | `python-api` | `high` | 6 | 220 | api-doc, classes:5, funcs:3 | src/stackops/cluster/remote/models.py |  |
| `stackops.cluster.remote.remote_machine` | `api` | `python-api` | `high` | 2 | 257 | api-doc, classes:1, funcs:1 | src/stackops/cluster/remote/remote_machine.py |  |
| `stackops.cluster.scheduler` | `api` | `python-api` | `high` | 2 | 265 | api-doc, classes:4, funcs:2 | src/stackops/cluster/scheduler.py | Was `utils.scheduler`; moved to `cluster/`. |
| `stackops.cluster.sessions_managers` | `package` | `package-marker` | `high` | 0 | 0 | api-doc | src/stackops/cluster/sessions_managers/__init__.py |  |
| `stackops.cluster.sessions_managers.helpers` | `package` | `package-marker` | `high` | 0 | 1 | api-doc | src/stackops/cluster/sessions_managers/helpers/__init__.py |  |
| `stackops.cluster.sessions_managers.helpers.enhanced_command_runner` | `api` | `api-cli-bridge` | `medium` | 0 | 65 | api-doc, __main__, funcs:1 | src/stackops/cluster/sessions_managers/helpers/enhanced_command_runner.py |  |
| `stackops.cluster.sessions_managers.helpers.load_balancer_helper` | `api` | `python-api` | `high` | 1 | 153 | api-doc, funcs:10 | src/stackops/cluster/sessions_managers/helpers/load_balancer_helper.py |  |
| `stackops.cluster.sessions_managers.monitoring_types` | `api` | `python-api` | `high` | 7 | 43 | api-doc, classes:4 | src/stackops/cluster/sessions_managers/monitoring_types.py |  |
| `stackops.cluster.sessions_managers.session_conflict` | `api` | `python-api` | `high` | 14 | 379 | api-doc, classes:2, funcs:8 | src/stackops/cluster/sessions_managers/session_conflict.py |  |
| `stackops.cluster.sessions_managers.session_exit_mode` | `api` | `python-api` | `high` | 11 | 92 | api-doc, funcs:3 | src/stackops/cluster/sessions_managers/session_exit_mode.py |  |
| `stackops.cluster.sessions_managers.session_launch_table` | `api` | `python-api` | `high` | 5 | 80 | api-doc, classes:2, funcs:2 | src/stackops/cluster/sessions_managers/session_launch_table.py |  |
| `stackops.cluster.sessions_managers.status_reporting` | `api` | `python-api` | `high` | 1 | 43 | api-doc, funcs:1 | src/stackops/cluster/sessions_managers/status_reporting.py |  |
| `stackops.cluster.sessions_managers.tmux` | `package` | `package-marker` | `high` | 0 | 0 | api-doc | src/stackops/cluster/sessions_managers/tmux/__init__.py |  |
| `stackops.cluster.sessions_managers.tmux.tmux_local` | `api` | `api-cli-bridge` | `medium` | 3 | 258 | api-doc, __main__, classes:3, funcs:1 | src/stackops/cluster/sessions_managers/tmux/tmux_local.py |  |
| `stackops.cluster.sessions_managers.tmux.tmux_local_manager` | `api` | `python-api` | `high` | 2 | 213 | api-doc, classes:2 | src/stackops/cluster/sessions_managers/tmux/tmux_local_manager.py |  |
| `stackops.cluster.sessions_managers.tmux.tmux_utils` | `package` | `package-marker` | `high` | 0 | 1 | api-doc | src/stackops/cluster/sessions_managers/tmux/tmux_utils/__init__.py |  |
| `stackops.cluster.sessions_managers.tmux.tmux_utils.tmux_common` | `api` | `python-api` | `high` | 5 | 15 | api-doc, funcs:2 | src/stackops/cluster/sessions_managers/tmux/tmux_utils/tmux_common.py |  |
| `stackops.cluster.sessions_managers.tmux.tmux_utils.tmux_execution` | `api` | `python-api` | `high` | 8 | 320 | api-doc, funcs:21 | src/stackops/cluster/sessions_managers/tmux/tmux_utils/tmux_execution.py |  |
| `stackops.cluster.sessions_managers.tmux.tmux_utils.tmux_launch_table` | `api` | `python-api` | `high` | 2 | 31 | api-doc, funcs:2 | src/stackops/cluster/sessions_managers/tmux/tmux_utils/tmux_launch_table.py |  |
| `stackops.cluster.sessions_managers.tmux.tmux_utils.tmux_layout` | `api` | `python-api` | `high` | 2 | 271 | api-doc, funcs:12 | src/stackops/cluster/sessions_managers/tmux/tmux_utils/tmux_layout.py |  |
| `stackops.cluster.sessions_managers.tmux.tmux_utils.tmux_status` | `api` | `python-api` | `high` | 3 | 82 | api-doc, classes:1, funcs:2 | src/stackops/cluster/sessions_managers/tmux/tmux_utils/tmux_status.py |  |
| `stackops.cluster.sessions_managers.utils` | `package` | `package-marker` | `high` | 0 | 0 | api-doc | src/stackops/cluster/sessions_managers/utils/__init__.py |  |
| `stackops.cluster.sessions_managers.utils.load_balancer` | `api` | `python-api` | `high` | 1 | 55 | api-doc, classes:1, funcs:3 | src/stackops/cluster/sessions_managers/utils/load_balancer.py |  |
| `stackops.cluster.sessions_managers.utils.maker` | `api` | `python-api` | `high` | 0 | 119 | api-doc, funcs:5 | src/stackops/cluster/sessions_managers/utils/maker.py |  |
| `stackops.jobs` | `package` | `package-marker` | `high` | 1 | 0 | api-doc | src/stackops/jobs/__init__.py |  |
| `stackops.jobs.agents.mcps` | `package` | `package-marker` | `high` | 2 | 2 | - | src/stackops/jobs/agents/mcps/__init__.py |  |
| `stackops.jobs.installer` | `package` | `package-marker` | `high` | 2 | 1 | api-doc | src/stackops/jobs/installer/__init__.py |  |
| `stackops.jobs.installer.checks` | `package` | `package-marker` | `high` | 1 | 0 | api-doc | src/stackops/jobs/installer/checks/__init__.py |  |
| `stackops.jobs.installer.checks.app_upload` | `api` | `python-api` | `high` | 2 | 35 | api-doc, funcs:1 | src/stackops/jobs/installer/checks/app_upload.py |  |
| `stackops.jobs.installer.checks.check_installations` | `api` | `python-api` | `high` | 2 | 22 | api-doc, funcs:1 | src/stackops/jobs/installer/checks/check_installations.py |  |
| `stackops.jobs.installer.checks.constants` | `api` | `python-api` | `high` | 12 | 35 | api-doc | src/stackops/jobs/installer/checks/constants.py |  |
| `stackops.jobs.installer.checks.history_cli` | `api` | `api-cli-bridge` | `medium` | 1 | 192 | api-doc, typer, funcs:4 | src/stackops/jobs/installer/checks/history_cli.py |  |
| `stackops.jobs.installer.checks.install_utils` | `api` | `python-api` | `high` | 1 | 119 | api-doc, funcs:3 | src/stackops/jobs/installer/checks/install_utils.py |  |
| `stackops.jobs.installer.checks.report_utils` | `api` | `python-api` | `high` | 5 | 310 | api-doc, classes:4, funcs:16 | src/stackops/jobs/installer/checks/report_utils.py |  |
| `stackops.jobs.installer.checks.run_reports` | `api` | `python-api` | `high` | 2 | 72 | api-doc, funcs:2 | src/stackops/jobs/installer/checks/run_reports.py |  |
| `stackops.jobs.installer.checks.scan_execution` | `api` | `api-cli-bridge` | `medium` | 1 | 140 | api-doc, typer, funcs:1 | src/stackops/jobs/installer/checks/scan_execution.py |  |
| `stackops.jobs.installer.checks.scan_history` | `api` | `python-api` | `high` | 8 | 134 | api-doc, classes:3, funcs:4 | src/stackops/jobs/installer/checks/scan_history.py |  |
| `stackops.jobs.installer.checks.scan_outcomes` | `api` | `python-api` | `high` | 8 | 42 | api-doc, classes:3, funcs:1 | src/stackops/jobs/installer/checks/scan_outcomes.py |  |
| `stackops.jobs.installer.checks.scan_overview` | `api` | `python-api` | `high` | 4 | 202 | api-doc, classes:5, funcs:4 | src/stackops/jobs/installer/checks/scan_overview.py |  |
| `stackops.jobs.installer.checks.scan_records` | `api` | `python-api` | `high` | 1 | 66 | api-doc, funcs:1 | src/stackops/jobs/installer/checks/scan_records.py |  |
| `stackops.jobs.installer.checks.security_cli` | `api` | `api-cli-bridge` | `medium` | 1 | 153 | api-doc, typer, typer-app, cli-registration, get_app, funcs:7 | src/stackops/jobs/installer/checks/security_cli.py |  |
| `stackops.jobs.installer.checks.security_helper` | `api` | `python-api` | `high` | 5 | 38 | api-doc, funcs:3 | src/stackops/jobs/installer/checks/security_helper.py |  |
| `stackops.jobs.installer.checks.status_cli` | `api` | `api-cli-bridge` | `medium` | 1 | 66 | api-doc, typer, funcs:1 | src/stackops/jobs/installer/checks/status_cli.py |  |
| `stackops.jobs.installer.checks.vt_account_report` | `api` | `python-api` | `high` | 1 | 91 | api-doc, funcs:3 | src/stackops/jobs/installer/checks/vt_account_report.py |  |
| `stackops.jobs.installer.checks.vt_account_stats` | `api` | `python-api` | `high` | 4 | 105 | api-doc, classes:4 | src/stackops/jobs/installer/checks/vt_account_stats.py |  |
| `stackops.jobs.installer.checks.vt_accounts` | `api` | `python-api` | `high` | 2 | 50 | api-doc, classes:3, funcs:2 | src/stackops/jobs/installer/checks/vt_accounts.py |  |
| `stackops.jobs.installer.checks.vt_display` | `api` | `python-api` | `high` | 1 | 13 | api-doc, funcs:1 | src/stackops/jobs/installer/checks/vt_display.py |  |
| `stackops.jobs.installer.checks.vt_request_errors` | `api` | `python-api` | `high` | 1 | 74 | api-doc, classes:1, funcs:1 | src/stackops/jobs/installer/checks/vt_request_errors.py |  |
| `stackops.jobs.installer.checks.vt_requests` | `api` | `python-api` | `high` | 2 | 164 | api-doc, classes:4 | src/stackops/jobs/installer/checks/vt_requests.py |  |
| `stackops.jobs.installer.checks.vt_scanner` | `api` | `python-api` | `high` | 1 | 146 | api-doc, funcs:3 | src/stackops/jobs/installer/checks/vt_scanner.py |  |
| `stackops.jobs.installer.checks.vt_transport` | `api` | `python-api` | `high` | 1 | 57 | api-doc, classes:1, funcs:2 | src/stackops/jobs/installer/checks/vt_transport.py |  |
| `stackops.jobs.installer.checks.vt_utils` | `api` | `python-api` | `high` | 4 | 118 | api-doc, classes:2, funcs:5 | src/stackops/jobs/installer/checks/vt_utils.py |  |
| `stackops.jobs.installer.checks.vt_workers` | `api` | `python-api` | `high` | 1 | 163 | api-doc, classes:4, funcs:2 | src/stackops/jobs/installer/checks/vt_workers.py |  |
| `stackops.jobs.installer.linux_scripts` | `package` | `package-marker` | `high` | 1 | 4 | api-doc | src/stackops/jobs/installer/linux_scripts/__init__.py |  |
| `stackops.jobs.installer.macos_scripts` | `package` | `package-marker` | `high` | 0 | 0 | api-doc | src/stackops/jobs/installer/macos_scripts/__init__.py |  |
| `stackops.jobs.installer.powershell_scripts` | `package` | `package-marker` | `high` | 2 | 3 | api-doc | src/stackops/jobs/installer/powershell_scripts/__init__.py |  |
| `stackops.jobs.installer.python_scripts` | `package` | `package-marker` | `high` | 0 | 0 | api-doc | src/stackops/jobs/installer/python_scripts/__init__.py |  |
| `stackops.jobs.installer.python_scripts.alacritty` | `script-asset` | `installer-script-asset` | `high` | 0 | 91 | api-doc, main, __main__, funcs:1 | src/stackops/jobs/installer/python_scripts/alacritty.py |  |
| `stackops.jobs.installer.python_scripts.boxes` | `script-asset` | `installer-script-asset` | `high` | 0 | 67 | api-doc, main, __main__, funcs:1 | src/stackops/jobs/installer/python_scripts/boxes.py |  |
| `stackops.jobs.installer.python_scripts.brave` | `script-asset` | `installer-script-asset` | `high` | 0 | 121 | api-doc, main, __main__, funcs:2 | src/stackops/jobs/installer/python_scripts/brave.py |  |
| `stackops.jobs.installer.python_scripts.bypass_paywall` | `script-asset` | `installer-script-asset` | `high` | 0 | 83 | api-doc, main, __main__, funcs:1 | src/stackops/jobs/installer/python_scripts/bypass_paywall.py |  |
| `stackops.jobs.installer.python_scripts.cloudflare_warp_cli` | `script-asset` | `installer-script-asset` | `high` | 0 | 81 | api-doc, main, __main__, funcs:2 | src/stackops/jobs/installer/python_scripts/cloudflare_warp_cli.py |  |
| `stackops.jobs.installer.python_scripts.code` | `script-asset` | `installer-script-asset` | `high` | 0 | 119 | api-doc, main, __main__, funcs:2 | src/stackops/jobs/installer/python_scripts/code.py |  |
| `stackops.jobs.installer.python_scripts.cursor` | `script-asset` | `installer-script-asset` | `high` | 0 | 122 | api-doc, main, __main__, funcs:3 | src/stackops/jobs/installer/python_scripts/cursor.py |  |
| `stackops.jobs.installer.python_scripts.deer_flow` | `script-asset` | `installer-script-asset` | `high` | 0 | 63 | api-doc, main, funcs:1 | src/stackops/jobs/installer/python_scripts/deer_flow.py |  |
| `stackops.jobs.installer.python_scripts.docker` | `script-asset` | `installer-script-asset` | `high` | 0 | 193 | api-doc, main, __main__, funcs:3 | src/stackops/jobs/installer/python_scripts/docker.py |  |
| `stackops.jobs.installer.python_scripts.dubdb_adbc` | `script-asset` | `installer-script-asset` | `high` | 0 | 39 | api-doc, main, __main__, funcs:1 | src/stackops/jobs/installer/python_scripts/dubdb_adbc.py |  |
| `stackops.jobs.installer.python_scripts.espanso` | `script-asset` | `installer-script-asset` | `high` | 0 | 145 | api-doc, main, __main__, funcs:4 | src/stackops/jobs/installer/python_scripts/espanso.py |  |
| `stackops.jobs.installer.python_scripts.freellmapi` | `script-asset` | `installer-script-asset` | `high` | 0 | 102 | api-doc, main, __main__, funcs:7 | src/stackops/jobs/installer/python_scripts/freellmapi.py |  |
| `stackops.jobs.installer.python_scripts.goes` | `script-asset` | `installer-script-asset` | `high` | 0 | 68 | api-doc, main, funcs:1 | src/stackops/jobs/installer/python_scripts/goes.py |  |
| `stackops.jobs.installer.python_scripts.hx` | `script-asset` | `installer-script-asset` | `high` | 0 | 230 | api-doc, main, __main__, funcs:1 | src/stackops/jobs/installer/python_scripts/hx.py |  |
| `stackops.jobs.installer.python_scripts.lvim` | `script-asset` | `installer-script-asset` | `high` | 0 | 94 | api-doc, main, __main__, funcs:1 | src/stackops/jobs/installer/python_scripts/lvim.py |  |
| `stackops.jobs.installer.python_scripts.nerdfont` | `script-asset` | `installer-script-asset` | `high` | 0 | 362 | api-doc, main, __main__, funcs:17 | src/stackops/jobs/installer/python_scripts/nerdfont.py |  |
| `stackops.jobs.installer.python_scripts.orca` | `script-asset` | `installer-script-asset` | `high` | 0 | 157 | api-doc, main, __main__, funcs:12 | src/stackops/jobs/installer/python_scripts/orca.py |  |
| `stackops.jobs.installer.python_scripts.oz` | `script-asset` | `installer-script-asset` | `high` | 0 | 105 | api-doc, main, __main__, funcs:2 | src/stackops/jobs/installer/python_scripts/oz.py |  |
| `stackops.jobs.installer.python_scripts.poppler` | `script-asset` | `installer-script-asset` | `high` | 0 | 68 | api-doc, main, __main__, funcs:2 | src/stackops/jobs/installer/python_scripts/poppler.py |  |
| `stackops.jobs.installer.python_scripts.psmux` | `script-asset` | `installer-script-asset` | `high` | 0 | 44 | api-doc, main, funcs:1 | src/stackops/jobs/installer/python_scripts/psmux.py |  |
| `stackops.jobs.installer.python_scripts.redis` | `script-asset` | `installer-script-asset` | `high` | 0 | 118 | api-doc, main, __main__, funcs:2 | src/stackops/jobs/installer/python_scripts/redis.py |  |
| `stackops.jobs.installer.python_scripts.rmpc` | `script-asset` | `installer-script-asset` | `high` | 0 | 485 | api-doc, main, __main__, funcs:25 | src/stackops/jobs/installer/python_scripts/rmpc.py |  |
| `stackops.jobs.installer.python_scripts.rustdesk_server` | `script-asset` | `installer-script-asset` | `high` | 0 | 69 | api-doc, main, funcs:3 | src/stackops/jobs/installer/python_scripts/rustdesk_server.py |  |
| `stackops.jobs.installer.python_scripts.sysabc` | `script-asset` | `installer-script-asset` | `high` | 0 | 174 | api-doc, main, __main__, funcs:2 | src/stackops/jobs/installer/python_scripts/sysabc.py |  |
| `stackops.jobs.installer.python_scripts.termusic` | `script-asset` | `installer-script-asset` | `high` | 0 | 314 | api-doc, main, __main__, funcs:19 | src/stackops/jobs/installer/python_scripts/termusic.py |  |
| `stackops.jobs.installer.python_scripts.wezterm` | `script-asset` | `installer-script-asset` | `high` | 0 | 114 | api-doc, main, __main__, funcs:2 | src/stackops/jobs/installer/python_scripts/wezterm.py |  |
| `stackops.jobs.installer.python_scripts.winget` | `script-asset` | `installer-script-asset` | `high` | 0 | 181 | api-doc, main, __main__, funcs:5 | src/stackops/jobs/installer/python_scripts/winget.py |  |
| `stackops.jobs.installer.python_scripts.yazi` | `script-asset` | `installer-script-asset` | `high` | 0 | 156 | api-doc, main, __main__, funcs:2 | src/stackops/jobs/installer/python_scripts/yazi.py |  |
| `stackops.jobs.installer.python_scripts.youtube_tui` | `script-asset` | `installer-script-asset` | `high` | 0 | 263 | api-doc, main, __main__, funcs:14 | src/stackops/jobs/installer/python_scripts/youtube_tui.py |  |
| `stackops.jobs.installer.python_scripts.ytui_music` | `script-asset` | `installer-script-asset` | `high` | 0 | 364 | api-doc, main, __main__, funcs:23 | src/stackops/jobs/installer/python_scripts/ytui_music.py |  |
| `stackops.jobs.scripts.bash_scripts` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/jobs/scripts/bash_scripts/__init__.py |  |
| `stackops.jobs.scripts.powershell_scripts` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/jobs/scripts/powershell_scripts/__init__.py |  |
| `stackops.jobs.scripts.python_scripts.chatgpt_random_questions` | `script-asset` | `script-asset` | `medium` | 0 | 362 | typer, typer-app, cli-registration, main, __main__, classes:1, funcs:10 | src/stackops/jobs/scripts/python_scripts/chatgpt_random_questions.py |  |
| `stackops.jobs.scripts.python_scripts.gh` | `script-asset` | `script-asset` | `medium` | 0 | 1292 | typer, typer-app, cli-registration, main, __main__, classes:9, funcs:73 | src/stackops/jobs/scripts/python_scripts/gh.py |  |
| `stackops.jobs.scripts_dynamic` | `package` | `package-marker` | `high` | 2 | 3 | - | src/stackops/jobs/scripts_dynamic/__init__.py |  |
| `stackops.jobs.scripts_dynamic.download_stackops_offline_installer` | `script-asset` | `script-asset` | `medium` | 1 | 148 | main, __main__, classes:1, funcs:10 | src/stackops/jobs/scripts_dynamic/download_stackops_offline_installer.py |  |
| `stackops.jobs.scripts_dynamic.system_compute_analyzer` | `script-asset` | `script-asset` | `medium` | 1 | 437 | main, __main__, classes:4, funcs:2 | src/stackops/jobs/scripts_dynamic/system_compute_analyzer.py |  |
| `stackops.logger` | `api` | `python-api` | `high` | 1 | 48 | api-doc, funcs:2 | src/stackops/logger.py |  |
| `stackops.paths` | `api` | `python-api-candidate` | `medium` | 1 | 7 | - | src/stackops/paths.py |  |
| `stackops.profile` | `package` | `package-marker` | `high` | 3 | 6 | - | src/stackops/profile/__init__.py |  |
| `stackops.profile.create_helper` | `api` | `python-api` | `high` | 4 | 89 | api-doc, funcs:4 | src/stackops/profile/create_helper.py |  |
| `stackops.profile.create_links` | `api-or-script` | `manual-review` | `medium` | 6 | 387 | __main__, classes:1, funcs:13 | src/stackops/profile/create_links.py |  |
| `stackops.profile.create_links_export` | `api-or-script` | `manual-review` | `medium` | 3 | 74 | typer, funcs:2 | src/stackops/profile/create_links_export.py |  |
| `stackops.profile.create_shell_profile` | `api-or-script` | `manual-review` | `medium` | 4 | 167 | __main__, funcs:5 | src/stackops/profile/create_shell_profile.py |  |
| `stackops.profile.dotfiles_collect_plan` | `api` | `python-api-candidate` | `medium` | 3 | 203 | classes:1, funcs:9 | src/stackops/profile/dotfiles_collect_plan.py |  |
| `stackops.profile.dotfiles_constants` | `api` | `python-api-candidate` | `medium` | 22 | 13 | - | src/stackops/profile/dotfiles_constants.py |  |
| `stackops.profile.dotfiles_mapper` | `api` | `python-api` | `high` | 9 | 163 | api-doc, classes:1, funcs:12 | src/stackops/profile/dotfiles_mapper.py |  |
| `stackops.profile.linking` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/profile/linking/__init__.py |  |
| `stackops.profile.linking.conflict` | `api` | `python-api-candidate` | `medium` | 4 | 33 | - | src/stackops/profile/linking/conflict.py |  |
| `stackops.profile.linking.display` | `api` | `python-api-candidate` | `medium` | 3 | 119 | funcs:6 | src/stackops/profile/linking/display.py |  |
| `stackops.profile.linking.operations` | `api` | `python-api-candidate` | `medium` | 5 | 316 | classes:2, funcs:4 | src/stackops/profile/linking/operations.py |  |
| `stackops.profile.linking.options` | `api` | `python-api-candidate` | `medium` | 10 | 39 | - | src/stackops/profile/linking/options.py |  |
| `stackops.profile.migration_until_2028_01_bash_zsh_hook` | `api` | `python-api-candidate` | `medium` | 3 | 47 | funcs:1 | src/stackops/profile/migration_until_2028_01_bash_zsh_hook.py |  |
| `stackops.profile.shell_profile_source` | `api` | `python-api-candidate` | `medium` | 7 | 66 | classes:1, funcs:1 | src/stackops/profile/shell_profile_source.py |  |
| `stackops.scripts` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/scripts/__init__.py |  |
| `stackops.scripts.linux` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/scripts/linux/__init__.py |  |
| `stackops.scripts.nu` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/scripts/nu/__init__.py |  |
| `stackops.scripts.python` | `package` | `package-marker` | `high` | 1 | 0 | - | src/stackops/scripts/python/__init__.py |  |
| `stackops.scripts.python.agents` | `cli` | `cli-entrypoint` | `high` | 1 | 959 | entry:agents, typer, typer-app, cli-registration, get_app, main, __main__, classes:1, funcs:21 | src/stackops/scripts/python/agents.py |  |
| `stackops.scripts.python.agents_browser` | `cli` | `cli-module` | `high` | 1 | 696 | typer, typer-app, cli-registration, get_app, funcs:12 | src/stackops/scripts/python/agents_browser.py |  |
| `stackops.scripts.python.agents_computer` | `cli` | `cli-module` | `high` | 1 | 87 | typer, typer-app, cli-registration, get_app, funcs:3 | src/stackops/scripts/python/agents_computer.py |  |
| `stackops.scripts.python.agents_config_files` | `cli` | `cli-module` | `high` | 1 | 59 | typer, typer-app, cli-registration, get_app, funcs:4 | src/stackops/scripts/python/agents_config_files.py |  |
| `stackops.scripts.python.agents_depoison` | `cli` | `cli-module` | `high` | 1 | 189 | typer, funcs:2 | src/stackops/scripts/python/agents_depoison.py |  |
| `stackops.scripts.python.agents_followup` | `cli` | `cli-module` | `high` | 1 | 126 | typer, classes:1, funcs:3 | src/stackops/scripts/python/agents_followup.py |  |
| `stackops.scripts.python.agents_iter` | `cli` | `cli-module` | `high` | 1 | 147 | typer, typer-app, cli-registration, get_app, funcs:5 | src/stackops/scripts/python/agents_iter.py |  |
| `stackops.scripts.python.agents_local` | `cli` | `cli-module` | `high` | 1 | 166 | typer, typer-app, cli-registration, get_app, funcs:3 | src/stackops/scripts/python/agents_local.py |  |
| `stackops.scripts.python.agents_local_vllm` | `cli` | `cli-module` | `high` | 1 | 109 | typer, funcs:3 | src/stackops/scripts/python/agents_local_vllm.py |  |
| `stackops.scripts.python.agents_second_brain` | `cli` | `cli-module` | `high` | 1 | 144 | typer, typer-app, cli-registration, get_app, funcs:6 | src/stackops/scripts/python/agents_second_brain.py |  |
| `stackops.scripts.python.agents_status` | `cli` | `cli-module` | `high` | 1 | 113 | typer, funcs:1 | src/stackops/scripts/python/agents_status.py |  |
| `stackops.scripts.python.agents_test_runtime` | `cli` | `cli-module` | `high` | 1 | 181 | typer, typer-app, get_app, classes:1, funcs:9 | src/stackops/scripts/python/agents_test_runtime.py |  |
| `stackops.scripts.python.agents_type_fix` | `cli` | `cli-module` | `high` | 1 | 105 | typer, typer-app, get_app, funcs:2 | src/stackops/scripts/python/agents_type_fix.py |  |
| `stackops.scripts.python.ai` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/scripts/python/ai/__init__.py |  |
| `stackops.scripts.python.ai.constants` | `cli-helper` | `cli-helper` | `medium` | 1 | 29 | - | src/stackops/scripts/python/ai/constants.py |  |
| `stackops.scripts.python.ai.initai` | `cli-helper` | `cli-helper` | `medium` | 1 | 137 | funcs:2 | src/stackops/scripts/python/ai/initai.py |  |
| `stackops.scripts.python.ai.initai_artifacts` | `cli-helper` | `cli-helper` | `medium` | 24 | 47 | funcs:2 | src/stackops/scripts/python/ai/initai_artifacts.py |  |
| `stackops.scripts.python.ai.initai_frameworks` | `cli-helper` | `cli-helper` | `medium` | 1 | 122 | funcs:1 | src/stackops/scripts/python/ai/initai_frameworks.py |  |
| `stackops.scripts.python.ai.initai_models` | `cli-helper` | `cli-helper` | `medium` | 28 | 31 | classes:3 | src/stackops/scripts/python/ai/initai_models.py |  |
| `stackops.scripts.python.ai.initai_rich_output` | `cli-helper` | `cli-helper` | `medium` | 1 | 141 | funcs:10 | src/stackops/scripts/python/ai/initai_rich_output.py |  |
| `stackops.scripts.python.ai.scripts` | `package` | `package-marker` | `high` | 5 | 5 | - | src/stackops/scripts/python/ai/scripts/__init__.py |  |
| `stackops.scripts.python.ai.scripts.constants` | `cli-helper` | `cli-helper` | `medium` | 10 | 18 | - | src/stackops/scripts/python/ai/scripts/constants.py |  |
| `stackops.scripts.python.ai.scripts.dashboard` | `cli-helper` | `cli-helper` | `medium` | 1 | 259 | funcs:6 | src/stackops/scripts/python/ai/scripts/dashboard.py |  |
| `stackops.scripts.python.ai.scripts.lint_and_type_check` | `cli-helper` | `cli-helper` | `medium` | 0 | 436 | main, __main__, funcs:10 | src/stackops/scripts/python/ai/scripts/lint_and_type_check.py |  |
| `stackops.scripts.python.ai.scripts.models` | `cli-helper` | `cli-helper` | `medium` | 3 | 196 | __all__, classes:3 | src/stackops/scripts/python/ai/scripts/models.py |  |
| `stackops.scripts.python.ai.scripts.models_config` | `cli-helper` | `cli-helper` | `medium` | 3 | 349 | funcs:16 | src/stackops/scripts/python/ai/scripts/models_config.py |  |
| `stackops.scripts.python.ai.scripts.models_core` | `cli-helper` | `cli-helper` | `medium` | 7 | 38 | classes:2 | src/stackops/scripts/python/ai/scripts/models_core.py |  |
| `stackops.scripts.python.ai.scripts.models_diagnostics` | `cli-helper` | `cli-helper` | `medium` | 1 | 213 | classes:2, funcs:8 | src/stackops/scripts/python/ai/scripts/models_diagnostics.py |  |
| `stackops.scripts.python.ai.scripts.models_json` | `cli-helper` | `cli-helper` | `medium` | 2 | 92 | classes:1, funcs:5 | src/stackops/scripts/python/ai/scripts/models_json.py |  |
| `stackops.scripts.python.ai.scripts.models_reports` | `cli-helper` | `cli-helper` | `medium` | 2 | 129 | funcs:10 | src/stackops/scripts/python/ai/scripts/models_reports.py |  |
| `stackops.scripts.python.ai.scripts.paths` | `cli-helper` | `cli-helper` | `medium` | 3 | 17 | - | src/stackops/scripts/python/ai/scripts/paths.py |  |
| `stackops.scripts.python.ai.scripts.report_schema` | `cli-helper` | `cli-helper` | `medium` | 2 | 31 | classes:2 | src/stackops/scripts/python/ai/scripts/report_schema.py |  |
| `stackops.scripts.python.ai.scripts.run_reports` | `cli-helper` | `cli-helper` | `medium` | 1 | 162 | classes:8, funcs:1 | src/stackops/scripts/python/ai/scripts/run_reports.py |  |
| `stackops.scripts.python.ai.scripts.tool_versions` | `cli-helper` | `cli-helper` | `medium` | 2 | 174 | classes:3, funcs:5 | src/stackops/scripts/python/ai/scripts/tool_versions.py |  |
| `stackops.scripts.python.ai.solutions` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/scripts/python/ai/solutions/__init__.py |  |
| `stackops.scripts.python.ai.solutions.antigravity` | `package` | `package-marker` | `high` | 1 | 0 | - | src/stackops/scripts/python/ai/solutions/antigravity/__init__.py |  |
| `stackops.scripts.python.ai.solutions.antigravity.antigravity` | `cli-helper` | `cli-helper` | `medium` | 1 | 39 | funcs:2 | src/stackops/scripts/python/ai/solutions/antigravity/antigravity.py |  |
| `stackops.scripts.python.ai.solutions.auggie` | `package` | `package-marker` | `high` | 1 | 0 | - | src/stackops/scripts/python/ai/solutions/auggie/__init__.py |  |
| `stackops.scripts.python.ai.solutions.auggie.auggie` | `cli-helper` | `cli-helper` | `medium` | 1 | 20 | funcs:1 | src/stackops/scripts/python/ai/solutions/auggie/auggie.py |  |
| `stackops.scripts.python.ai.solutions.claude.claude` | `cli-helper` | `cli-helper` | `medium` | 1 | 148 | funcs:5 | src/stackops/scripts/python/ai/solutions/claude/claude.py |  |
| `stackops.scripts.python.ai.solutions.cline.cline` | `cli-helper` | `cli-helper` | `medium` | 1 | 20 | funcs:1 | src/stackops/scripts/python/ai/solutions/cline/cline.py |  |
| `stackops.scripts.python.ai.solutions.codex` | `package` | `package-marker` | `high` | 1 | 1 | - | src/stackops/scripts/python/ai/solutions/codex/__init__.py |  |
| `stackops.scripts.python.ai.solutions.codex.codex` | `cli-helper` | `cli-helper` | `medium` | 1 | 41 | funcs:3 | src/stackops/scripts/python/ai/solutions/codex/codex.py |  |
| `stackops.scripts.python.ai.solutions.copilot` | `package` | `package-marker` | `high` | 2 | 0 | - | src/stackops/scripts/python/ai/solutions/copilot/__init__.py |  |
| `stackops.scripts.python.ai.solutions.copilot.agents` | `package` | `package-marker` | `high` | 0 | 3 | - | src/stackops/scripts/python/ai/solutions/copilot/agents/__init__.py |  |
| `stackops.scripts.python.ai.solutions.copilot.github_copilot` | `cli-helper` | `cli-helper` | `medium` | 1 | 81 | funcs:1 | src/stackops/scripts/python/ai/solutions/copilot/github_copilot.py |  |
| `stackops.scripts.python.ai.solutions.copilot.instructions.archive` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/scripts/python/ai/solutions/copilot/instructions/archive/__init__.py |  |
| `stackops.scripts.python.ai.solutions.copilot.instructions.python` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/scripts/python/ai/solutions/copilot/instructions/python/__init__.py |  |
| `stackops.scripts.python.ai.solutions.copilot.prompts` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/scripts/python/ai/solutions/copilot/prompts/__init__.py |  |
| `stackops.scripts.python.ai.solutions.cortex.cortex` | `cli-helper` | `cli-helper` | `medium` | 1 | 34 | funcs:1 | src/stackops/scripts/python/ai/solutions/cortex/cortex.py |  |
| `stackops.scripts.python.ai.solutions.crush` | `package` | `package-marker` | `high` | 1 | 2 | - | src/stackops/scripts/python/ai/solutions/crush/__init__.py |  |
| `stackops.scripts.python.ai.solutions.crush.crush` | `cli-helper` | `cli-helper` | `medium` | 1 | 93 | funcs:3 | src/stackops/scripts/python/ai/solutions/crush/crush.py |  |
| `stackops.scripts.python.ai.solutions.cursor.cursors` | `cli-helper` | `cli-helper` | `medium` | 1 | 21 | funcs:1 | src/stackops/scripts/python/ai/solutions/cursor/cursors.py |  |
| `stackops.scripts.python.ai.solutions.deepseek` | `package` | `package-marker` | `high` | 1 | 0 | - | src/stackops/scripts/python/ai/solutions/deepseek/__init__.py |  |
| `stackops.scripts.python.ai.solutions.deepseek.deepseek` | `cli-helper` | `cli-helper` | `medium` | 1 | 30 | funcs:1 | src/stackops/scripts/python/ai/solutions/deepseek/deepseek.py |  |
| `stackops.scripts.python.ai.solutions.droid` | `package` | `package-marker` | `high` | 1 | 0 | - | src/stackops/scripts/python/ai/solutions/droid/__init__.py |  |
| `stackops.scripts.python.ai.solutions.droid.droid` | `cli-helper` | `cli-helper` | `medium` | 1 | 50 | funcs:1 | src/stackops/scripts/python/ai/solutions/droid/droid.py |  |
| `stackops.scripts.python.ai.solutions.forge` | `package` | `package-marker` | `high` | 1 | 0 | - | src/stackops/scripts/python/ai/solutions/forge/__init__.py |  |
| `stackops.scripts.python.ai.solutions.forge.forge` | `cli-helper` | `cli-helper` | `medium` | 1 | 54 | funcs:4 | src/stackops/scripts/python/ai/solutions/forge/forge.py |  |
| `stackops.scripts.python.ai.solutions.kilocode` | `package` | `package-marker` | `high` | 2 | 1 | - | src/stackops/scripts/python/ai/solutions/kilocode/__init__.py |  |
| `stackops.scripts.python.ai.solutions.kilocode.kilocode` | `cli-helper` | `cli-helper` | `medium` | 1 | 100 | funcs:4 | src/stackops/scripts/python/ai/solutions/kilocode/kilocode.py |  |
| `stackops.scripts.python.ai.solutions.maki` | `package` | `package-marker` | `high` | 1 | 0 | - | src/stackops/scripts/python/ai/solutions/maki/__init__.py |  |
| `stackops.scripts.python.ai.solutions.maki.maki` | `cli-helper` | `cli-helper` | `medium` | 1 | 31 | funcs:1 | src/stackops/scripts/python/ai/solutions/maki/maki.py |  |
| `stackops.scripts.python.ai.solutions.muse` | `package` | `package-marker` | `high` | 1 | 0 | - | src/stackops/scripts/python/ai/solutions/muse/__init__.py |  |
| `stackops.scripts.python.ai.solutions.muse.muse` | `cli-helper` | `cli-helper` | `medium` | 1 | 19 | funcs:1 | src/stackops/scripts/python/ai/solutions/muse/muse.py |  |
| `stackops.scripts.python.ai.solutions.omp` | `package` | `package-marker` | `high` | 1 | 0 | - | src/stackops/scripts/python/ai/solutions/omp/__init__.py |  |
| `stackops.scripts.python.ai.solutions.omp.constants` | `cli-helper` | `cli-helper` | `medium` | 1 | 19 | - | src/stackops/scripts/python/ai/solutions/omp/constants.py |  |
| `stackops.scripts.python.ai.solutions.omp.omp` | `cli-helper` | `cli-helper` | `medium` | 1 | 68 | funcs:1 | src/stackops/scripts/python/ai/solutions/omp/omp.py |  |
| `stackops.scripts.python.ai.solutions.opencode` | `package` | `package-marker` | `high` | 2 | 1 | - | src/stackops/scripts/python/ai/solutions/opencode/__init__.py |  |
| `stackops.scripts.python.ai.solutions.opencode.opencode` | `cli-helper` | `cli-helper` | `medium` | 1 | 57 | funcs:1 | src/stackops/scripts/python/ai/solutions/opencode/opencode.py |  |
| `stackops.scripts.python.ai.solutions.opencode.openrouter_config` | `cli-helper` | `cli-helper` | `medium` | 2 | 37 | funcs:2 | src/stackops/scripts/python/ai/solutions/opencode/openrouter_config.py |  |
| `stackops.scripts.python.ai.solutions.oz` | `package` | `package-marker` | `high` | 1 | 0 | - | src/stackops/scripts/python/ai/solutions/oz/__init__.py |  |
| `stackops.scripts.python.ai.solutions.oz.oz` | `cli-helper` | `cli-helper` | `medium` | 1 | 20 | funcs:1 | src/stackops/scripts/python/ai/solutions/oz/oz.py |  |
| `stackops.scripts.python.ai.solutions.pi` | `package` | `package-marker` | `high` | 1 | 0 | - | src/stackops/scripts/python/ai/solutions/pi/__init__.py |  |
| `stackops.scripts.python.ai.solutions.pi.constants` | `cli-helper` | `cli-helper` | `medium` | 1 | 30 | - | src/stackops/scripts/python/ai/solutions/pi/constants.py |  |
| `stackops.scripts.python.ai.solutions.pi.pi` | `cli-helper` | `cli-helper` | `medium` | 1 | 87 | funcs:3 | src/stackops/scripts/python/ai/solutions/pi/pi.py |  |
| `stackops.scripts.python.ai.solutions.prime_agent` | `package` | `package-marker` | `high` | 1 | 0 | - | src/stackops/scripts/python/ai/solutions/prime_agent/__init__.py |  |
| `stackops.scripts.python.ai.solutions.prime_agent.prime_agent` | `cli-helper` | `cli-helper` | `medium` | 1 | 18 | funcs:1 | src/stackops/scripts/python/ai/solutions/prime_agent/prime_agent.py |  |
| `stackops.scripts.python.ai.solutions.q` | `package` | `package-marker` | `high` | 1 | 0 | - | src/stackops/scripts/python/ai/solutions/q/__init__.py |  |
| `stackops.scripts.python.ai.solutions.q.amazon_q` | `cli-helper` | `cli-helper` | `medium` | 1 | 20 | funcs:1 | src/stackops/scripts/python/ai/solutions/q/amazon_q.py |  |
| `stackops.scripts.python.ai.solutions.qwen_code` | `package` | `package-marker` | `high` | 1 | 0 | - | src/stackops/scripts/python/ai/solutions/qwen_code/__init__.py |  |
| `stackops.scripts.python.ai.solutions.qwen_code.qwen_code` | `cli-helper` | `cli-helper` | `medium` | 1 | 66 | funcs:2 | src/stackops/scripts/python/ai/solutions/qwen_code/qwen_code.py |  |
| `stackops.scripts.python.ai.solutions.warp` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/scripts/python/ai/solutions/warp/__init__.py |  |
| `stackops.scripts.python.ai.solutions.warp.warp` | `cli-helper` | `cli-helper` | `medium` | 0 | 12 | funcs:1 | src/stackops/scripts/python/ai/solutions/warp/warp.py |  |
| `stackops.scripts.python.ai.utils` | `package` | `package-marker` | `high` | 2 | 0 | - | src/stackops/scripts/python/ai/utils/__init__.py |  |
| `stackops.scripts.python.ai.utils.generate_files` | `cli` | `cli-module` | `high` | 0 | 113 | typer, typer-app, cli-registration, __main__, funcs:1 | src/stackops/scripts/python/ai/utils/generate_files.py |  |
| `stackops.scripts.python.ai.utils.generate_files_content` | `cli-helper` | `cli-helper` | `medium` | 1 | 104 | funcs:5 | src/stackops/scripts/python/ai/utils/generate_files_content.py |  |
| `stackops.scripts.python.ai.utils.generate_files_utils` | `cli-helper` | `cli-helper` | `medium` | 1 | 123 | funcs:8 | src/stackops/scripts/python/ai/utils/generate_files_utils.py |  |
| `stackops.scripts.python.ai.utils.generic` | `cli-helper` | `cli-helper` | `medium` | 2 | 91 | funcs:3 | src/stackops/scripts/python/ai/utils/generic.py |  |
| `stackops.scripts.python.ai.utils.shared` | `cli-helper` | `cli-helper` | `medium` | 23 | 15 | funcs:1 | src/stackops/scripts/python/ai/utils/shared.py |  |
| `stackops.scripts.python.ai.utils.vscode_tasks` | `cli-helper` | `cli-helper` | `medium` | 1 | 56 | funcs:1 | src/stackops/scripts/python/ai/utils/vscode_tasks.py |  |
| `stackops.scripts.python.cloud` | `cli` | `cli-entrypoint` | `high` | 1 | 179 | entry:cloud, typer, typer-app, cli-registration, get_app, main, __main__, funcs:6 | src/stackops/scripts/python/cloud.py |  |
| `stackops.scripts.python.devops` | `cli` | `cli-entrypoint` | `high` | 2 | 176 | entry:devops, typer, typer-app, cli-registration, get_app, main, __main__, classes:1, funcs:14 | src/stackops/scripts/python/devops.py |  |
| `stackops.scripts.python.enums` | `cli-helper` | `cli-helper` | `medium` | 3 | 90 | - | src/stackops/scripts/python/enums.py |  |
| `stackops.scripts.python.fire_jobs` | `cli` | `cli-entrypoint` | `high` | 1 | 126 | entry:fire, typer, typer-app, cli-registration, get_app, main, __main__, funcs:7 | src/stackops/scripts/python/fire_jobs.py |  |
| `stackops.scripts.python.ftpx` | `cli` | `cli-module` | `high` | 1 | 87 | typer, typer-app, cli-registration, main, __main__, funcs:4 | src/stackops/scripts/python/ftpx.py |  |
| `stackops.scripts.python.graph` | `package` | `package-marker` | `high` | 3 | 1 | - | src/stackops/scripts/python/graph/__init__.py |  |
| `stackops.scripts.python.graph.cli_graph_apps` | `cli-helper` | `cli-helper` | `medium` | 2 | 285 | classes:1, funcs:6 | src/stackops/scripts/python/graph/cli_graph_apps.py |  |
| `stackops.scripts.python.graph.cli_graph_eval` | `cli-helper` | `cli-helper` | `medium` | 3 | 47 | funcs:2 | src/stackops/scripts/python/graph/cli_graph_eval.py |  |
| `stackops.scripts.python.graph.cli_graph_managed_files` | `cli-helper` | `cli-helper` | `medium` | 1 | 58 | funcs:1 | src/stackops/scripts/python/graph/cli_graph_managed_files.py |  |
| `stackops.scripts.python.graph.cli_graph_node_utils` | `cli-helper` | `cli-helper` | `medium` | 1 | 55 | funcs:6 | src/stackops/scripts/python/graph/cli_graph_node_utils.py |  |
| `stackops.scripts.python.graph.cli_graph_nodes` | `cli-helper` | `cli-helper` | `medium` | 1 | 224 | funcs:5 | src/stackops/scripts/python/graph/cli_graph_nodes.py |  |
| `stackops.scripts.python.graph.cli_graph_policy` | `cli-helper` | `cli-helper` | `medium` | 1 | 164 | funcs:4 | src/stackops/scripts/python/graph/cli_graph_policy.py |  |
| `stackops.scripts.python.graph.cli_graph_registration` | `cli-helper` | `cli-helper` | `medium` | 2 | 91 | funcs:3 | src/stackops/scripts/python/graph/cli_graph_registration.py |  |
| `stackops.scripts.python.graph.cli_graph_resolver` | `cli-helper` | `cli-helper` | `medium` | 6 | 218 | funcs:12 | src/stackops/scripts/python/graph/cli_graph_resolver.py |  |
| `stackops.scripts.python.graph.cli_graph_shared` | `cli-helper` | `cli-helper` | `medium` | 12 | 91 | classes:7 | src/stackops/scripts/python/graph/cli_graph_shared.py |  |
| `stackops.scripts.python.graph.cli_graph_signature` | `cli-helper` | `cli-helper` | `medium` | 1 | 222 | funcs:10 | src/stackops/scripts/python/graph/cli_graph_signature.py |  |
| `stackops.scripts.python.graph.cli_graph_targets` | `cli-helper` | `cli-helper` | `medium` | 1 | 159 | funcs:8 | src/stackops/scripts/python/graph/cli_graph_targets.py |  |
| `stackops.scripts.python.graph.cli_graph_tree` | `cli-helper` | `cli-helper` | `medium` | 1 | 78 | funcs:1 | src/stackops/scripts/python/graph/cli_graph_tree.py |  |
| `stackops.scripts.python.graph.cli_graph_values` | `cli-helper` | `cli-helper` | `medium` | 2 | 236 | funcs:4 | src/stackops/scripts/python/graph/cli_graph_values.py |  |
| `stackops.scripts.python.graph.generate_cli_graph` | `cli-helper` | `cli-helper` | `medium` | 1 | 34 | main, __main__, funcs:1 | src/stackops/scripts/python/graph/generate_cli_graph.py |  |
| `stackops.scripts.python.graph.python_api_graph` | `cli-helper` | `cli-helper` | `medium` | 1 | 518 | classes:1, funcs:28 | src/stackops/scripts/python/graph/python_api_graph.py |  |
| `stackops.scripts.python.graph.visualize` | `package` | `package-marker` | `high` | 1 | 0 | - | src/stackops/scripts/python/graph/visualize/__init__.py |  |
| `stackops.scripts.python.graph.visualize.cli_graph_app` | `cli` | `cli-module` | `high` | 4 | 190 | typer, typer-app, cli-registration, get_app, main, __main__, funcs:9 | src/stackops/scripts/python/graph/visualize/cli_graph_app.py |  |
| `stackops.scripts.python.graph.visualize.cli_graph_execute` | `cli` | `cli-module` | `high` | 1 | 208 | typer, typer-app, cli-registration, funcs:6 | src/stackops/scripts/python/graph/visualize/cli_graph_execute.py |  |
| `stackops.scripts.python.graph.visualize.cli_graph_search` | `cli-helper` | `cli-helper` | `medium` | 2 | 434 | classes:1, funcs:31 | src/stackops/scripts/python/graph/visualize/cli_graph_search.py |  |
| `stackops.scripts.python.graph.visualize.cli_graph_typer_app` | `cli` | `cli-module` | `high` | 0 | 78 | typer, typer-app, cli-registration, funcs:1 | src/stackops/scripts/python/graph/visualize/cli_graph_typer_app.py |  |
| `stackops.scripts.python.graph.visualize.dot_export` | `cli-helper` | `cli-helper` | `medium` | 2 | 81 | funcs:5 | src/stackops/scripts/python/graph/visualize/dot_export.py |  |
| `stackops.scripts.python.graph.visualize.graph_data` | `cli-helper` | `cli-helper` | `medium` | 3 | 145 | classes:1, funcs:8 | src/stackops/scripts/python/graph/visualize/graph_data.py |  |
| `stackops.scripts.python.graph.visualize.graph_paths` | `cli-helper` | `cli-helper` | `medium` | 4 | 8 | - | src/stackops/scripts/python/graph/visualize/graph_paths.py |  |
| `stackops.scripts.python.graph.visualize.helpers_navigator` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/scripts/python/graph/visualize/helpers_navigator/__init__.py |  |
| `stackops.scripts.python.graph.visualize.helpers_navigator.cli_graph_loader` | `cli-helper` | `cli-helper` | `medium` | 1 | 234 | classes:1, funcs:14 | src/stackops/scripts/python/graph/visualize/helpers_navigator/cli_graph_loader.py |  |
| `stackops.scripts.python.graph.visualize.helpers_navigator.command_builder` | `cli-helper` | `cli-helper` | `medium` | 1 | 182 | classes:1 | src/stackops/scripts/python/graph/visualize/helpers_navigator/command_builder.py |  |
| `stackops.scripts.python.graph.visualize.helpers_navigator.command_detail` | `cli-helper` | `cli-helper` | `medium` | 1 | 152 | classes:1 | src/stackops/scripts/python/graph/visualize/helpers_navigator/command_detail.py |  |
| `stackops.scripts.python.graph.visualize.helpers_navigator.command_tree` | `cli-helper` | `cli-helper` | `medium` | 1 | 50 | classes:1 | src/stackops/scripts/python/graph/visualize/helpers_navigator/command_tree.py |  |
| `stackops.scripts.python.graph.visualize.helpers_navigator.data_models` | `cli-helper` | `cli-helper` | `medium` | 5 | 34 | classes:2 | src/stackops/scripts/python/graph/visualize/helpers_navigator/data_models.py |  |
| `stackops.scripts.python.graph.visualize.helpers_navigator.devops_navigator` | `cli-helper` | `cli-helper` | `medium` | 1 | 20 | main, __main__, funcs:1 | src/stackops/scripts/python/graph/visualize/helpers_navigator/devops_navigator.py |  |
| `stackops.scripts.python.graph.visualize.helpers_navigator.main_app` | `cli-helper` | `cli-helper` | `medium` | 1 | 275 | classes:1 | src/stackops/scripts/python/graph/visualize/helpers_navigator/main_app.py |  |
| `stackops.scripts.python.graph.visualize.helpers_navigator.search_bar` | `cli-helper` | `cli-helper` | `medium` | 1 | 18 | classes:1 | src/stackops/scripts/python/graph/visualize/helpers_navigator/search_bar.py |  |
| `stackops.scripts.python.graph.visualize.plotly_browser` | `cli-helper` | `cli-helper` | `medium` | 1 | 185 | classes:1, funcs:11 | src/stackops/scripts/python/graph/visualize/plotly_browser.py |  |
| `stackops.scripts.python.graph.visualize.plotly_views` | `cli` | `cli-module` | `high` | 3 | 205 | typer, __main__, funcs:2 | src/stackops/scripts/python/graph/visualize/plotly_views.py |  |
| `stackops.scripts.python.graph.visualize.python_api_graph_app` | `cli` | `cli-module` | `high` | 1 | 177 | typer, typer-app, cli-registration, get_app, main, __main__, funcs:10 | src/stackops/scripts/python/graph/visualize/python_api_graph_app.py |  |
| `stackops.scripts.python.graph.visualize.python_api_graph_search` | `cli-helper` | `cli-helper` | `medium` | 1 | 231 | classes:1, funcs:15 | src/stackops/scripts/python/graph/visualize/python_api_graph_search.py |  |
| `stackops.scripts.python.graph.visualize.rich_tree` | `cli-helper` | `cli-helper` | `medium` | 2 | 80 | funcs:4 | src/stackops/scripts/python/graph/visualize/rich_tree.py |  |
| `stackops.scripts.python.helpers` | `package` | `package-marker` | `high` | 1 | 0 | - | src/stackops/scripts/python/helpers/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents` | `package` | `package-marker` | `high` | 2 | 0 | - | src/stackops/scripts/python/helpers/helpers_agents/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agentic_frameworks` | `package` | `package-marker` | `high` | 1 | 1 | - | src/stackops/scripts/python/helpers/helpers_agents/agentic_frameworks/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_codex` | `cli-helper` | `cli-helper` | `medium` | 1 | 40 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agentic_frameworks/fire_codex.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_copilot` | `cli-helper` | `cli-helper` | `medium` | 1 | 32 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agentic_frameworks/fire_copilot.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_cortex` | `cli-helper` | `cli-helper` | `medium` | 1 | 31 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agentic_frameworks/fire_cortex.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_crush` | `cli-helper` | `cli-helper` | `medium` | 1 | 64 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agentic_frameworks/fire_crush.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_cursor_agents` | `cli-helper` | `cli-helper` | `medium` | 0 | 18 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agentic_frameworks/fire_cursor_agents.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_deepseek` | `cli-helper` | `cli-helper` | `medium` | 1 | 32 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agentic_frameworks/fire_deepseek.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_maki` | `cli-helper` | `cli-helper` | `medium` | 1 | 29 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agentic_frameworks/fire_maki.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_pi` | `cli-helper` | `cli-helper` | `medium` | 1 | 44 | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agentic_frameworks/fire_pi.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_prime_agent` | `cli-helper` | `cli-helper` | `medium` | 1 | 33 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agentic_frameworks/fire_prime_agent.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_qwen` | `cli-helper` | `cli-helper` | `medium` | 0 | 27 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agentic_frameworks/fire_qwen.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_agent_ops_cache` | `cli-helper` | `cli-helper` | `medium` | 4 | 165 | classes:1, funcs:5 | src/stackops/scripts/python/helpers/helpers_agents/agents_agent_ops_cache.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_ask_impl` | `cli-helper` | `cli-helper` | `medium` | 1 | 136 | funcs:10 | src/stackops/scripts/python/helpers/helpers_agents/agents_ask_impl.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_app_window_models` | `cli-helper` | `cli-helper` | `medium` | 8 | 24 | classes:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_app_window_models.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_app_windows` | `cli-helper` | `cli-helper` | `medium` | 2 | 118 | funcs:5 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_app_windows.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_apple_events_windows` | `cli-helper` | `cli-helper` | `medium` | 1 | 103 | classes:3, funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_apple_events_windows.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_batch` | `cli-helper` | `cli-helper` | `medium` | 1 | 75 | classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_batch.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_bidi_windows` | `cli-helper` | `cli-helper` | `medium` | 1 | 103 | classes:3, funcs:7 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_bidi_windows.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_cdp_windows` | `cli-helper` | `cli-helper` | `medium` | 1 | 126 | classes:3, funcs:6 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_cdp_windows.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_close` | `cli-helper` | `cli-helper` | `medium` | 1 | 140 | classes:5, funcs:9 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_close.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_constants` | `cli-helper` | `cli-helper` | `medium` | 48 | 146 | - | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_constants.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_detached_launch` | `cli-helper` | `cli-helper` | `medium` | 2 | 121 | funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_detached_launch.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_detached_processes` | `cli-helper` | `cli-helper` | `medium` | 9 | 219 | classes:1, funcs:17 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_detached_processes.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_endpoint_rpc` | `cli-helper` | `cli-helper` | `medium` | 2 | 16 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_endpoint_rpc.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_guides` | `cli-helper` | `cli-helper` | `medium` | 1 | 70 | classes:1, funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_guides.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_hosts` | `cli-helper` | `cli-helper` | `medium` | 3 | 94 | funcs:5 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_hosts.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_impl` | `cli-helper` | `cli-helper` | `medium` | 1 | 159 | classes:2, funcs:8 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_impl.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_json` | `cli-helper` | `cli-helper` | `medium` | 1 | 18 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_json.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_launch` | `cli-helper` | `cli-helper` | `medium` | 1 | 60 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_launch.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_details` | `cli-helper` | `cli-helper` | `medium` | 2 | 41 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_launch_details.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_identity` | `cli-helper` | `cli-helper` | `medium` | 4 | 26 | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_launch_identity.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_lock` | `cli-helper` | `cli-helper` | `medium` | 4 | 33 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_launch_lock.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_models` | `cli-helper` | `cli-helper` | `medium` | 14 | 94 | classes:4, funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_launch_models.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_records` | `cli-helper` | `cli-helper` | `medium` | 6 | 189 | classes:4, funcs:5 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_launch_records.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_runtime` | `cli-helper` | `cli-helper` | `medium` | 8 | 184 | funcs:12 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_launch_runtime.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_lifecycle` | `cli-helper` | `cli-helper` | `medium` | 2 | 50 | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_lifecycle.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_multiplexed_launch` | `cli-helper` | `cli-helper` | `medium` | 2 | 111 | funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_multiplexed_launch.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_native_profiles` | `cli-helper` | `cli-helper` | `medium` | 3 | 122 | classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_native_profiles.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_native_replication` | `cli-helper` | `cli-helper` | `medium` | 1 | 73 | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_native_replication.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_native_selection` | `cli-helper` | `cli-helper` | `medium` | 1 | 34 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_native_selection.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_process_scan` | `cli-helper` | `cli-helper` | `medium` | 3 | 78 | classes:1, funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_process_scan.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_profile_filesystem` | `cli-helper` | `cli-helper` | `medium` | 3 | 112 | funcs:7 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_profile_filesystem.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_profile_inventory` | `cli-helper` | `cli-helper` | `medium` | 2 | 151 | classes:1, funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_profile_inventory.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_profile_inventory_output` | `cli-helper` | `cli-helper` | `medium` | 1 | 113 | funcs:5 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_profile_inventory_output.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_profile_listing` | `cli-helper` | `cli-helper` | `medium` | 5 | 23 | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_profile_listing.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_profile_sign_in` | `cli-helper` | `cli-helper` | `medium` | 2 | 178 | classes:4, funcs:7 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_profile_sign_in.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_profiles` | `cli-helper` | `cli-helper` | `medium` | 3 | 241 | classes:2, funcs:9 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_profiles.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_resolution` | `cli-helper` | `cli-helper` | `medium` | 3 | 92 | funcs:9 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_resolution.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_reuse` | `cli-helper` | `cli-helper` | `medium` | 1 | 128 | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_reuse.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_rich_output` | `cli-helper` | `cli-helper` | `medium` | 1 | 108 | funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_rich_output.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_status` | `cli-helper` | `cli-helper` | `medium` | 2 | 149 | classes:2, funcs:6 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_status.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_tabs` | `cli-helper` | `cli-helper` | `medium` | 1 | 87 | classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_tabs.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_temporary_profiles` | `cli-helper` | `cli-helper` | `medium` | 1 | 70 | funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_temporary_profiles.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_tmux_common` | `cli-helper` | `cli-helper` | `medium` | 1 | 34 | funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_tmux_common.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_tmux_host` | `cli-helper` | `cli-helper` | `medium` | 1 | 91 | funcs:6 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_tmux_host.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_tuios_host` | `cli-helper` | `cli-helper` | `medium` | 1 | 78 | funcs:6 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_tuios_host.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_windows_desktop` | `cli-helper` | `cli-helper` | `medium` | 1 | 90 | funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_windows_desktop.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_zellij_host` | `cli-helper` | `cli-helper` | `medium` | 1 | 64 | funcs:5 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_zellij_host.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_computer_constants` | `cli-helper` | `cli-helper` | `medium` | 2 | 8 | - | src/stackops/scripts/python/helpers/helpers_agents/agents_computer_constants.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_computer_status` | `cli-helper` | `cli-helper` | `medium` | 1 | 132 | classes:3, funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_computer_status.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_create_artifacts` | `cli-helper` | `cli-helper` | `medium` | 2 | 124 | classes:4, funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_create_artifacts.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_create_inputs` | `cli-helper` | `cli-helper` | `medium` | 2 | 297 | classes:2, funcs:7 | src/stackops/scripts/python/helpers/helpers_agents/agents_create_inputs.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_create_replacement` | `cli-helper` | `cli-helper` | `medium` | 1 | 40 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_create_replacement.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.agy` | `cli-helper` | `cli-helper` | `medium` | 1 | 52 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/agy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.amazon_q` | `cli-helper` | `cli-helper` | `medium` | 1 | 48 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/amazon_q.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.auggie` | `cli-helper` | `cli-helper` | `medium` | 1 | 42 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/auggie.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.claude` | `cli-helper` | `cli-helper` | `medium` | 1 | 73 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/claude.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.cline` | `cli-helper` | `cli-helper` | `medium` | 1 | 71 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/cline.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.codex` | `cli-helper` | `cli-helper` | `medium` | 1 | 39 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/codex.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.codex_config` | `cli-helper` | `cli-helper` | `medium` | 2 | 82 | classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/codex_config.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.codex_context` | `cli-helper` | `cli-helper` | `medium` | 1 | 69 | funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/codex_context.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.codex_plugin_cache` | `cli-helper` | `cli-helper` | `medium` | 1 | 79 | classes:1, funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/codex_plugin_cache.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.codex_plugins` | `cli-helper` | `cli-helper` | `medium` | 2 | 69 | classes:1, funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/codex_plugins.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.copilot` | `cli-helper` | `cli-helper` | `medium` | 1 | 71 | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/copilot.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.cortex` | `cli-helper` | `cli-helper` | `medium` | 1 | 73 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/cortex.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.crush` | `cli-helper` | `cli-helper` | `medium` | 1 | 58 | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/crush.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.cursor_agent` | `cli-helper` | `cli-helper` | `medium` | 1 | 69 | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/cursor_agent.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.deepseek` | `cli-helper` | `cli-helper` | `medium` | 1 | 69 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/deepseek.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.deepseek_cleanup` | `cli-helper` | `cli-helper` | `medium` | 1 | 37 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/deepseek_cleanup.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.deepseek_config` | `cli-helper` | `cli-helper` | `medium` | 3 | 104 | classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/deepseek_config.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.droid` | `cli-helper` | `cli-helper` | `medium` | 1 | 49 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/droid.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.forge` | `cli-helper` | `cli-helper` | `medium` | 1 | 36 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/forge.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.kilocode` | `cli-helper` | `cli-helper` | `medium` | 1 | 53 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/kilocode.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.maki` | `cli-helper` | `cli-helper` | `medium` | 1 | 77 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/maki.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.muse` | `cli-helper` | `cli-helper` | `medium` | 1 | 41 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/muse.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.omp` | `cli-helper` | `cli-helper` | `medium` | 1 | 26 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/omp.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.omp_config` | `cli-helper` | `cli-helper` | `medium` | 5 | 73 | funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/omp_config.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.omp_context` | `cli-helper` | `cli-helper` | `medium` | 1 | 107 | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/omp_context.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.omp_plugin_state` | `cli-helper` | `cli-helper` | `medium` | 3 | 151 | classes:1, funcs:7 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/omp_plugin_state.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.omp_plugins` | `cli-helper` | `cli-helper` | `medium` | 1 | 101 | funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/omp_plugins.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.opencode` | `cli-helper` | `cli-helper` | `medium` | 1 | 173 | funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/opencode.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.opencode_config` | `cli-helper` | `cli-helper` | `medium` | 2 | 70 | funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/opencode_config.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.oz` | `cli-helper` | `cli-helper` | `medium` | 1 | 42 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/oz.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.pi` | `cli-helper` | `cli-helper` | `medium` | 1 | 21 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/pi.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.pi_context` | `cli-helper` | `cli-helper` | `medium` | 1 | 94 | funcs:5 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/pi_context.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.pi_settings` | `cli-helper` | `cli-helper` | `medium` | 1 | 154 | funcs:7 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/pi_settings.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.prime_agent` | `cli-helper` | `cli-helper` | `medium` | 1 | 56 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/prime_agent.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.qwen` | `cli-helper` | `cli-helper` | `medium` | 1 | 49 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/agents/qwen.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_apply` | `cli-helper` | `cli-helper` | `medium` | 2 | 61 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/cleanup_apply.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_configuration` | `cli-helper` | `cli-helper` | `medium` | 2 | 113 | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/cleanup_configuration.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_documents` | `cli-helper` | `cli-helper` | `medium` | 1 | 116 | funcs:5 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/cleanup_documents.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_html` | `cli-helper` | `cli-helper` | `medium` | 1 | 102 | classes:4, funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/cleanup_html.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_interactive` | `cli` | `cli-module` | `high` | 5 | 110 | typer, classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/cleanup_interactive.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_models` | `cli-helper` | `cli-helper` | `medium` | 10 | 46 | classes:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/cleanup_models.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_output` | `cli-helper` | `cli-helper` | `medium` | 2 | 124 | funcs:5 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/cleanup_output.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_paths` | `cli-helper` | `cli-helper` | `medium` | 3 | 27 | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/cleanup_paths.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_plan` | `cli-helper` | `cli-helper` | `medium` | 2 | 67 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/cleanup_plan.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_resource_roots` | `cli-helper` | `cli-helper` | `medium` | 1 | 76 | funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/cleanup_resource_roots.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_resources` | `cli-helper` | `cli-helper` | `medium` | 2 | 90 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/cleanup_resources.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_scope` | `cli-helper` | `cli-helper` | `medium` | 6 | 3 | - | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/cleanup_scope.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_sizes` | `cli-helper` | `cli-helper` | `medium` | 2 | 32 | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/cleanup_sizes.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_workspace` | `cli-helper` | `cli-helper` | `medium` | 4 | 60 | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/cleanup_workspace.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.command` | `cli-helper` | `cli-helper` | `medium` | 3 | 96 | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/command.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.constants` | `cli-helper` | `cli-helper` | `medium` | 12 | 15 | - | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/constants.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.context_estimate` | `cli-helper` | `cli-helper` | `medium` | 2 | 150 | classes:1, funcs:5 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/context_estimate.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.extra_configuration` | `cli-helper` | `cli-helper` | `medium` | 1 | 31 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/extra_configuration.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.claude_plugins` | `cli-helper` | `cli-helper` | `medium` | 1 | 105 | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/hooks/claude_plugins.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.cline` | `cli-helper` | `cli-helper` | `medium` | 1 | 31 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/hooks/cline.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.codex_hooks` | `cli-helper` | `cli-helper` | `medium` | 1 | 130 | classes:1, funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/hooks/codex_hooks.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.codex_plugin_hooks` | `cli-helper` | `cli-helper` | `medium` | 1 | 103 | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/hooks/codex_plugin_hooks.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.discovery` | `cli-helper` | `cli-helper` | `medium` | 3 | 92 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/hooks/discovery.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.extended_constants` | `cli-helper` | `cli-helper` | `medium` | 2 | 6 | - | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/hooks/extended_constants.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.extension_sources` | `cli-helper` | `cli-helper` | `medium` | 3 | 42 | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/hooks/extension_sources.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.extensions` | `cli-helper` | `cli-helper` | `medium` | 2 | 110 | funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/hooks/extensions.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.json_inventory` | `cli-helper` | `cli-helper` | `medium` | 4 | 83 | funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/hooks/json_inventory.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.models` | `cli-helper` | `cli-helper` | `medium` | 24 | 53 | classes:5 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/hooks/models.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.omp_hooks` | `cli-helper` | `cli-helper` | `medium` | 1 | 63 | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/hooks/omp_hooks.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.paths` | `cli-helper` | `cli-helper` | `medium` | 23 | 60 | funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/hooks/paths.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.sources` | `cli-helper` | `cli-helper` | `medium` | 2 | 96 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/hooks/sources.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.html_report` | `cli-helper` | `cli-helper` | `medium` | 1 | 116 | classes:4, funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/html_report.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.mcp_servers` | `cli-helper` | `cli-helper` | `medium` | 1 | 25 | classes:1, funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/mcp_servers.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.models` | `cli-helper` | `cli-helper` | `medium` | 69 | 71 | classes:6 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/models.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.registry` | `cli-helper` | `cli-helper` | `medium` | 9 | 93 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/registry.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.resource_inventory` | `cli-helper` | `cli-helper` | `medium` | 2 | 23 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/resource_inventory.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.rich_output` | `cli-helper` | `cli-helper` | `medium` | 1 | 229 | funcs:10 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/rich_output.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.scanning` | `cli-helper` | `cli-helper` | `medium` | 22 | 223 | funcs:11 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/scanning.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.standard` | `cli-helper` | `cli-helper` | `medium` | 18 | 100 | classes:2, funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/standard.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.tui_cleanup` | `cli-helper` | `cli-helper` | `medium` | 2 | 84 | funcs:6 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/tui_cleanup.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.tui_cleanup_browser` | `cli-helper` | `cli-helper` | `medium` | 1 | 156 | classes:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/tui_cleanup_browser.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.tui_cleanup_review` | `cli-helper` | `cli-helper` | `medium` | 1 | 98 | classes:1, funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/tui_cleanup_review.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.tui_depoison` | `cli-helper` | `cli-helper` | `medium` | 1 | 196 | classes:1, funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/tui_depoison.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.tui_doctor` | `cli-helper` | `cli-helper` | `medium` | 1 | 108 | classes:1, funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/tui_doctor.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.tui_doctor_data` | `cli-helper` | `cli-helper` | `medium` | 1 | 60 | funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/tui_doctor_data.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.tui_doctor_widgets` | `cli-helper` | `cli-helper` | `medium` | 1 | 177 | classes:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/tui_doctor_widgets.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_doctor.tui_launch` | `cli` | `cli-module` | `high` | 2 | 67 | typer, funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_doctor/tui_launch.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_edit_source` | `cli-helper` | `cli-helper` | `medium` | 2 | 73 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_edit_source.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_impl` | `cli-helper` | `cli-helper` | `medium` | 3 | 255 | classes:1, funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_impl.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_iter_constants` | `cli-helper` | `cli-helper` | `medium` | 3 | 7 | - | src/stackops/scripts/python/helpers/helpers_agents/agents_iter_constants.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_iter_contract` | `cli-helper` | `cli-helper` | `medium` | 1 | 79 | funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_iter_contract.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_iter_herdr` | `cli-helper` | `cli-helper` | `medium` | 1 | 72 | classes:2, funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_iter_herdr.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_iter_herdr_protocol` | `cli-helper` | `cli-helper` | `medium` | 1 | 198 | classes:1, funcs:18 | src/stackops/scripts/python/helpers/helpers_agents/agents_iter_herdr_protocol.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_iter_json` | `cli` | `cli-module` | `high` | 1 | 35 | typer, funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_iter_json.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_iter_models` | `cli-helper` | `cli-helper` | `medium` | 12 | 147 | classes:11 | src/stackops/scripts/python/helpers/helpers_agents/agents_iter_models.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_iter_plan` | `cli-helper` | `cli-helper` | `medium` | 1 | 170 | funcs:9 | src/stackops/scripts/python/helpers/helpers_agents/agents_iter_plan.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_iter_records` | `cli-helper` | `cli-helper` | `medium` | 5 | 205 | classes:2, funcs:12 | src/stackops/scripts/python/helpers/helpers_agents/agents_iter_records.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_iter_render` | `cli-helper` | `cli-helper` | `medium` | 1 | 179 | funcs:12 | src/stackops/scripts/python/helpers/helpers_agents/agents_iter_render.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_iter_rich_output` | `cli-helper` | `cli-helper` | `medium` | 1 | 90 | funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_iter_rich_output.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_iter_selection` | `cli-helper` | `cli-helper` | `medium` | 1 | 155 | funcs:6 | src/stackops/scripts/python/helpers/helpers_agents/agents_iter_selection.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_iter_service` | `cli-helper` | `cli-helper` | `medium` | 3 | 137 | funcs:8 | src/stackops/scripts/python/helpers/helpers_agents/agents_iter_service.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_iter_workspace_records` | `cli-helper` | `cli-helper` | `medium` | 1 | 92 | classes:1, funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_iter_workspace_records.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_json` | `cli` | `cli-module` | `high` | 10 | 22 | typer, funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_json.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_local.catalog` | `cli-helper` | `cli-helper` | `medium` | 2 | 129 | classes:2, funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_local/catalog.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_local.catalog_downloads` | `cli-helper` | `cli-helper` | `medium` | 1 | 69 | classes:2, funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_local/catalog_downloads.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_local.catalog_report` | `cli-helper` | `cli-helper` | `medium` | 1 | 44 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_local/catalog_report.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_local.constants` | `cli-helper` | `cli-helper` | `medium` | 9 | 32 | - | src/stackops/scripts/python/helpers/helpers_agents/agents_local/constants.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_local.ollama` | `cli-helper` | `cli-helper` | `medium` | 2 | 141 | classes:3, funcs:5 | src/stackops/scripts/python/helpers/helpers_agents/agents_local/ollama.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_local.report` | `cli-helper` | `cli-helper` | `medium` | 1 | 86 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_local/report.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_local.server` | `cli-helper` | `cli-helper` | `medium` | 2 | 27 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_local/server.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_local.vllm` | `cli-helper` | `cli-helper` | `medium` | 2 | 140 | classes:3, funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_local/vllm.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_local.vllm_catalog` | `cli-helper` | `cli-helper` | `medium` | 2 | 99 | classes:1, funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_local/vllm_catalog.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_local.vllm_catalog_report` | `cli-helper` | `cli-helper` | `medium` | 1 | 38 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_local/vllm_catalog_report.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_local.vllm_report` | `cli-helper` | `cli-helper` | `medium` | 1 | 64 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_local/vllm_report.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_mcp_impl` | `cli-helper` | `cli-helper` | `medium` | 1 | 83 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_mcp_impl.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_rich_output` | `cli-helper` | `cli-helper` | `medium` | 2 | 173 | funcs:12 | src/stackops/scripts/python/helpers/helpers_agents/agents_rich_output.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_run_context` | `cli` | `cli-module` | `high` | 4 | 346 | typer, funcs:18 | src/stackops/scripts/python/helpers/helpers_agents/agents_run_context.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_run_impl` | `cli` | `cli-module` | `high` | 3 | 369 | typer, funcs:12 | src/stackops/scripts/python/helpers/helpers_agents/agents_run_impl.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_run_interactive` | `cli-helper` | `cli-helper` | `medium` | 2 | 84 | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_run_interactive.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_run_interactive_script` | `cli-helper` | `cli-helper` | `medium` | 1 | 39 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_run_interactive_script.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_run_pi_monitor` | `cli-helper` | `cli-helper` | `medium` | 0 | 203 | main, __main__, classes:1, funcs:12 | src/stackops/scripts/python/helpers/helpers_agents/agents_run_pi_monitor.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_run_prompt_catalog` | `cli-helper` | `cli-helper` | `medium` | 1 | 79 | classes:3, funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_run_prompt_catalog.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_run_sandbox` | `cli-helper` | `cli-helper` | `medium` | 2 | 154 | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_run_sandbox.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_run_skill` | `cli-helper` | `cli-helper` | `medium` | 1 | 55 | funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_run_skill.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_run_types` | `cli-helper` | `cli-helper` | `medium` | 4 | 3 | - | src/stackops/scripts/python/helpers/helpers_agents/agents_run_types.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_sandbox` | `cli-helper` | `cli-helper` | `medium` | 7 | 123 | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_sandbox.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_sandbox_prompt_access` | `cli-helper` | `cli-helper` | `medium` | 1 | 146 | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_sandbox_prompt_access.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_second_brain_activity` | `cli-helper` | `cli-helper` | `medium` | 3 | 127 | classes:3, funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_second_brain_activity.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_second_brain_constants` | `cli-helper` | `cli-helper` | `medium` | 3 | 26 | - | src/stackops/scripts/python/helpers/helpers_agents/agents_second_brain_constants.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_second_brain_progress` | `cli-helper` | `cli-helper` | `medium` | 1 | 80 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_second_brain_progress.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_second_brain_records` | `cli-helper` | `cli-helper` | `medium` | 4 | 191 | classes:3, funcs:6 | src/stackops/scripts/python/helpers/helpers_agents/agents_second_brain_records.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_second_brain_report` | `cli-helper` | `cli-helper` | `medium` | 1 | 151 | funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_second_brain_report.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_shell` | `cli-helper` | `cli-helper` | `medium` | 15 | 98 | funcs:13 | src/stackops/scripts/python/helpers/helpers_agents/agents_shell.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_skill_impl` | `cli-helper` | `cli-helper` | `medium` | 4 | 260 | classes:1, funcs:16 | src/stackops/scripts/python/helpers/helpers_agents/agents_skill_impl.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_skill_stackops_backend` | `cli-helper` | `cli-helper` | `medium` | 3 | 205 | classes:2, funcs:9 | src/stackops/scripts/python/helpers/helpers_agents/agents_skill_stackops_backend.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_skill_types` | `cli-helper` | `cli-helper` | `medium` | 3 | 4 | - | src/stackops/scripts/python/helpers/helpers_agents/agents_skill_types.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_aoe` | `cli-helper` | `cli-helper` | `medium` | 3 | 113 | funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_aoe.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_aoe_acp` | `cli-helper` | `cli-helper` | `medium` | 1 | 119 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_aoe_acp.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_aoe_inspect` | `cli-helper` | `cli-helper` | `medium` | 1 | 100 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_aoe_inspect.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_assessment` | `cli-helper` | `cli-helper` | `medium` | 4 | 87 | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_assessment.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_btw` | `cli-helper` | `cli-helper` | `medium` | 1 | 164 | funcs:7 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_btw.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_collect` | `cli-helper` | `cli-helper` | `medium` | 1 | 139 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_collect.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_filters` | `cli-helper` | `cli-helper` | `medium` | 2 | 75 | funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_filters.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_herdr` | `cli-helper` | `cli-helper` | `medium` | 2 | 120 | funcs:5 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_herdr.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_herdr_inspect` | `cli-helper` | `cli-helper` | `medium` | 1 | 117 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_herdr_inspect.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_history` | `cli-helper` | `cli-helper` | `medium` | 3 | 104 | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_history.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_history_claude` | `cli-helper` | `cli-helper` | `medium` | 1 | 104 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_history_claude.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_history_codex` | `cli-helper` | `cli-helper` | `medium` | 1 | 114 | funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_history_codex.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_history_common` | `cli-helper` | `cli-helper` | `medium` | 3 | 79 | classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_history_common.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_inspect` | `cli-helper` | `cli-helper` | `medium` | 3 | 113 | classes:1, funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_inspect.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_links` | `cli-helper` | `cli-helper` | `medium` | 2 | 118 | funcs:7 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_links.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_models` | `cli-helper` | `cli-helper` | `medium` | 21 | 118 | classes:7 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_models.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_processes` | `cli-helper` | `cli-helper` | `medium` | 3 | 166 | classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_processes.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_render` | `cli-helper` | `cli-helper` | `medium` | 2 | 235 | funcs:10 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_render.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_rich_output` | `cli-helper` | `cli-helper` | `medium` | 1 | 148 | funcs:5 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_rich_output.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_t3` | `cli-helper` | `cli-helper` | `medium` | 1 | 173 | funcs:5 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_t3.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_status_tuios` | `cli-helper` | `cli-helper` | `medium` | 10 | 96 | funcs:7 | src/stackops/scripts/python/helpers/helpers_agents/agents_status_tuios.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_t3_launch` | `cli` | `cli-module` | `high` | 1 | 150 | typer, classes:4, funcs:5 | src/stackops/scripts/python/helpers/helpers_agents/agents_t3_launch.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_t3_mcp` | `cli-helper` | `cli-helper` | `medium` | 3 | 170 | classes:1, funcs:11 | src/stackops/scripts/python/helpers/helpers_agents/agents_t3_mcp.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_yaml_schemas` | `cli-helper` | `cli-helper` | `medium` | 0 | 27 | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_yaml_schemas.py |  |
| `stackops.scripts.python.helpers.helpers_agents.browser_cdp_relay` | `cli-helper` | `cli-helper` | `medium` | 0 | 111 | main, __main__, classes:1, funcs:7 | src/stackops/scripts/python/helpers/helpers_agents/browser_cdp_relay.py |  |
| `stackops.scripts.python.helpers.helpers_agents.browser_guides` | `package` | `package-marker` | `high` | 1 | 16 | - | src/stackops/scripts/python/helpers/helpers_agents/browser_guides/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.browser_launchers` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/scripts/python/helpers/helpers_agents/browser_launchers/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.browser_launchers.brave` | `cli-helper` | `cli-helper` | `medium` | 1 | 46 | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/browser_launchers/brave.py |  |
| `stackops.scripts.python.helpers.helpers_agents.browser_launchers.chrome` | `cli-helper` | `cli-helper` | `medium` | 1 | 46 | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/browser_launchers/chrome.py |  |
| `stackops.scripts.python.helpers.helpers_agents.browser_launchers.common` | `cli-helper` | `cli-helper` | `medium` | 4 | 19 | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/browser_launchers/common.py |  |
| `stackops.scripts.python.helpers.helpers_agents.browser_launchers.edge` | `cli-helper` | `cli-helper` | `medium` | 1 | 46 | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/browser_launchers/edge.py |  |
| `stackops.scripts.python.helpers.helpers_agents.browser_launchers.firefox` | `cli-helper` | `cli-helper` | `medium` | 1 | 45 | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/browser_launchers/firefox.py |  |
| `stackops.scripts.python.helpers.helpers_agents.browser_launchers.models` | `cli-helper` | `cli-helper` | `medium` | 6 | 31 | classes:3 | src/stackops/scripts/python/helpers/helpers_agents/browser_launchers/models.py |  |
| `stackops.scripts.python.helpers.helpers_agents.browser_launchers.registry` | `cli-helper` | `cli-helper` | `medium` | 9 | 25 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/browser_launchers/registry.py |  |
| `stackops.scripts.python.helpers.helpers_agents.browser_launchers.safari` | `cli-helper` | `cli-helper` | `medium` | 1 | 32 | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/browser_launchers/safari.py |  |
| `stackops.scripts.python.helpers.helpers_agents.constants` | `cli-helper` | `cli-helper` | `medium` | 10 | 45 | - | src/stackops/scripts/python/helpers/helpers_agents/constants.py |  |
| `stackops.scripts.python.helpers.helpers_agents.cortex_launch` | `cli-helper` | `cli-helper` | `medium` | 6 | 34 | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/cortex_launch.py |  |
| `stackops.scripts.python.helpers.helpers_agents.cortex_paths` | `cli-helper` | `cli-helper` | `medium` | 3 | 8 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/cortex_paths.py |  |
| `stackops.scripts.python.helpers.helpers_agents.deepseek_launch` | `cli-helper` | `cli-helper` | `medium` | 4 | 35 | funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/deepseek_launch.py |  |
| `stackops.scripts.python.helpers.helpers_agents.deepseek_mcp` | `cli-helper` | `cli-helper` | `medium` | 1 | 109 | funcs:4 | src/stackops/scripts/python/helpers/helpers_agents/deepseek_mcp.py |  |
| `stackops.scripts.python.helpers.helpers_agents.fire_agents_help_launch` | `cli-helper` | `cli-helper` | `medium` | 1 | 375 | funcs:10 | src/stackops/scripts/python/helpers/helpers_agents/fire_agents_help_launch.py |  |
| `stackops.scripts.python.helpers.helpers_agents.maki_launch` | `cli-helper` | `cli-helper` | `medium` | 5 | 22 | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/maki_launch.py |  |
| `stackops.scripts.python.helpers.helpers_agents.maki_mcp` | `cli-helper` | `cli-helper` | `medium` | 1 | 43 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/maki_mcp.py |  |
| `stackops.scripts.python.helpers.helpers_agents.maki_paths` | `cli-helper` | `cli-helper` | `medium` | 2 | 13 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/maki_paths.py |  |
| `stackops.scripts.python.helpers.helpers_agents.mcp_catalog` | `cli-helper` | `cli-helper` | `medium` | 4 | 345 | funcs:16 | src/stackops/scripts/python/helpers/helpers_agents/mcp_catalog.py |  |
| `stackops.scripts.python.helpers.helpers_agents.mcp_install` | `cli-helper` | `cli-helper` | `medium` | 4 | 769 | funcs:37 | src/stackops/scripts/python/helpers/helpers_agents/mcp_install.py |  |
| `stackops.scripts.python.helpers.helpers_agents.mcp_types` | `cli-helper` | `cli-helper` | `medium` | 8 | 46 | classes:5 | src/stackops/scripts/python/helpers/helpers_agents/mcp_types.py |  |
| `stackops.scripts.python.helpers.helpers_agents.prime_agent_launch` | `cli-helper` | `cli-helper` | `medium` | 4 | 24 | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/prime_agent_launch.py |  |
| `stackops.scripts.python.helpers.helpers_agents.prime_agent_mcp` | `cli-helper` | `cli-helper` | `medium` | 1 | 79 | funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/prime_agent_mcp.py |  |
| `stackops.scripts.python.helpers.helpers_agents.prime_agent_paths` | `cli-helper` | `cli-helper` | `medium` | 2 | 7 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/prime_agent_paths.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.aichat` | `package` | `package-marker` | `high` | 1 | 1 | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/aichat/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.auggie` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/auggie/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.auggie.auggie_privacy` | `cli-helper` | `cli-helper` | `medium` | 2 | 37 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/auggie/auggie_privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.chatgpt` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/chatgpt/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.chatgpt.chatgpt_privacy` | `cli-helper` | `cli-helper` | `medium` | 2 | 43 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/chatgpt/chatgpt_privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.cline` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/cline/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.cline.cline_privacy` | `cli-helper` | `cli-helper` | `medium` | 2 | 43 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/cline/cline_privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.codex` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/codex/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.codex.codex_privacy` | `cli-helper` | `cli-helper` | `medium` | 2 | 33 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/codex/codex_privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.common` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/common/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.common.json_settings` | `cli-helper` | `cli-helper` | `medium` | 7 | 18 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/common/json_settings.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.common.privacy_orchestrator` | `cli-helper` | `cli-helper` | `medium` | 1 | 125 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/common/privacy_orchestrator.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.copilot` | `package` | `package-marker` | `high` | 1 | 1 | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/copilot/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.crush` | `package` | `package-marker` | `high` | 1 | 1 | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/crush/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.cursor` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/cursor/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.cursor.cursor_privacy` | `cli-helper` | `cli-helper` | `medium` | 2 | 51 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/cursor/cursor_privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.droid` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/droid/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.droid.droid_privacy` | `cli-helper` | `cli-helper` | `medium` | 2 | 25 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/droid/droid_privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.kilocode` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/kilocode/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.kilocode.kilocode_privacy` | `cli-helper` | `cli-helper` | `medium` | 2 | 32 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/kilocode/kilocode_privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.mods` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/mods/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.mods.mods_privacy` | `cli-helper` | `cli-helper` | `medium` | 2 | 35 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/mods/mods_privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.opencode` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/opencode/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.q` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/q/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.q.q_privacy` | `cli-helper` | `cli-helper` | `medium` | 2 | 58 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/q/q_privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.qwen` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/qwen/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.qwen.qwen_privacy` | `cli-helper` | `cli-helper` | `medium` | 2 | 24 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/qwen/qwen_privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.privacy` | `cli-helper` | `cli-helper` | `medium` | 0 | 28 | __main__, __all__ | src/stackops/scripts/python/helpers/helpers_agents/privacy/privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.reasoning_capabilities` | `cli-helper` | `cli-helper` | `medium` | 8 | 99 | classes:1, funcs:6 | src/stackops/scripts/python/helpers/helpers_agents/reasoning_capabilities.py |  |
| `stackops.scripts.python.helpers.helpers_agents.type_check_context` | `cli-helper` | `cli-helper` | `medium` | 2 | 54 | classes:1, funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/type_check_context.py |  |
| `stackops.scripts.python.helpers.helpers_cloud` | `package` | `package-marker` | `high` | 1 | 0 | - | src/stackops/scripts/python/helpers/helpers_cloud/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.backup_config` | `cli-helper` | `cli-helper` | `medium` | 10 | 366 | classes:1, funcs:22 | src/stackops/scripts/python/helpers/helpers_cloud/backup_config.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.backup_registration` | `cli-helper` | `cli-helper` | `medium` | 4 | 146 | classes:1, funcs:5 | src/stackops/scripts/python/helpers/helpers_cloud/backup_registration.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.backup_remote` | `cli-helper` | `cli-helper` | `medium` | 2 | 16 | funcs:2 | src/stackops/scripts/python/helpers/helpers_cloud/backup_remote.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.backup_selection` | `cli-helper` | `cli-helper` | `medium` | 2 | 50 | classes:1, funcs:2 | src/stackops/scripts/python/helpers/helpers_cloud/backup_selection.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.cloud_copy` | `cli-helper` | `cli-helper` | `medium` | 2 | 402 | main, classes:1, funcs:10 | src/stackops/scripts/python/helpers/helpers_cloud/cloud_copy.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.cloud_copy_artifacts` | `cli-helper` | `cli-helper` | `medium` | 1 | 182 | classes:1, funcs:6 | src/stackops/scripts/python/helpers/helpers_cloud/cloud_copy_artifacts.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.cloud_copy_summary` | `cli-helper` | `cli-helper` | `medium` | 1 | 78 | funcs:1 | src/stackops/scripts/python/helpers/helpers_cloud/cloud_copy_summary.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.cloud_helpers` | `cli-helper` | `cli-helper` | `medium` | 1 | 43 | funcs:8 | src/stackops/scripts/python/helpers/helpers_cloud/cloud_helpers.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.cloud_mount` | `cli` | `cli-module` | `high` | 1 | 276 | typer, typer-app, cli-registration, get_app, __main__, funcs:4 | src/stackops/scripts/python/helpers/helpers_cloud/cloud_mount.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.cloud_mount_background` | `cli-helper` | `cli-helper` | `medium` | 1 | 53 | classes:1, funcs:1 | src/stackops/scripts/python/helpers/helpers_cloud/cloud_mount_background.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.cloud_mount_directory` | `cli-helper` | `cli-helper` | `medium` | 1 | 21 | funcs:1 | src/stackops/scripts/python/helpers/helpers_cloud/cloud_mount_directory.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.cloud_mount_tmux` | `cli-helper` | `cli-helper` | `medium` | 2 | 67 | funcs:2 | src/stackops/scripts/python/helpers/helpers_cloud/cloud_mount_tmux.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.cloud_mount_tuios` | `cli-helper` | `cli-helper` | `medium` | 1 | 72 | funcs:1 | src/stackops/scripts/python/helpers/helpers_cloud/cloud_mount_tuios.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.cloud_path_resolver` | `cli-helper` | `cli-helper` | `medium` | 8 | 75 | funcs:1 | src/stackops/scripts/python/helpers/helpers_cloud/cloud_path_resolver.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.cloud_sync` | `cli-helper` | `cli-helper` | `medium` | 1 | 84 | main, funcs:1 | src/stackops/scripts/python/helpers/helpers_cloud/cloud_sync.py |  |
| `stackops.scripts.python.helpers.helpers_devops` | `package` | `package-marker` | `high` | 31 | 0 | - | src/stackops/scripts/python/helpers/helpers_devops/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_backup_retrieve` | `cli-helper` | `cli-helper` | `medium` | 2 | 326 | __main__, funcs:6 | src/stackops/scripts/python/helpers/helpers_devops/cli_backup_retrieve.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_cloudflare` | `cli` | `cli-module` | `high` | 1 | 197 | typer, typer-app, cli-registration, get_app, funcs:6 | src/stackops/scripts/python/helpers/helpers_devops/cli_cloudflare.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_cloudflare_tunnel` | `cli` | `cli-module` | `high` | 1 | 142 | typer, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/cli_cloudflare_tunnel.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config` | `cli` | `cli-module` | `high` | 1 | 109 | typer, typer-app, cli-registration, get_app, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/cli_config.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_collect` | `cli` | `cli-module` | `high` | 2 | 166 | typer, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_dotfile_collect.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_mapper` | `cli` | `cli-module` | `high` | 6 | 373 | typer, typer-app, cli-registration, __main__, funcs:15 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_dotfile_mapper.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_status` | `cli` | `cli-module` | `high` | 1 | 72 | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_dotfile_status.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_status_data` | `cli-helper` | `cli-helper` | `medium` | 4 | 166 | classes:7, funcs:9 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_dotfile_status_data.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_status_render` | `cli-helper` | `cli-helper` | `medium` | 2 | 106 | funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_dotfile_status_render.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_status_render_radar` | `cli-helper` | `cli-helper` | `medium` | 1 | 65 | funcs:2 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_dotfile_status_render_radar.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_transfer` | `cli` | `cli-module` | `high` | 2 | 187 | typer, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_dotfile_transfer.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_dotfiles` | `cli` | `cli-module` | `high` | 1 | 31 | typer, typer-app, cli-registration, get_app, funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_dotfiles.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_dump` | `cli` | `cli-module` | `high` | 2 | 55 | typer, funcs:2 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_dump.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_edit` | `cli` | `cli-module` | `high` | 1 | 22 | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_edit.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_files` | `cli` | `cli-module` | `high` | 1 | 28 | typer, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_files.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_init_script` | `cli` | `cli-module` | `high` | 1 | 74 | typer, funcs:2 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_init_script.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_mount` | `cli` | `cli-module` | `high` | 2 | 144 | typer, funcs:5 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_mount.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets` | `cli` | `cli-module` | `high` | 1 | 183 | typer, typer-app, cli-registration, get_app, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_actions` | `cli` | `cli-module` | `high` | 5 | 376 | typer, classes:1, funcs:22 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets_actions.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_add` | `cli` | `cli-module` | `high` | 1 | 103 | typer, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets_add.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_candidates` | `cli` | `cli-module` | `high` | 5 | 336 | typer, __all__, classes:2, funcs:21 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets_candidates.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_constants` | `cli-helper` | `cli-helper` | `medium` | 11 | 6 | - | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets_constants.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_delete` | `cli` | `cli-module` | `high` | 1 | 185 | typer, classes:2, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets_delete.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_errors` | `cli` | `cli-module` | `high` | 1 | 40 | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets_errors.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_files` | `cli` | `cli-module` | `high` | 1 | 75 | typer, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets_files.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_json` | `cli-helper` | `cli-helper` | `medium` | 1 | 22 | funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets_json.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_prompts` | `cli` | `cli-module` | `high` | 2 | 152 | typer, funcs:10 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets_prompts.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_rotate` | `cli` | `cli-module` | `high` | 1 | 169 | typer, classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets_rotate.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_search` | `cli` | `cli-module` | `high` | 1 | 174 | typer, funcs:2 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets_search.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_selection` | `cli` | `cli-module` | `high` | 3 | 150 | typer, classes:2, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets_selection.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_subset_selection` | `cli` | `cli-module` | `high` | 1 | 22 | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets_subset_selection.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_support` | `cli` | `cli-module` | `high` | 8 | 489 | typer, classes:2, funcs:31 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets_support.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_validation` | `cli-helper` | `cli-helper` | `medium` | 4 | 7 | funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets_validation.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_setup` | `cli` | `cli-module` | `high` | 1 | 174 | typer, typer-app, cli-registration, get_app, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_setup.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_setup_config` | `cli` | `cli-module` | `high` | 4 | 79 | typer, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_setup_config.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_setup_domains` | `cli` | `cli-module` | `high` | 1 | 117 | typer, funcs:5 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_setup_domains.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_setup_multiplexer` | `cli` | `cli-module` | `high` | 1 | 60 | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_setup_multiplexer.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_terminal` | `cli` | `cli-module` | `high` | 1 | 188 | typer, typer-app, cli-registration, get_app, funcs:8 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_terminal.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_tmux` | `cli` | `cli-module` | `high` | 1 | 249 | typer, typer-app, cli-registration, get_app, classes:1, funcs:19 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_tmux.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_data` | `cli` | `cli-module` | `high` | 2 | 298 | typer, typer-app, cli-registration, get_app, funcs:7 | src/stackops/scripts/python/helpers/helpers_devops/cli_data.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_data_display` | `cli` | `cli-module` | `high` | 1 | 124 | typer, funcs:2 | src/stackops/scripts/python/helpers/helpers_devops/cli_data_display.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_data_edit` | `cli` | `cli-module` | `high` | 1 | 16 | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/cli_data_edit.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_data_encrypt` | `cli` | `cli-module` | `high` | 5 | 262 | typer, funcs:12 | src/stackops/scripts/python/helpers/helpers_devops/cli_data_encrypt.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_data_encrypt_output` | `cli-helper` | `cli-helper` | `medium` | 2 | 49 | funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/cli_data_encrypt_output.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_data_subset` | `cli` | `cli-module` | `high` | 1 | 186 | typer, funcs:8 | src/stackops/scripts/python/helpers/helpers_devops/cli_data_subset.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_data_subset_io` | `cli` | `cli-module` | `high` | 1 | 86 | typer, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/cli_data_subset_io.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_device` | `cli` | `cli-module` | `high` | 1 | 134 | typer, typer-app, cli-registration, get_app, funcs:5 | src/stackops/scripts/python/helpers/helpers_devops/cli_device.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_interactive_picker` | `cli` | `cli-module` | `high` | 5 | 90 | typer, classes:1, funcs:7 | src/stackops/scripts/python/helpers/helpers_devops/cli_interactive_picker.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_nw` | `cli` | `cli-module` | `high` | 1 | 239 | typer, typer-app, cli-registration, get_app, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/cli_nw.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_nw_vscode_share` | `cli` | `cli-module` | `high` | 1 | 180 | typer, funcs:8 | src/stackops/scripts/python/helpers/helpers_devops/cli_nw_vscode_share.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_repos` | `cli` | `cli-module` | `high` | 2 | 278 | typer, typer-app, cli-registration, get_app, funcs:9 | src/stackops/scripts/python/helpers/helpers_devops/cli_repos.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_repos_edit` | `cli` | `cli-module` | `high` | 1 | 18 | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/cli_repos_edit.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_repos_files` | `cli` | `cli-module` | `high` | 1 | 34 | typer, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/cli_repos_files.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_repos_list` | `cli` | `cli-module` | `high` | 1 | 107 | typer, classes:1, funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/cli_repos_list.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_repos_selection` | `cli-helper` | `cli-helper` | `medium` | 1 | 65 | funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/cli_repos_selection.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_repos_version` | `cli` | `cli-module` | `high` | 1 | 238 | typer, typer-app, cli-registration, get_app, funcs:10 | src/stackops/scripts/python/helpers/helpers_devops/cli_repos_version.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_scripts` | `cli` | `cli-module` | `high` | 1 | 115 | typer, typer-app, cli-registration, get_app, funcs:5 | src/stackops/scripts/python/helpers/helpers_devops/cli_scripts.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self` | `cli` | `cli-module` | `high` | 2 | 281 | typer, typer-app, cli-registration, get_app, funcs:8 | src/stackops/scripts/python/helpers/helpers_devops/cli_self.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self_assets` | `cli` | `cli-module` | `high` | 1 | 79 | typer, typer-app, cli-registration, get_app, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/cli_self_assets.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self_clone` | `cli` | `cli-module` | `high` | 1 | 147 | typer, funcs:5 | src/stackops/scripts/python/helpers/helpers_devops/cli_self_clone.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self_docker` | `cli-helper` | `cli-helper` | `medium` | 1 | 173 | classes:2, funcs:9 | src/stackops/scripts/python/helpers/helpers_devops/cli_self_docker.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self_docs` | `cli` | `cli-module` | `high` | 3 | 162 | typer, classes:1, funcs:9 | src/stackops/scripts/python/helpers/helpers_devops/cli_self_docs.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self_export` | `cli` | `cli-module` | `high` | 1 | 135 | typer, funcs:2 | src/stackops/scripts/python/helpers/helpers_devops/cli_self_export.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self_info` | `cli` | `cli-module` | `high` | 1 | 224 | typer, funcs:6 | src/stackops/scripts/python/helpers/helpers_devops/cli_self_info.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self_release` | `cli` | `cli-module` | `high` | 1 | 58 | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/cli_self_release.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self_repo` | `cli` | `cli-module` | `high` | 5 | 58 | typer, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/cli_self_repo.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_share_file` | `cli` | `cli-module` | `high` | 2 | 294 | typer, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/cli_share_file.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_share_server` | `cli` | `cli-module` | `high` | 2 | 153 | typer, typer-app, cli-registration, __main__, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/cli_share_server.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_share_temp` | `cli` | `cli-module` | `high` | 1 | 107 | typer, classes:1, funcs:5 | src/stackops/scripts/python/helpers/helpers_devops/cli_share_temp.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_share_terminal` | `cli` | `cli-module` | `high` | 1 | 174 | typer, typer-app, cli-registration, __main__, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/cli_share_terminal.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_software` | `cli` | `cli-module` | `high` | 1 | 92 | typer, typer-app, cli-registration, get_app, funcs:2 | src/stackops/scripts/python/helpers/helpers_devops/cli_software.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_software_attrs` | `cli` | `cli-module` | `high` | 1 | 44 | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/cli_software_attrs.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_software_files` | `cli` | `cli-module` | `high` | 1 | 57 | typer, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/cli_software_files.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_software_install` | `cli` | `cli-module` | `high` | 1 | 148 | typer, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/cli_software_install.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_software_report` | `cli` | `cli-module` | `high` | 1 | 87 | typer, funcs:2 | src/stackops/scripts/python/helpers/helpers_devops/cli_software_report.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_ssh` | `cli` | `cli-module` | `high` | 1 | 180 | typer, typer-app, cli-registration, get_app, funcs:6 | src/stackops/scripts/python/helpers/helpers_devops/cli_ssh.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_ssh_port` | `cli` | `cli-module` | `high` | 2 | 176 | typer, funcs:6 | src/stackops/scripts/python/helpers/helpers_devops/cli_ssh_port.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_status` | `cli` | `cli-module` | `high` | 1 | 87 | typer, funcs:2 | src/stackops/scripts/python/helpers/helpers_devops/cli_status.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_subset_support` | `cli-helper` | `cli-helper` | `medium` | 4 | 21 | funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/cli_subset_support.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_vault` | `cli` | `cli-module` | `high` | 1 | 194 | typer, typer-app, cli-registration, get_app, funcs:8 | src/stackops/scripts/python/helpers/helpers_devops/cli_vault.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cloudflare_tunnel_config` | `cli-helper` | `cli-helper` | `medium` | 1 | 100 | classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/cloudflare_tunnel_config.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cloudflare_tunnel_maintenance` | `cli-helper` | `cli-helper` | `medium` | 1 | 183 | funcs:6 | src/stackops/scripts/python/helpers/helpers_devops/cloudflare_tunnel_maintenance.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cloudflare_tunnel_runtime` | `cli-helper` | `cli-helper` | `medium` | 2 | 163 | classes:2, funcs:10 | src/stackops/scripts/python/helpers/helpers_devops/cloudflare_tunnel_runtime.py |  |
| `stackops.scripts.python.helpers.helpers_devops.devops_status` | `cli-helper` | `cli-helper` | `medium` | 1 | 71 | main, __main__, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/devops_status.py |  |
| `stackops.scripts.python.helpers.helpers_devops.devops_status_apps` | `cli-helper` | `cli-helper` | `medium` | 2 | 47 | funcs:2 | src/stackops/scripts/python/helpers/helpers_devops/devops_status_apps.py |  |
| `stackops.scripts.python.helpers.helpers_devops.devops_status_backup` | `cli-helper` | `cli-helper` | `medium` | 2 | 82 | classes:1, funcs:2 | src/stackops/scripts/python/helpers/helpers_devops/devops_status_backup.py |  |
| `stackops.scripts.python.helpers.helpers_devops.devops_status_checks` | `cli-helper` | `cli-helper` | `medium` | 2 | 78 | classes:3, funcs:2 | src/stackops/scripts/python/helpers/helpers_devops/devops_status_checks.py |  |
| `stackops.scripts.python.helpers.helpers_devops.devops_status_config` | `cli-helper` | `cli-helper` | `medium` | 3 | 153 | classes:2, funcs:5 | src/stackops/scripts/python/helpers/helpers_devops/devops_status_config.py |  |
| `stackops.scripts.python.helpers.helpers_devops.devops_status_constants` | `cli-helper` | `cli-helper` | `medium` | 4 | 18 | - | src/stackops/scripts/python/helpers/helpers_devops/devops_status_constants.py |  |
| `stackops.scripts.python.helpers.helpers_devops.devops_status_data` | `cli-helper` | `cli-helper` | `medium` | 3 | 120 | classes:1, funcs:2 | src/stackops/scripts/python/helpers/helpers_devops/devops_status_data.py |  |
| `stackops.scripts.python.helpers.helpers_devops.devops_status_display` | `cli-helper` | `cli-helper` | `medium` | 2 | 132 | funcs:11 | src/stackops/scripts/python/helpers/helpers_devops/devops_status_display.py |  |
| `stackops.scripts.python.helpers.helpers_devops.devops_status_managed` | `cli-helper` | `cli-helper` | `medium` | 1 | 107 | classes:1, funcs:2 | src/stackops/scripts/python/helpers/helpers_devops/devops_status_managed.py |  |
| `stackops.scripts.python.helpers.helpers_devops.devops_status_repos` | `cli-helper` | `cli-helper` | `medium` | 2 | 94 | classes:2, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/devops_status_repos.py |  |
| `stackops.scripts.python.helpers.helpers_devops.devops_status_tui` | `cli-helper` | `cli-helper` | `medium` | 1 | 168 | classes:1 | src/stackops/scripts/python/helpers/helpers_devops/devops_status_tui.py |  |
| `stackops.scripts.python.helpers.helpers_devops.devops_update_repos` | `cli-helper` | `cli-helper` | `medium` | 0 | 235 | main, __main__, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/devops_update_repos.py |  |
| `stackops.scripts.python.helpers.helpers_devops.file_receive_proposal` | `cli` | `cli-module` | `high` | 1 | 123 | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/file_receive_proposal.py |  |
| `stackops.scripts.python.helpers.helpers_devops.file_send_encryption` | `cli` | `cli-module` | `high` | 1 | 32 | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/file_send_encryption.py |  |
| `stackops.scripts.python.helpers.helpers_devops.file_send_runtime` | `cli` | `cli-module` | `high` | 1 | 92 | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/file_send_runtime.py |  |
| `stackops.scripts.python.helpers.helpers_devops.interactive` | `cli-helper` | `cli-helper` | `medium` | 1 | 228 | main, __main__, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/interactive.py |  |
| `stackops.scripts.python.helpers.helpers_devops.mount_helpers` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/scripts/python/helpers/helpers_devops/mount_helpers/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_devops.mount_helpers.commands` | `cli-helper` | `cli-helper` | `medium` | 8 | 33 | funcs:5 | src/stackops/scripts/python/helpers/helpers_devops/mount_helpers/commands.py |  |
| `stackops.scripts.python.helpers.helpers_devops.mount_helpers.device_entry` | `cli-helper` | `cli-helper` | `medium` | 12 | 17 | classes:1 | src/stackops/scripts/python/helpers/helpers_devops/mount_helpers/device_entry.py |  |
| `stackops.scripts.python.helpers.helpers_devops.mount_helpers.devices` | `cli-helper` | `cli-helper` | `medium` | 3 | 17 | funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/mount_helpers/devices.py |  |
| `stackops.scripts.python.helpers.helpers_devops.mount_helpers.linux` | `cli-helper` | `cli-helper` | `medium` | 2 | 221 | funcs:10 | src/stackops/scripts/python/helpers/helpers_devops/mount_helpers/linux.py |  |
| `stackops.scripts.python.helpers.helpers_devops.mount_helpers.macos` | `cli-helper` | `cli-helper` | `medium` | 3 | 101 | funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/mount_helpers/macos.py |  |
| `stackops.scripts.python.helpers.helpers_devops.mount_helpers.selection` | `cli-helper` | `cli-helper` | `medium` | 2 | 38 | funcs:2 | src/stackops/scripts/python/helpers/helpers_devops/mount_helpers/selection.py |  |
| `stackops.scripts.python.helpers.helpers_devops.mount_helpers.utils` | `cli-helper` | `cli-helper` | `medium` | 4 | 28 | funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/mount_helpers/utils.py |  |
| `stackops.scripts.python.helpers.helpers_devops.mount_helpers.windows` | `cli-helper` | `cli-helper` | `medium` | 2 | 86 | funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/mount_helpers/windows.py |  |
| `stackops.scripts.python.helpers.helpers_devops.network_service` | `cli` | `cli-module` | `high` | 9 | 174 | typer, classes:1, funcs:8 | src/stackops/scripts/python/helpers/helpers_devops/network_service.py |  |
| `stackops.scripts.python.helpers.helpers_devops.register_interactive` | `cli` | `cli-module` | `high` | 5 | 72 | typer, funcs:7 | src/stackops/scripts/python/helpers/helpers_devops/register_interactive.py |  |
| `stackops.scripts.python.helpers.helpers_devops.run_script` | `cli` | `cli-module` | `high` | 1 | 161 | typer, typer-app, cli-registration, get_app, funcs:9 | src/stackops/scripts/python/helpers/helpers_devops/run_script.py |  |
| `stackops.scripts.python.helpers.helpers_devops.script_discovery` | `cli-helper` | `cli-helper` | `medium` | 5 | 37 | funcs:2 | src/stackops/scripts/python/helpers/helpers_devops/script_discovery.py |  |
| `stackops.scripts.python.helpers.helpers_devops.script_resolution` | `cli` | `cli-module` | `high` | 3 | 127 | typer, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/script_resolution.py |  |
| `stackops.scripts.python.helpers.helpers_devops.script_sources` | `cli-helper` | `cli-helper` | `medium` | 4 | 24 | funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/script_sources.py |  |
| `stackops.scripts.python.helpers.helpers_devops.share_server_filebrowser` | `cli` | `cli-module` | `high` | 1 | 58 | typer, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/share_server_filebrowser.py |  |
| `stackops.scripts.python.helpers.helpers_devops.stackops_publish` | `cli-helper` | `cli-helper` | `medium` | 1 | 93 | classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/stackops_publish.py |  |
| `stackops.scripts.python.helpers.helpers_devops.stackops_release` | `cli-helper` | `cli-helper` | `medium` | 4 | 101 | classes:2, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/stackops_release.py |  |
| `stackops.scripts.python.helpers.helpers_devops.stackops_release_constants` | `cli-helper` | `cli-helper` | `medium` | 1 | 4 | - | src/stackops/scripts/python/helpers/helpers_devops/stackops_release_constants.py |  |
| `stackops.scripts.python.helpers.helpers_devops.stackops_skill_refs` | `cli-helper` | `cli-helper` | `medium` | 1 | 205 | funcs:12 | src/stackops/scripts/python/helpers/helpers_devops/stackops_skill_refs.py |  |
| `stackops.scripts.python.helpers.helpers_devops.stackops_versioning` | `cli-helper` | `cli-helper` | `medium` | 2 | 42 | classes:1, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/stackops_versioning.py |  |
| `stackops.scripts.python.helpers.helpers_devops.themes` | `package` | `package-marker` | `high` | 1 | 4 | - | src/stackops/scripts/python/helpers/helpers_devops/themes/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_devops.themes.choose_wezterm_theme` | `cli-helper` | `cli-helper` | `medium` | 3 | 128 | main, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/themes/choose_wezterm_theme.py |  |
| `stackops.scripts.python.helpers.helpers_devops.themes.theme_commands` | `cli` | `cli-module` | `high` | 1 | 98 | typer, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/themes/theme_commands.py |  |
| `stackops.scripts.python.helpers.helpers_devops.vault` | `cli-helper` | `cli-helper` | `medium` | 5 | 459 | classes:4, funcs:26 | src/stackops/scripts/python/helpers/helpers_devops/vault.py |  |
| `stackops.scripts.python.helpers.helpers_devops.vault_clipboard` | `cli` | `cli-module` | `high` | 2 | 92 | typer, classes:3, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/vault_clipboard.py |  |
| `stackops.scripts.python.helpers.helpers_devops.vault_clipboard_clear` | `cli-helper` | `cli-helper` | `medium` | 1 | 29 | main, __main__, classes:1, funcs:2 | src/stackops/scripts/python/helpers/helpers_devops/vault_clipboard_clear.py |  |
| `stackops.scripts.python.helpers.helpers_devops.vault_constants` | `cli-helper` | `cli-helper` | `medium` | 4 | 24 | classes:1 | src/stackops/scripts/python/helpers/helpers_devops/vault_constants.py |  |
| `stackops.scripts.python.helpers.helpers_devops.vault_environment` | `cli` | `cli-module` | `high` | 2 | 44 | typer, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/vault_environment.py |  |
| `stackops.scripts.python.helpers.helpers_devops.vault_search` | `cli-helper` | `cli-helper` | `medium` | 1 | 206 | classes:2, funcs:7 | src/stackops/scripts/python/helpers/helpers_devops/vault_search.py |  |
| `stackops.scripts.python.helpers.helpers_devops.vault_search_output` | `cli-helper` | `cli-helper` | `medium` | 1 | 119 | classes:1, funcs:8 | src/stackops/scripts/python/helpers/helpers_devops/vault_search_output.py |  |
| `stackops.scripts.python.helpers.helpers_devops.vscode_share_runtime` | `cli` | `cli-module` | `high` | 1 | 76 | typer, funcs:2 | src/stackops/scripts/python/helpers/helpers_devops/vscode_share_runtime.py |  |
| `stackops.scripts.python.helpers.helpers_devops.vscode_tunnel_auth` | `cli-helper` | `cli-helper` | `medium` | 1 | 50 | funcs:2 | src/stackops/scripts/python/helpers/helpers_devops/vscode_tunnel_auth.py |  |
| `stackops.scripts.python.helpers.helpers_env` | `package` | `package-marker` | `high` | 1 | 3 | - | src/stackops/scripts/python/helpers/helpers_env/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_env.env_manager_tui` | `cli-helper` | `cli-helper` | `medium` | 0 | 228 | main, __main__, classes:4, funcs:4 | src/stackops/scripts/python/helpers/helpers_env/env_manager_tui.py |  |
| `stackops.scripts.python.helpers.helpers_env.path_manager_backend` | `cli-helper` | `cli-helper` | `medium` | 3 | 43 | funcs:3 | src/stackops/scripts/python/helpers/helpers_env/path_manager_backend.py |  |
| `stackops.scripts.python.helpers.helpers_env.path_manager_tui` | `cli-helper` | `cli-helper` | `medium` | 0 | 252 | main, __main__, classes:3, funcs:1 | src/stackops/scripts/python/helpers/helpers_env/path_manager_tui.py |  |
| `stackops.scripts.python.helpers.helpers_fire_command` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/scripts/python/helpers/helpers_fire_command/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_fire_command.cloud_manager` | `cli-helper` | `cli-helper` | `medium` | 0 | 75 | - | src/stackops/scripts/python/helpers/helpers_fire_command/cloud_manager.py |  |
| `stackops.scripts.python.helpers.helpers_fire_command.f` | `cli-helper` | `cli-helper` | `medium` | 0 | 0 | - | src/stackops/scripts/python/helpers/helpers_fire_command/f.py |  |
| `stackops.scripts.python.helpers.helpers_fire_command.file_wrangler` | `cli-helper` | `cli-helper` | `medium` | 2 | 102 | funcs:3 | src/stackops/scripts/python/helpers/helpers_fire_command/file_wrangler.py |  |
| `stackops.scripts.python.helpers.helpers_fire_command.fire_jobs_args_helper` | `cli` | `cli-module` | `high` | 2 | 144 | typer, classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_fire_command/fire_jobs_args_helper.py |  |
| `stackops.scripts.python.helpers.helpers_fire_command.fire_jobs_environment` | `cli-helper` | `cli-helper` | `medium` | 1 | 58 | classes:1, funcs:3 | src/stackops/scripts/python/helpers/helpers_fire_command/fire_jobs_environment.py |  |
| `stackops.scripts.python.helpers.helpers_fire_command.fire_jobs_impl` | `cli-helper` | `cli-helper` | `medium` | 1 | 372 | funcs:13 | src/stackops/scripts/python/helpers/helpers_fire_command/fire_jobs_impl.py |  |
| `stackops.scripts.python.helpers.helpers_fire_command.fire_jobs_route_helper` | `cli-helper` | `cli-helper` | `medium` | 2 | 107 | funcs:2 | src/stackops/scripts/python/helpers/helpers_fire_command/fire_jobs_route_helper.py |  |
| `stackops.scripts.python.helpers.helpers_fire_command.fire_jobs_streamlit_helper` | `cli-helper` | `cli-helper` | `medium` | 0 | 0 | - | src/stackops/scripts/python/helpers/helpers_fire_command/fire_jobs_streamlit_helper.py |  |
| `stackops.scripts.python.helpers.helpers_network` | `package` | `package-marker` | `high` | 2 | 0 | api-doc | src/stackops/scripts/python/helpers/helpers_network/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_network.address_switch` | `api-or-cli-helper` | `manual-review` | `low` | 1 | 134 | api-doc, __main__, funcs:7 | src/stackops/scripts/python/helpers/helpers_network/address_switch.py |  |
| `stackops.scripts.python.helpers.helpers_network.ftpx_impl` | `api-or-cli-helper` | `manual-review` | `low` | 1 | 303 | api-doc, funcs:7 | src/stackops/scripts/python/helpers/helpers_network/ftpx_impl.py |  |
| `stackops.scripts.python.helpers.helpers_network.onetimeshare` | `api-or-cli-helper` | `manual-review` | `low` | 0 | 65 | api-doc | src/stackops/scripts/python/helpers/helpers_network/onetimeshare.py |  |
| `stackops.scripts.python.helpers.helpers_network.ssh` | `package` | `package-marker` | `high` | 1 | 0 | api-doc | src/stackops/scripts/python/helpers/helpers_network/ssh/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_add_key_posix` | `api-or-cli-helper` | `manual-review` | `low` | 2 | 16 | api-doc, funcs:1 | src/stackops/scripts/python/helpers/helpers_network/ssh/ssh_add_key_posix.py |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_add_key_windows` | `api-or-cli-helper` | `manual-review` | `low` | 2 | 117 | api-doc, funcs:4 | src/stackops/scripts/python/helpers/helpers_network/ssh/ssh_add_key_windows.py |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_add_ssh_key` | `api-or-cli-helper` | `manual-review` | `low` | 1 | 160 | api-doc, main, funcs:5 | src/stackops/scripts/python/helpers/helpers_network/ssh/ssh_add_ssh_key.py |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_cloud_init` | `api-or-cli-helper` | `manual-review` | `low` | 0 | 33 | api-doc, funcs:2 | src/stackops/scripts/python/helpers/helpers_network/ssh/ssh_cloud_init.py |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_common` | `api-or-cli-helper` | `manual-review` | `low` | 11 | 489 | api-doc, classes:4, funcs:4 | src/stackops/scripts/python/helpers/helpers_network/ssh/ssh_debug_common.py |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_darwin` | `api-or-cli-helper` | `manual-review` | `low` | 2 | 176 | api-doc, __main__, funcs:2 | src/stackops/scripts/python/helpers/helpers_network/ssh/ssh_debug_darwin.py |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_darwin_firewall` | `api-or-cli-helper` | `manual-review` | `low` | 1 | 240 | api-doc, funcs:2 | src/stackops/scripts/python/helpers/helpers_network/ssh/ssh_debug_darwin_firewall.py |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_darwin_network` | `api-or-cli-helper` | `manual-review` | `low` | 1 | 190 | api-doc, funcs:4 | src/stackops/scripts/python/helpers/helpers_network/ssh/ssh_debug_darwin_network.py |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_darwin_utils` | `api-or-cli-helper` | `manual-review` | `low` | 1 | 137 | api-doc, funcs:3 | src/stackops/scripts/python/helpers/helpers_network/ssh/ssh_debug_darwin_utils.py |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_keys` | `api-or-cli-helper` | `manual-review` | `low` | 3 | 200 | api-doc, classes:1, funcs:3 | src/stackops/scripts/python/helpers/helpers_network/ssh/ssh_debug_keys.py |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_linux` | `api-or-cli-helper` | `manual-review` | `low` | 1 | 181 | api-doc, __main__, funcs:2 | src/stackops/scripts/python/helpers/helpers_network/ssh/ssh_debug_linux.py |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_linux_firewall` | `api-or-cli-helper` | `manual-review` | `low` | 1 | 311 | api-doc, funcs:5 | src/stackops/scripts/python/helpers/helpers_network/ssh/ssh_debug_linux_firewall.py |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_linux_utils` | `api-or-cli-helper` | `manual-review` | `low` | 1 | 257 | api-doc, classes:1, funcs:6 | src/stackops/scripts/python/helpers/helpers_network/ssh/ssh_debug_linux_utils.py |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_models` | `api-or-cli-helper` | `manual-review` | `low` | 14 | 133 | api-doc, classes:3, funcs:2 | src/stackops/scripts/python/helpers/helpers_network/ssh/ssh_debug_models.py |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_windows` | `api-or-cli-helper` | `manual-review` | `low` | 1 | 213 | api-doc, __main__, funcs:2 | src/stackops/scripts/python/helpers/helpers_network/ssh/ssh_debug_windows.py |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_windows_acl` | `api-or-cli-helper` | `manual-review` | `low` | 1 | 170 | api-doc, funcs:3 | src/stackops/scripts/python/helpers/helpers_network/ssh/ssh_debug_windows_acl.py |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_windows_firewall` | `api-or-cli-helper` | `manual-review` | `low` | 1 | 485 | api-doc, funcs:9 | src/stackops/scripts/python/helpers/helpers_network/ssh/ssh_debug_windows_firewall.py |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_windows_network` | `api-or-cli-helper` | `manual-review` | `low` | 1 | 182 | api-doc, funcs:2 | src/stackops/scripts/python/helpers/helpers_network/ssh/ssh_debug_windows_network.py |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_windows_utils` | `api-or-cli-helper` | `manual-review` | `low` | 4 | 249 | api-doc, classes:2, funcs:7 | src/stackops/scripts/python/helpers/helpers_network/ssh/ssh_debug_windows_utils.py |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_deploy_key_remote` | `api-or-cli-helper` | `manual-review` | `low` | 1 | 203 | api-doc, funcs:6 | src/stackops/scripts/python/helpers/helpers_network/ssh/ssh_deploy_key_remote.py |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_public_key_validation` | `api-or-cli-helper` | `manual-review` | `low` | 1 | 118 | api-doc, funcs:6 | src/stackops/scripts/python/helpers/helpers_network/ssh/ssh_public_key_validation.py |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_public_keys` | `api-or-cli-helper` | `manual-review` | `low` | 6 | 166 | api-doc, classes:1, funcs:7 | src/stackops/scripts/python/helpers/helpers_network/ssh/ssh_public_keys.py |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_remote_connection` | `api-or-cli-helper` | `manual-review` | `low` | 2 | 127 | api-doc, classes:2, funcs:5 | src/stackops/scripts/python/helpers/helpers_network/ssh/ssh_remote_connection.py |  |
| `stackops.scripts.python.helpers.helpers_network.warp_connect` | `api-or-cli-helper` | `manual-review` | `low` | 1 | 154 | api-doc, classes:3, funcs:7 | src/stackops/scripts/python/helpers/helpers_network/warp_connect.py |  |
| `stackops.scripts.python.helpers.helpers_network.warp_status` | `api-or-cli-helper` | `manual-review` | `low` | 2 | 69 | api-doc, classes:2, funcs:7 | src/stackops/scripts/python/helpers/helpers_network/warp_status.py |  |
| `stackops.scripts.python.helpers.helpers_network.wifi_conn` | `api-or-cli-helper` | `manual-review` | `low` | 2 | 146 | api-doc, classes:1, funcs:10 | src/stackops/scripts/python/helpers/helpers_network/wifi_conn.py |  |
| `stackops.scripts.python.helpers.helpers_network.wifi_conn_platforms.common` | `api-or-cli-helper` | `manual-review` | `low` | 6 | 45 | api-doc, classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_network/wifi_conn_platforms/common.py |  |
| `stackops.scripts.python.helpers.helpers_network.wifi_conn_platforms.darwin` | `api-or-cli-helper` | `manual-review` | `low` | 0 | 104 | api-doc, funcs:8 | src/stackops/scripts/python/helpers/helpers_network/wifi_conn_platforms/darwin.py |  |
| `stackops.scripts.python.helpers.helpers_network.wifi_conn_platforms.linux` | `api-or-cli-helper` | `manual-review` | `low` | 0 | 268 | api-doc, classes:1, funcs:16 | src/stackops/scripts/python/helpers/helpers_network/wifi_conn_platforms/linux.py |  |
| `stackops.scripts.python.helpers.helpers_network.wifi_conn_platforms.unsupported` | `api-or-cli-helper` | `manual-review` | `low` | 0 | 45 | api-doc, funcs:7 | src/stackops/scripts/python/helpers/helpers_network/wifi_conn_platforms/unsupported.py |  |
| `stackops.scripts.python.helpers.helpers_network.wifi_conn_platforms.windows` | `api-or-cli-helper` | `manual-review` | `low` | 0 | 149 | api-doc, funcs:6 | src/stackops/scripts/python/helpers/helpers_network/wifi_conn_platforms/windows.py |  |
| `stackops.scripts.python.helpers.helpers_preview` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/scripts/python/helpers/helpers_preview/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_preview.pomodoro` | `cli-helper` | `cli-helper` | `medium` | 0 | 55 | - | src/stackops/scripts/python/helpers/helpers_preview/pomodoro.py |  |
| `stackops.scripts.python.helpers.helpers_preview.preview_impl` | `cli-helper` | `cli-helper` | `medium` | 1 | 324 | funcs:7 | src/stackops/scripts/python/helpers/helpers_preview/preview_impl.py |  |
| `stackops.scripts.python.helpers.helpers_preview.preview_read` | `cli-helper` | `cli-helper` | `medium` | 1 | 66 | funcs:6 | src/stackops/scripts/python/helpers/helpers_preview/preview_read.py |  |
| `stackops.scripts.python.helpers.helpers_preview.scheduler` | `cli-helper` | `cli-helper` | `medium` | 0 | 69 | - | src/stackops/scripts/python/helpers/helpers_preview/scheduler.py |  |
| `stackops.scripts.python.helpers.helpers_preview.start_slidev` | `cli` | `cli-module` | `high` | 0 | 144 | typer, typer-app, cli-registration, main, __main__, funcs:6 | src/stackops/scripts/python/helpers/helpers_preview/start_slidev.py |  |
| `stackops.scripts.python.helpers.helpers_preview.viewer` | `cli-helper` | `cli-helper` | `medium` | 0 | 54 | - | src/stackops/scripts/python/helpers/helpers_preview/viewer.py |  |
| `stackops.scripts.python.helpers.helpers_preview.viewer_template` | `cli-helper` | `cli-helper` | `medium` | 0 | 137 | - | src/stackops/scripts/python/helpers/helpers_preview/viewer_template.py |  |
| `stackops.scripts.python.helpers.helpers_repos.action` | `cli-helper` | `cli-helper` | `medium` | 1 | 130 | classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_repos/action.py |  |
| `stackops.scripts.python.helpers.helpers_repos.action_helper` | `cli-helper` | `cli-helper` | `medium` | 2 | 153 | classes:3, funcs:3 | src/stackops/scripts/python/helpers/helpers_repos/action_helper.py |  |
| `stackops.scripts.python.helpers.helpers_repos.clone` | `cli-helper` | `cli-helper` | `medium` | 1 | 145 | funcs:6 | src/stackops/scripts/python/helpers/helpers_repos/clone.py |  |
| `stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync` | `cli` | `cli-module` | `high` | 1 | 146 | typer, main, funcs:2 | src/stackops/scripts/python/helpers/helpers_repos/cloud_repo_sync.py |  |
| `stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_actions` | `cli` | `cli-module` | `high` | 2 | 98 | typer, funcs:6 | src/stackops/scripts/python/helpers/helpers_repos/cloud_repo_sync_actions.py |  |
| `stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_archive` | `cli-helper` | `cli-helper` | `medium` | 4 | 109 | funcs:4 | src/stackops/scripts/python/helpers/helpers_repos/cloud_repo_sync_archive.py |  |
| `stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_conflicts` | `cli-helper` | `cli-helper` | `medium` | 5 | 96 | classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_repos/cloud_repo_sync_conflicts.py |  |
| `stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_git` | `cli` | `cli-module` | `high` | 3 | 158 | typer, classes:3, funcs:7 | src/stackops/scripts/python/helpers/helpers_repos/cloud_repo_sync_git.py |  |
| `stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_gpg` | `cli-helper` | `cli-helper` | `medium` | 2 | 20 | funcs:1 | src/stackops/scripts/python/helpers/helpers_repos/cloud_repo_sync_gpg.py |  |
| `stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_integration` | `cli` | `cli-module` | `high` | 2 | 162 | typer, classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_repos/cloud_repo_sync_integration.py |  |
| `stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_replacement` | `cli-helper` | `cli-helper` | `medium` | 1 | 101 | funcs:2 | src/stackops/scripts/python/helpers/helpers_repos/cloud_repo_sync_replacement.py |  |
| `stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_status` | `cli-helper` | `cli-helper` | `medium` | 3 | 100 | funcs:3 | src/stackops/scripts/python/helpers/helpers_repos/cloud_repo_sync_status.py |  |
| `stackops.scripts.python.helpers.helpers_repos.discovery` | `cli-helper` | `cli-helper` | `medium` | 2 | 27 | funcs:1 | src/stackops/scripts/python/helpers/helpers_repos/discovery.py |  |
| `stackops.scripts.python.helpers.helpers_repos.git_action` | `cli-helper` | `cli-helper` | `medium` | 1 | 143 | classes:1, funcs:6 | src/stackops/scripts/python/helpers/helpers_repos/git_action.py |  |
| `stackops.scripts.python.helpers.helpers_repos.guard_transport` | `cli-helper` | `cli-helper` | `medium` | 5 | 196 | funcs:2 | src/stackops/scripts/python/helpers/helpers_repos/guard_transport.py |  |
| `stackops.scripts.python.helpers.helpers_repos.local_status` | `cli-helper` | `cli-helper` | `medium` | 2 | 57 | classes:1, funcs:1 | src/stackops/scripts/python/helpers/helpers_repos/local_status.py |  |
| `stackops.scripts.python.helpers.helpers_repos.record` | `cli` | `cli-module` | `high` | 1 | 382 | typer, funcs:12 | src/stackops/scripts/python/helpers/helpers_repos/record.py |  |
| `stackops.scripts.python.helpers.helpers_repos.registration_sync` | `cli-helper` | `cli-helper` | `medium` | 1 | 31 | funcs:1 | src/stackops/scripts/python/helpers/helpers_repos/registration_sync.py |  |
| `stackops.scripts.python.helpers.helpers_repos.spec_store` | `cli-helper` | `cli-helper` | `medium` | 14 | 192 | classes:2, funcs:12 | src/stackops/scripts/python/helpers/helpers_repos/spec_store.py |  |
| `stackops.scripts.python.helpers.helpers_repos.sync` | `cli-helper` | `cli-helper` | `medium` | 1 | 50 | funcs:4 | src/stackops/scripts/python/helpers/helpers_repos/sync.py |  |
| `stackops.scripts.python.helpers.helpers_repos.sync_settings` | `cli-helper` | `cli-helper` | `medium` | 2 | 28 | funcs:1 | src/stackops/scripts/python/helpers/helpers_repos/sync_settings.py |  |
| `stackops.scripts.python.helpers.helpers_repos.update` | `cli-helper` | `cli-helper` | `medium` | 2 | 253 | classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_repos/update.py |  |
| `stackops.scripts.python.helpers.helpers_repos.version_capture` | `cli-helper` | `cli-helper` | `medium` | 3 | 109 | classes:1, funcs:5 | src/stackops/scripts/python/helpers/helpers_repos/version_capture.py |  |
| `stackops.scripts.python.helpers.helpers_repos.version_checkout` | `cli-helper` | `cli-helper` | `medium` | 1 | 206 | classes:1, funcs:9 | src/stackops/scripts/python/helpers/helpers_repos/version_checkout.py |  |
| `stackops.scripts.python.helpers.helpers_repos.version_constants` | `cli-helper` | `cli-helper` | `medium` | 3 | 7 | - | src/stackops/scripts/python/helpers/helpers_repos/version_constants.py |  |
| `stackops.scripts.python.helpers.helpers_repos.version_models` | `cli-helper` | `cli-helper` | `medium` | 6 | 58 | classes:8 | src/stackops/scripts/python/helpers/helpers_repos/version_models.py |  |
| `stackops.scripts.python.helpers.helpers_repos.version_paths` | `cli-helper` | `cli-helper` | `medium` | 3 | 23 | funcs:2 | src/stackops/scripts/python/helpers/helpers_repos/version_paths.py |  |
| `stackops.scripts.python.helpers.helpers_repos.version_status` | `cli-helper` | `cli-helper` | `medium` | 1 | 70 | funcs:4 | src/stackops/scripts/python/helpers/helpers_repos/version_status.py |  |
| `stackops.scripts.python.helpers.helpers_repos.version_store` | `cli-helper` | `cli-helper` | `medium` | 1 | 180 | classes:1, funcs:14 | src/stackops/scripts/python/helpers/helpers_repos/version_store.py |  |
| `stackops.scripts.python.helpers.helpers_search.ast_search` | `cli-helper` | `cli-helper` | `medium` | 2 | 138 | classes:1, funcs:9 | src/stackops/scripts/python/helpers/helpers_search/ast_search.py |  |
| `stackops.scripts.python.helpers.helpers_search.qr_code` | `cli-helper` | `cli-helper` | `medium` | 0 | 168 | funcs:3 | src/stackops/scripts/python/helpers/helpers_search/qr_code.py |  |
| `stackops.scripts.python.helpers.helpers_search.repo_rag` | `cli-helper` | `cli-helper` | `medium` | 0 | 325 | - | src/stackops/scripts/python/helpers/helpers_search/repo_rag.py |  |
| `stackops.scripts.python.helpers.helpers_search.script_help` | `cli-helper` | `cli-helper` | `medium` | 4 | 48 | funcs:1 | src/stackops/scripts/python/helpers/helpers_search/script_help.py |  |
| `stackops.scripts.python.helpers.helpers_search.semantic_search` | `cli-helper` | `cli-helper` | `medium` | 0 | 25 | - | src/stackops/scripts/python/helpers/helpers_search/semantic_search.py |  |
| `stackops.scripts.python.helpers.helpers_seek` | `package` | `package-marker` | `high` | 0 | 3 | - | src/stackops/scripts/python/helpers/helpers_seek/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_seek.json_search` | `cli-helper` | `cli-helper` | `medium` | 1 | 158 | classes:6, funcs:6 | src/stackops/scripts/python/helpers/helpers_seek/json_search.py |  |
| `stackops.scripts.python.helpers.helpers_seek.scripts_linux` | `package` | `package-marker` | `high` | 1 | 2 | - | src/stackops/scripts/python/helpers/helpers_seek/scripts_linux/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_seek.scripts_macos` | `package` | `package-marker` | `high` | 1 | 1 | - | src/stackops/scripts/python/helpers/helpers_seek/scripts_macos/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_seek.scripts_windows` | `package` | `package-marker` | `high` | 1 | 1 | - | src/stackops/scripts/python/helpers/helpers_seek/scripts_windows/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_seek.seek_impl` | `cli-helper` | `cli-helper` | `medium` | 1 | 410 | funcs:16 | src/stackops/scripts/python/helpers/helpers_seek/seek_impl.py |  |
| `stackops.scripts.python.helpers.helpers_seek.semantic` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/scripts/python/helpers/helpers_seek/semantic/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_seek.semantic.backend_ck` | `cli-helper` | `cli-helper` | `medium` | 1 | 64 | classes:2, funcs:2 | src/stackops/scripts/python/helpers/helpers_seek/semantic/backend_ck.py |  |
| `stackops.scripts.python.helpers.helpers_seek.semantic.backend_grepai` | `cli-helper` | `cli-helper` | `medium` | 1 | 139 | classes:5, funcs:4 | src/stackops/scripts/python/helpers/helpers_seek/semantic/backend_grepai.py |  |
| `stackops.scripts.python.helpers.helpers_seek.semantic.backend_names` | `cli-helper` | `cli-helper` | `medium` | 7 | 4 | - | src/stackops/scripts/python/helpers/helpers_seek/semantic/backend_names.py |  |
| `stackops.scripts.python.helpers.helpers_seek.semantic.backend_qmd` | `cli-helper` | `cli-helper` | `medium` | 1 | 123 | classes:1, funcs:3 | src/stackops/scripts/python/helpers/helpers_seek/semantic/backend_qmd.py |  |
| `stackops.scripts.python.helpers.helpers_seek.semantic.backend_semtools` | `cli-helper` | `cli-helper` | `medium` | 1 | 112 | classes:2, funcs:3 | src/stackops/scripts/python/helpers/helpers_seek/semantic/backend_semtools.py |  |
| `stackops.scripts.python.helpers.helpers_seek.semantic.command_runner` | `cli-helper` | `cli-helper` | `medium` | 4 | 36 | funcs:1 | src/stackops/scripts/python/helpers/helpers_seek/semantic/command_runner.py |  |
| `stackops.scripts.python.helpers.helpers_seek.semantic.constants` | `cli-helper` | `cli-helper` | `medium` | 9 | 33 | - | src/stackops/scripts/python/helpers/helpers_seek/semantic/constants.py |  |
| `stackops.scripts.python.helpers.helpers_seek.semantic.hit_selection` | `cli-helper` | `cli-helper` | `medium` | 2 | 73 | funcs:2 | src/stackops/scripts/python/helpers/helpers_seek/semantic/hit_selection.py |  |
| `stackops.scripts.python.helpers.helpers_seek.semantic.index_dirs` | `cli-helper` | `cli-helper` | `medium` | 2 | 9 | funcs:1 | src/stackops/scripts/python/helpers/helpers_seek/semantic/index_dirs.py |  |
| `stackops.scripts.python.helpers.helpers_seek.semantic.json_search` | `cli-helper` | `cli-helper` | `medium` | 1 | 47 | funcs:1 | src/stackops/scripts/python/helpers/helpers_seek/semantic/json_search.py |  |
| `stackops.scripts.python.helpers.helpers_seek.semantic.run_semantic_search` | `cli-helper` | `cli-helper` | `medium` | 2 | 74 | funcs:4 | src/stackops/scripts/python/helpers/helpers_seek/semantic/run_semantic_search.py |  |
| `stackops.scripts.python.helpers.helpers_seek.semantic.semantic_models` | `cli-helper` | `cli-helper` | `medium` | 10 | 35 | classes:3 | src/stackops/scripts/python/helpers/helpers_seek/semantic/semantic_models.py |  |
| `stackops.scripts.python.helpers.helpers_sessions` | `package` | `package-marker` | `high` | 3 | 0 | - | src/stackops/scripts/python/helpers/helpers_sessions/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._aoe_backend` | `cli-helper` | `cli-helper` | `medium` | 6 | 296 | funcs:23 | src/stackops/scripts/python/helpers/helpers_sessions/_aoe_backend.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._attach_common` | `cli-helper` | `cli-helper` | `medium` | 27 | 120 | funcs:9 | src/stackops/scripts/python/helpers/helpers_sessions/_attach_common.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._herdr_backend` | `cli-helper` | `cli-helper` | `medium` | 5 | 772 | classes:2, funcs:43 | src/stackops/scripts/python/helpers/helpers_sessions/_herdr_backend.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._herdr_backend_idle` | `cli-helper` | `cli-helper` | `medium` | 1 | 178 | funcs:8 | src/stackops/scripts/python/helpers/helpers_sessions/_herdr_backend_idle.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._tmux_backend` | `cli-helper` | `cli-helper` | `medium` | 7 | 316 | funcs:12 | src/stackops/scripts/python/helpers/helpers_sessions/_tmux_backend.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._tmux_backend_options` | `cli-helper` | `cli-helper` | `medium` | 1 | 209 | funcs:10 | src/stackops/scripts/python/helpers/helpers_sessions/_tmux_backend_options.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._tmux_backend_preview` | `cli-helper` | `cli-helper` | `medium` | 5 | 334 | classes:1, funcs:15 | src/stackops/scripts/python/helpers/helpers_sessions/_tmux_backend_preview.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._tmux_backend_process_commands` | `cli-helper` | `cli-helper` | `medium` | 1 | 83 | funcs:5 | src/stackops/scripts/python/helpers/helpers_sessions/_tmux_backend_process_commands.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._tmux_backend_processes` | `cli-helper` | `cli-helper` | `medium` | 3 | 78 | funcs:4 | src/stackops/scripts/python/helpers/helpers_sessions/_tmux_backend_processes.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._tmux_process_inspection` | `cli-helper` | `cli-helper` | `medium` | 5 | 158 | classes:1, funcs:11 | src/stackops/scripts/python/helpers/helpers_sessions/_tmux_process_inspection.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._tuios_backend` | `cli-helper` | `cli-helper` | `medium` | 6 | 167 | funcs:7 | src/stackops/scripts/python/helpers/helpers_sessions/_tuios_backend.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._tuios_backend_idle` | `cli-helper` | `cli-helper` | `medium` | 5 | 51 | funcs:2 | src/stackops/scripts/python/helpers/helpers_sessions/_tuios_backend_idle.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._tuios_backend_kill` | `cli-helper` | `cli-helper` | `medium` | 1 | 80 | funcs:1 | src/stackops/scripts/python/helpers/helpers_sessions/_tuios_backend_kill.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._tuios_backend_models` | `cli-helper` | `cli-helper` | `medium` | 10 | 46 | classes:4 | src/stackops/scripts/python/helpers/helpers_sessions/_tuios_backend_models.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._tuios_backend_preview` | `cli-helper` | `cli-helper` | `medium` | 2 | 31 | funcs:3 | src/stackops/scripts/python/helpers/helpers_sessions/_tuios_backend_preview.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._tuios_backend_state` | `cli-helper` | `cli-helper` | `medium` | 18 | 136 | funcs:9 | src/stackops/scripts/python/helpers/helpers_sessions/_tuios_backend_state.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._zellij_backend` | `cli-helper` | `cli-helper` | `medium` | 5 | 132 | funcs:5 | src/stackops/scripts/python/helpers/helpers_sessions/_zellij_backend.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._zellij_backend_idle` | `cli-helper` | `cli-helper` | `medium` | 5 | 44 | funcs:2 | src/stackops/scripts/python/helpers/helpers_sessions/_zellij_backend_idle.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._zellij_backend_kill` | `cli-helper` | `cli-helper` | `medium` | 1 | 87 | funcs:1 | src/stackops/scripts/python/helpers/helpers_sessions/_zellij_backend_kill.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._zellij_backend_models` | `cli-helper` | `cli-helper` | `medium` | 9 | 33 | classes:3 | src/stackops/scripts/python/helpers/helpers_sessions/_zellij_backend_models.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._zellij_backend_preview` | `cli-helper` | `cli-helper` | `medium` | 2 | 37 | funcs:4 | src/stackops/scripts/python/helpers/helpers_sessions/_zellij_backend_preview.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._zellij_backend_state` | `cli-helper` | `cli-helper` | `medium` | 19 | 121 | funcs:9 | src/stackops/scripts/python/helpers/helpers_sessions/_zellij_backend_state.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.attach_impl` | `cli-helper` | `cli-helper` | `medium` | 2 | 143 | funcs:9 | src/stackops/scripts/python/helpers/helpers_sessions/attach_impl.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.herdr_export` | `cli-helper` | `cli-helper` | `medium` | 1 | 178 | funcs:9 | src/stackops/scripts/python/helpers/helpers_sessions/herdr_export.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.herdr_export_selection` | `cli-helper` | `cli-helper` | `medium` | 1 | 151 | funcs:8 | src/stackops/scripts/python/helpers/helpers_sessions/herdr_export_selection.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.herdr_export_source` | `cli-helper` | `cli-helper` | `medium` | 4 | 142 | funcs:16 | src/stackops/scripts/python/helpers/helpers_sessions/herdr_export_source.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.kill_exact_target` | `cli-helper` | `cli-helper` | `medium` | 1 | 51 | funcs:1 | src/stackops/scripts/python/helpers/helpers_sessions/kill_exact_target.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.kill_impl` | `cli-helper` | `cli-helper` | `medium` | 1 | 153 | funcs:3 | src/stackops/scripts/python/helpers/helpers_sessions/kill_impl.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.kill_models` | `cli-helper` | `cli-helper` | `medium` | 14 | 8 | classes:1 | src/stackops/scripts/python/helpers/helpers_sessions/kill_models.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.session_trace_aoe` | `cli-helper` | `cli-helper` | `medium` | 2 | 372 | funcs:18 | src/stackops/scripts/python/helpers/helpers_sessions/session_trace_aoe.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.session_trace_herdr` | `cli-helper` | `cli-helper` | `medium` | 2 | 438 | funcs:27 | src/stackops/scripts/python/helpers/helpers_sessions/session_trace_herdr.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.session_trace_json` | `cli` | `cli-module` | `high` | 1 | 54 | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_sessions/session_trace_json.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.session_trace_kill` | `cli-helper` | `cli-helper` | `medium` | 2 | 154 | classes:2, funcs:3 | src/stackops/scripts/python/helpers/helpers_sessions/session_trace_kill.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.session_trace_models` | `cli-helper` | `cli-helper` | `medium` | 12 | 89 | classes:3, funcs:2 | src/stackops/scripts/python/helpers/helpers_sessions/session_trace_models.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.session_trace_runner` | `cli` | `cli-module` | `high` | 2 | 187 | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_sessions/session_trace_runner.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.session_trace_selection` | `cli-helper` | `cli-helper` | `medium` | 2 | 104 | funcs:5 | src/stackops/scripts/python/helpers/helpers_sessions/session_trace_selection.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.session_trace_tmux` | `cli-helper` | `cli-helper` | `medium` | 3 | 150 | funcs:4 | src/stackops/scripts/python/helpers/helpers_sessions/session_trace_tmux.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.session_trace_tuios` | `cli-helper` | `cli-helper` | `medium` | 2 | 111 | funcs:3 | src/stackops/scripts/python/helpers/helpers_sessions/session_trace_tuios.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.session_trace_zellij` | `cli-helper` | `cli-helper` | `medium` | 4 | 101 | funcs:3 | src/stackops/scripts/python/helpers/helpers_sessions/session_trace_zellij.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_aoe_impl` | `cli-helper` | `cli-helper` | `medium` | 1 | 181 | classes:2, funcs:7 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_aoe_impl.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_cli_common` | `cli` | `cli-module` | `high` | 3 | 152 | typer, funcs:5 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_cli_common.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_cli_run` | `cli` | `cli-module` | `high` | 1 | 139 | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_cli_run.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_cli_run_all` | `cli` | `cli-module` | `high` | 1 | 83 | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_cli_run_all.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_dynamic` | `cli-helper` | `cli-helper` | `medium` | 1 | 282 | funcs:7 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_dynamic.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_dynamic_display` | `cli-helper` | `cli-helper` | `medium` | 5 | 188 | classes:3, funcs:11 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_dynamic_display.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_dynamic_tmux` | `cli-helper` | `cli-helper` | `medium` | 1 | 107 | funcs:9 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_dynamic_tmux.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_dynamic_tuios` | `cli-helper` | `cli-helper` | `medium` | 1 | 61 | funcs:5 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_dynamic_tuios.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_dynamic_zellij` | `cli-helper` | `cli-helper` | `medium` | 1 | 52 | funcs:4 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_dynamic_zellij.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_herdr` | `cli` | `cli-module` | `high` | 1 | 293 | typer, classes:3, funcs:10 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_herdr.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_impl` | `cli-helper` | `cli-helper` | `medium` | 3 | 168 | funcs:3 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_impl.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_layout_source` | `cli` | `cli-module` | `high` | 6 | 149 | typer, classes:1, funcs:3 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_layout_source.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_layout_tabs` | `cli` | `cli-module` | `high` | 1 | 113 | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_layout_tabs.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_multiprocess` | `cli` | `cli-module` | `high` | 1 | 77 | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_multiprocess.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_test_layouts` | `cli-helper` | `cli-helper` | `medium` | 1 | 163 | classes:1, funcs:5 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_test_layouts.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_trace` | `cli` | `cli-module` | `high` | 1 | 177 | typer, __all__, funcs:7 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_trace.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_trace_layout` | `cli-helper` | `cli-helper` | `medium` | 1 | 93 | classes:1, funcs:2 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_trace_layout.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_trace_render` | `cli-helper` | `cli-helper` | `medium` | 1 | 383 | funcs:16 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_trace_render.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_tuios` | `cli` | `cli-module` | `high` | 2 | 131 | typer, funcs:2 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_tuios.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_tuios_commands` | `cli-helper` | `cli-helper` | `medium` | 4 | 87 | funcs:4 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_tuios_commands.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_zellij` | `cli` | `cli-module` | `high` | 2 | 119 | typer, funcs:3 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_zellij.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_zellij_commands` | `cli-helper` | `cli-helper` | `medium` | 4 | 38 | funcs:4 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_zellij_commands.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_zellij_constants` | `cli-helper` | `cli-helper` | `medium` | 2 | 2 | - | src/stackops/scripts/python/helpers/helpers_sessions/sessions_zellij_constants.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_zellij_layout` | `cli-helper` | `cli-helper` | `medium` | 3 | 111 | funcs:6 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_zellij_layout.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.terminal_cli_helpers` | `cli` | `cli-module` | `high` | 4 | 82 | typer, funcs:4 | src/stackops/scripts/python/helpers/helpers_sessions/terminal_cli_helpers.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.terminal_export` | `cli-helper` | `cli-helper` | `medium` | 3 | 109 | funcs:3 | src/stackops/scripts/python/helpers/helpers_sessions/terminal_export.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.terminal_export_settings` | `cli-helper` | `cli-helper` | `medium` | 1 | 133 | classes:1, funcs:5 | src/stackops/scripts/python/helpers/helpers_sessions/terminal_export_settings.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.terminal_run_command` | `cli` | `cli-module` | `high` | 1 | 21 | typer, classes:1 | src/stackops/scripts/python/helpers/helpers_sessions/terminal_run_command.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.terminal_summary_json` | `cli-helper` | `cli-helper` | `medium` | 2 | 160 | funcs:3 | src/stackops/scripts/python/helpers/helpers_sessions/terminal_summary_json.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.tmux_export` | `cli-helper` | `cli-helper` | `medium` | 2 | 248 | funcs:12 | src/stackops/scripts/python/helpers/helpers_sessions/tmux_export.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.tmux_export_constants` | `cli-helper` | `cli-helper` | `medium` | 6 | 12 | - | src/stackops/scripts/python/helpers/helpers_sessions/tmux_export_constants.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.tuios_export` | `cli-helper` | `cli-helper` | `medium` | 1 | 87 | funcs:4 | src/stackops/scripts/python/helpers/helpers_sessions/tuios_export.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.tuios_summary` | `cli` | `cli-module` | `high` | 1 | 83 | typer, funcs:2 | src/stackops/scripts/python/helpers/helpers_sessions/tuios_summary.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.utils` | `cli-helper` | `cli-helper` | `medium` | 1 | 82 | funcs:2 | src/stackops/scripts/python/helpers/helpers_sessions/utils.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.zellij_attach` | `cli-helper` | `cli-helper` | `medium` | 0 | 59 | main, __main__, funcs:3 | src/stackops/scripts/python/helpers/helpers_sessions/zellij_attach.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.zellij_export` | `cli-helper` | `cli-helper` | `medium` | 1 | 95 | funcs:4 | src/stackops/scripts/python/helpers/helpers_sessions/zellij_export.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.zellij_summary` | `cli` | `cli-module` | `high` | 1 | 81 | typer, funcs:3 | src/stackops/scripts/python/helpers/helpers_sessions/zellij_summary.py |  |
| `stackops.scripts.python.helpers.helpers_utils.autostart` | `cli` | `cli-module` | `high` | 2 | 98 | typer, funcs:3 | src/stackops/scripts/python/helpers/helpers_utils/autostart.py |  |
| `stackops.scripts.python.helpers.helpers_utils.autostart_apply` | `cli-helper` | `cli-helper` | `medium` | 2 | 94 | classes:3, funcs:2 | src/stackops/scripts/python/helpers/helpers_utils/autostart_apply.py |  |
| `stackops.scripts.python.helpers.helpers_utils.autostart_common` | `cli-helper` | `cli-helper` | `medium` | 11 | 129 | classes:1, funcs:2 | src/stackops/scripts/python/helpers/helpers_utils/autostart_common.py |  |
| `stackops.scripts.python.helpers.helpers_utils.autostart_entry` | `cli-helper` | `cli-helper` | `medium` | 6 | 156 | classes:3, funcs:4 | src/stackops/scripts/python/helpers/helpers_utils/autostart_entry.py |  |
| `stackops.scripts.python.helpers.helpers_utils.autostart_layout` | `cli-helper` | `cli-helper` | `medium` | 2 | 32 | funcs:2 | src/stackops/scripts/python/helpers/helpers_utils/autostart_layout.py |  |
| `stackops.scripts.python.helpers.helpers_utils.autostart_linux` | `cli-helper` | `cli-helper` | `medium` | 2 | 185 | funcs:9 | src/stackops/scripts/python/helpers/helpers_utils/autostart_linux.py |  |
| `stackops.scripts.python.helpers.helpers_utils.autostart_macos` | `cli-helper` | `cli-helper` | `medium` | 2 | 145 | funcs:4 | src/stackops/scripts/python/helpers/helpers_utils/autostart_macos.py |  |
| `stackops.scripts.python.helpers.helpers_utils.autostart_macos_login` | `cli` | `cli-module` | `high` | 2 | 68 | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_utils/autostart_macos_login.py |  |
| `stackops.scripts.python.helpers.helpers_utils.autostart_remembered` | `cli-helper` | `cli-helper` | `medium` | 3 | 119 | classes:1, funcs:5 | src/stackops/scripts/python/helpers/helpers_utils/autostart_remembered.py |  |
| `stackops.scripts.python.helpers.helpers_utils.autostart_script` | `cli-helper` | `cli-helper` | `medium` | 2 | 42 | funcs:2 | src/stackops/scripts/python/helpers/helpers_utils/autostart_script.py |  |
| `stackops.scripts.python.helpers.helpers_utils.autostart_script_cli` | `cli` | `cli-module` | `high` | 1 | 120 | typer, funcs:3 | src/stackops/scripts/python/helpers/helpers_utils/autostart_script_cli.py |  |
| `stackops.scripts.python.helpers.helpers_utils.autostart_script_constants` | `cli-helper` | `cli-helper` | `medium` | 4 | 14 | - | src/stackops/scripts/python/helpers/helpers_utils/autostart_script_constants.py |  |
| `stackops.scripts.python.helpers.helpers_utils.autostart_script_entries` | `cli-helper` | `cli-helper` | `medium` | 3 | 50 | funcs:3 | src/stackops/scripts/python/helpers/helpers_utils/autostart_script_entries.py |  |
| `stackops.scripts.python.helpers.helpers_utils.autostart_windows` | `cli-helper` | `cli-helper` | `medium` | 1 | 55 | classes:1, funcs:1 | src/stackops/scripts/python/helpers/helpers_utils/autostart_windows.py |  |
| `stackops.scripts.python.helpers.helpers_utils.clean_drive_catalog` | `cli-helper` | `cli-helper` | `medium` | 1 | 38 | - | src/stackops/scripts/python/helpers/helpers_utils/clean_drive_catalog.py |  |
| `stackops.scripts.python.helpers.helpers_utils.clean_drive_catalog_dev` | `cli-helper` | `cli-helper` | `medium` | 1 | 127 | - | src/stackops/scripts/python/helpers/helpers_utils/clean_drive_catalog_dev.py |  |
| `stackops.scripts.python.helpers.helpers_utils.clean_drive_catalog_stackops` | `cli-helper` | `cli-helper` | `medium` | 1 | 118 | - | src/stackops/scripts/python/helpers/helpers_utils/clean_drive_catalog_stackops.py |  |
| `stackops.scripts.python.helpers.helpers_utils.clean_drive_catalog_system` | `cli-helper` | `cli-helper` | `medium` | 1 | 151 | - | src/stackops/scripts/python/helpers/helpers_utils/clean_drive_catalog_system.py |  |
| `stackops.scripts.python.helpers.helpers_utils.clean_drive_cli` | `cli` | `cli-module` | `high` | 1 | 115 | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_utils/clean_drive_cli.py |  |
| `stackops.scripts.python.helpers.helpers_utils.clean_drive_constants` | `cli-helper` | `cli-helper` | `medium` | 10 | 30 | - | src/stackops/scripts/python/helpers/helpers_utils/clean_drive_constants.py |  |
| `stackops.scripts.python.helpers.helpers_utils.clean_drive_details` | `cli-helper` | `cli-helper` | `medium` | 3 | 149 | classes:7, funcs:5 | src/stackops/scripts/python/helpers/helpers_utils/clean_drive_details.py |  |
| `stackops.scripts.python.helpers.helpers_utils.clean_drive_execute` | `cli-helper` | `cli-helper` | `medium` | 1 | 99 | funcs:5 | src/stackops/scripts/python/helpers/helpers_utils/clean_drive_execute.py |  |
| `stackops.scripts.python.helpers.helpers_utils.clean_drive_interactive` | `cli-helper` | `cli-helper` | `medium` | 1 | 38 | funcs:2 | src/stackops/scripts/python/helpers/helpers_utils/clean_drive_interactive.py |  |
| `stackops.scripts.python.helpers.helpers_utils.clean_drive_models` | `cli-helper` | `cli-helper` | `medium` | 15 | 170 | classes:18 | src/stackops/scripts/python/helpers/helpers_utils/clean_drive_models.py |  |
| `stackops.scripts.python.helpers.helpers_utils.clean_drive_paths` | `cli-helper` | `cli-helper` | `medium` | 3 | 78 | funcs:4 | src/stackops/scripts/python/helpers/helpers_utils/clean_drive_paths.py |  |
| `stackops.scripts.python.helpers.helpers_utils.clean_drive_plans` | `cli-helper` | `cli-helper` | `medium` | 4 | 120 | funcs:10 | src/stackops/scripts/python/helpers/helpers_utils/clean_drive_plans.py |  |
| `stackops.scripts.python.helpers.helpers_utils.clean_drive_projects` | `cli-helper` | `cli-helper` | `medium` | 1 | 44 | funcs:1 | src/stackops/scripts/python/helpers/helpers_utils/clean_drive_projects.py |  |
| `stackops.scripts.python.helpers.helpers_utils.clean_drive_render` | `cli-helper` | `cli-helper` | `medium` | 2 | 192 | classes:5, funcs:10 | src/stackops/scripts/python/helpers/helpers_utils/clean_drive_render.py |  |
| `stackops.scripts.python.helpers.helpers_utils.clean_drive_scan` | `cli-helper` | `cli-helper` | `medium` | 4 | 174 | funcs:10 | src/stackops/scripts/python/helpers/helpers_utils/clean_drive_scan.py |  |
| `stackops.scripts.python.helpers.helpers_utils.clean_drive_usage` | `cli-helper` | `cli-helper` | `medium` | 4 | 110 | funcs:7 | src/stackops/scripts/python/helpers/helpers_utils/clean_drive_usage.py |  |
| `stackops.scripts.python.helpers.helpers_utils.environment_html` | `cli-helper` | `cli-helper` | `medium` | 2 | 97 | classes:3, funcs:3 | src/stackops/scripts/python/helpers/helpers_utils/environment_html.py |  |
| `stackops.scripts.python.helpers.helpers_utils.file_utils_app` | `cli` | `cli-module` | `high` | 1 | 309 | typer, typer-app, cli-registration, get_app, funcs:8 | src/stackops/scripts/python/helpers/helpers_utils/file_utils_app.py |  |
| `stackops.scripts.python.helpers.helpers_utils.machine_utils_app` | `cli` | `cli-module` | `high` | 1 | 311 | typer, typer-app, cli-registration, get_app, classes:1, funcs:7 | src/stackops/scripts/python/helpers/helpers_utils/machine_utils_app.py |  |
| `stackops.scripts.python.helpers.helpers_utils.path_helper` | `cli` | `cli-module` | `high` | 3 | 245 | typer, funcs:9 | src/stackops/scripts/python/helpers/helpers_utils/path_helper.py |  |
| `stackops.scripts.python.helpers.helpers_utils.path_reference_validation` | `cli-helper` | `cli-helper` | `medium` | 1 | 324 | classes:5, funcs:14 | src/stackops/scripts/python/helpers/helpers_utils/path_reference_validation.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pdf` | `cli` | `cli-module` | `high` | 1 | 100 | typer, funcs:2 | src/stackops/scripts/python/helpers/helpers_utils/pdf.py |  |
| `stackops.scripts.python.helpers.helpers_utils.process_models` | `cli-helper` | `cli-helper` | `medium` | 4 | 113 | classes:4, funcs:2 | src/stackops/scripts/python/helpers/helpers_utils/process_models.py |  |
| `stackops.scripts.python.helpers.helpers_utils.process_termination` | `cli-helper` | `cli-helper` | `medium` | 3 | 35 | classes:1, funcs:2 | src/stackops/scripts/python/helpers/helpers_utils/process_termination.py |  |
| `stackops.scripts.python.helpers.helpers_utils.processes` | `cli-helper` | `cli-helper` | `medium` | 1 | 264 | __main__, classes:2, funcs:3 | src/stackops/scripts/python/helpers/helpers_utils/processes.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_app` | `cli` | `cli-module` | `high` | 1 | 62 | typer, typer-app, cli-registration, get_app, funcs:1 | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_app.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_commands_check` | `cli` | `cli-module` | `high` | 1 | 168 | typer, funcs:2 | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_commands_check.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_commands_deps` | `cli` | `cli-module` | `high` | 1 | 160 | typer, funcs:6 | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_commands_deps.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_commands_maintenance` | `cli` | `cli-module` | `high` | 1 | 115 | typer, funcs:2 | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_commands_maintenance.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_commands_setup` | `cli` | `cli-module` | `high` | 1 | 112 | typer, funcs:2 | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_commands_setup.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps` | `cli-helper` | `cli-helper` | `medium` | 1 | 173 | funcs:11 | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_deps.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_graph` | `cli-helper` | `cli-helper` | `medium` | 3 | 110 | funcs:6 | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_deps_graph.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_models` | `cli-helper` | `cli-helper` | `medium` | 6 | 48 | classes:6 | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_deps_models.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_options` | `cli-helper` | `cli-helper` | `medium` | 5 | 6 | - | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_deps_options.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_parse` | `cli-helper` | `cli-helper` | `medium` | 1 | 92 | funcs:5 | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_deps_parse.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_render` | `cli-helper` | `cli-helper` | `medium` | 1 | 153 | funcs:8 | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_deps_render.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_render_css` | `cli-helper` | `cli-helper` | `medium` | 1 | 122 | - | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_deps_render_css.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_render_graph_css` | `cli-helper` | `cli-helper` | `medium` | 1 | 118 | - | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_deps_render_graph_css.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_render_js` | `cli-helper` | `cli-helper` | `medium` | 1 | 26 | - | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_deps_render_js.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_render_js_bootstrap` | `cli-helper` | `cli-helper` | `medium` | 1 | 52 | - | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_deps_render_js_bootstrap.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_render_js_interaction` | `cli-helper` | `cli-helper` | `medium` | 1 | 150 | - | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_deps_render_js_interaction.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_render_js_layout` | `cli-helper` | `cli-helper` | `medium` | 1 | 59 | - | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_deps_render_js_layout.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_render_js_shared` | `cli-helper` | `cli-helper` | `medium` | 1 | 36 | - | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_deps_render_js_shared.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_render_js_svg` | `cli-helper` | `cli-helper` | `medium` | 1 | 111 | - | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_deps_render_js_svg.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_runner` | `cli-helper` | `cli-helper` | `medium` | 1 | 73 | funcs:3 | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_deps_runner.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_helpers` | `cli-helper` | `cli-helper` | `medium` | 2 | 143 | funcs:6 | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_helpers.py |  |
| `stackops.scripts.python.helpers.helpers_utils.python` | `cli` | `cli-module` | `high` | 2 | 178 | typer, __main__, funcs:10 | src/stackops/scripts/python/helpers/helpers_utils/python.py |  |
| `stackops.scripts.python.helpers.helpers_utils.python_env` | `api-or-cli-helper` | `manual-review` | `low` | 2 | 27 | api-doc, funcs:2 | src/stackops/scripts/python/helpers/helpers_utils/python_env.py |  |
| `stackops.scripts.python.helpers.helpers_utils.python_init` | `cli` | `cli-module` | `high` | 1 | 88 | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_utils/python_init.py |  |
| `stackops.scripts.python.helpers.helpers_utils.read_db_cli_tui` | `cli-helper` | `cli-helper` | `medium` | 1 | 37 | funcs:1 | src/stackops/scripts/python/helpers/helpers_utils/read_db_cli_tui.py |  |
| `stackops.scripts.python.helpers.helpers_utils.read_db_cli_tui_backend` | `cli` | `cli-module` | `high` | 3 | 391 | typer, funcs:22 | src/stackops/scripts/python/helpers/helpers_utils/read_db_cli_tui_backend.py |  |
| `stackops.scripts.python.helpers.helpers_utils.scrape` | `cli` | `cli-module` | `high` | 1 | 93 | typer, funcs:3 | src/stackops/scripts/python/helpers/helpers_utils/scrape.py |  |
| `stackops.scripts.python.helpers.helpers_utils.specs` | `cli-helper` | `cli-helper` | `medium` | 1 | 312 | main, __main__, funcs:8 | src/stackops/scripts/python/helpers/helpers_utils/specs.py |  |
| `stackops.scripts.python.helpers.helpers_utils.surya` | `cli-helper` | `cli-helper` | `medium` | 1 | 99 | funcs:3 | src/stackops/scripts/python/helpers/helpers_utils/surya.py |  |
| `stackops.scripts.python.helpers.helpers_utils.upgrade_packages` | `cli-helper` | `cli-helper` | `medium` | 1 | 369 | classes:2, funcs:14 | src/stackops/scripts/python/helpers/helpers_utils/upgrade_packages.py |  |
| `stackops.scripts.python.helpers.helpers_utils.window` | `cli` | `cli-module` | `high` | 1 | 130 | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_utils/window.py |  |
| `stackops.scripts.python.helpers.helpers_webui.access_guard` | `cli-helper` | `cli-helper` | `medium` | 1 | 83 | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/access_guard.py |  |
| `stackops.scripts.python.helpers.helpers_webui.capture` | `cli-helper` | `cli-helper` | `medium` | 1 | 69 | classes:2, funcs:3 | src/stackops/scripts/python/helpers/helpers_webui/capture.py |  |
| `stackops.scripts.python.helpers.helpers_webui.catalog` | `cli` | `cli-module` | `high` | 1 | 141 | typer, typer-app, cli-registration, classes:3, funcs:2 | src/stackops/scripts/python/helpers/helpers_webui/catalog.py |  |
| `stackops.scripts.python.helpers.helpers_webui.cli_webui` | `cli` | `cli-module` | `high` | 1 | 39 | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/cli_webui.py |  |
| `stackops.scripts.python.helpers.helpers_webui.constants` | `cli-helper` | `cli-helper` | `medium` | 26 | 207 | - | src/stackops/scripts/python/helpers/helpers_webui/constants.py |  |
| `stackops.scripts.python.helpers.helpers_webui.dotfiles_constants` | `cli-helper` | `cli-helper` | `medium` | 5 | 22 | - | src/stackops/scripts/python/helpers/helpers_webui/dotfiles_constants.py |  |
| `stackops.scripts.python.helpers.helpers_webui.dotfiles_export_plan` | `cli-helper` | `cli-helper` | `medium` | 1 | 107 | classes:4, funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/dotfiles_export_plan.py |  |
| `stackops.scripts.python.helpers.helpers_webui.dotfiles_import_inspect` | `cli-helper` | `cli-helper` | `medium` | 1 | 112 | classes:2, funcs:3 | src/stackops/scripts/python/helpers/helpers_webui/dotfiles_import_inspect.py |  |
| `stackops.scripts.python.helpers.helpers_webui.dotfiles_import_state` | `cli-helper` | `cli-helper` | `medium` | 1 | 47 | classes:1, funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/dotfiles_import_state.py |  |
| `stackops.scripts.python.helpers.helpers_webui.dotfiles_model` | `cli-helper` | `cli-helper` | `medium` | 5 | 36 | classes:2, funcs:2 | src/stackops/scripts/python/helpers/helpers_webui/dotfiles_model.py |  |
| `stackops.scripts.python.helpers.helpers_webui.dotfiles_register_check` | `cli-helper` | `cli-helper` | `medium` | 1 | 153 | classes:4, funcs:3 | src/stackops/scripts/python/helpers/helpers_webui/dotfiles_register_check.py |  |
| `stackops.scripts.python.helpers.helpers_webui.dotfiles_routes` | `cli-helper` | `cli-helper` | `medium` | 1 | 84 | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/dotfiles_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.feature_routes` | `cli-helper` | `cli-helper` | `medium` | 1 | 43 | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/feature_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.field_choice_keywords` | `cli-helper` | `cli-helper` | `medium` | 1 | 48 | classes:1, funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/field_choice_keywords.py |  |
| `stackops.scripts.python.helpers.helpers_webui.field_choices` | `cli-helper` | `cli-helper` | `medium` | 1 | 196 | classes:1, funcs:8 | src/stackops/scripts/python/helpers/helpers_webui/field_choices.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_autostart_actions` | `cli-helper` | `cli-helper` | `medium` | 2 | 106 | funcs:7 | src/stackops/scripts/python/helpers/helpers_webui/machine_autostart_actions.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_autostart_constants` | `cli-helper` | `cli-helper` | `medium` | 11 | 98 | - | src/stackops/scripts/python/helpers/helpers_webui/machine_autostart_constants.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_autostart_detail` | `cli-helper` | `cli-helper` | `medium` | 2 | 78 | funcs:5 | src/stackops/scripts/python/helpers/helpers_webui/machine_autostart_detail.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_autostart_launchd` | `cli-helper` | `cli-helper` | `medium` | 3 | 113 | classes:3, funcs:7 | src/stackops/scripts/python/helpers/helpers_webui/machine_autostart_launchd.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_autostart_linux` | `cli-helper` | `cli-helper` | `medium` | 2 | 169 | funcs:7 | src/stackops/scripts/python/helpers/helpers_webui/machine_autostart_linux.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_autostart_linux_actions` | `cli-helper` | `cli-helper` | `medium` | 1 | 61 | funcs:3 | src/stackops/scripts/python/helpers/helpers_webui/machine_autostart_linux_actions.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_autostart_login_items` | `cli-helper` | `cli-helper` | `medium` | 1 | 57 | funcs:3 | src/stackops/scripts/python/helpers/helpers_webui/machine_autostart_login_items.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_autostart_macos` | `cli-helper` | `cli-helper` | `medium` | 3 | 174 | funcs:6 | src/stackops/scripts/python/helpers/helpers_webui/machine_autostart_macos.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_autostart_model` | `cli-helper` | `cli-helper` | `medium` | 11 | 79 | classes:6 | src/stackops/scripts/python/helpers/helpers_webui/machine_autostart_model.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_autostart_naming` | `cli-helper` | `cli-helper` | `medium` | 1 | 38 | funcs:3 | src/stackops/scripts/python/helpers/helpers_webui/machine_autostart_naming.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_autostart_read` | `cli-helper` | `cli-helper` | `medium` | 1 | 73 | funcs:2 | src/stackops/scripts/python/helpers/helpers_webui/machine_autostart_read.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_autostart_routes` | `cli-helper` | `cli-helper` | `medium` | 1 | 178 | funcs:2 | src/stackops/scripts/python/helpers/helpers_webui/machine_autostart_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_autostart_scripts` | `cli-helper` | `cli-helper` | `medium` | 1 | 149 | classes:6, funcs:7 | src/stackops/scripts/python/helpers/helpers_webui/machine_autostart_scripts.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_autostart_windows` | `cli-helper` | `cli-helper` | `medium` | 2 | 126 | funcs:5 | src/stackops/scripts/python/helpers/helpers_webui/machine_autostart_windows.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_devices_actions` | `cli-helper` | `cli-helper` | `medium` | 1 | 89 | funcs:5 | src/stackops/scripts/python/helpers/helpers_webui/machine_devices_actions.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_devices_linux` | `cli-helper` | `cli-helper` | `medium` | 1 | 80 | funcs:3 | src/stackops/scripts/python/helpers/helpers_webui/machine_devices_linux.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_devices_macos` | `cli-helper` | `cli-helper` | `medium` | 1 | 115 | funcs:3 | src/stackops/scripts/python/helpers/helpers_webui/machine_devices_macos.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_devices_model` | `cli-helper` | `cli-helper` | `medium` | 8 | 71 | classes:5 | src/stackops/scripts/python/helpers/helpers_webui/machine_devices_model.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_devices_mounts` | `cli-helper` | `cli-helper` | `medium` | 6 | 125 | classes:2, funcs:5 | src/stackops/scripts/python/helpers/helpers_webui/machine_devices_mounts.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_devices_read` | `cli-helper` | `cli-helper` | `medium` | 2 | 35 | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/machine_devices_read.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_devices_records` | `cli-helper` | `cli-helper` | `medium` | 3 | 45 | funcs:5 | src/stackops/scripts/python/helpers/helpers_webui/machine_devices_records.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_devices_routes` | `cli-helper` | `cli-helper` | `medium` | 1 | 53 | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/machine_devices_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_devices_windows` | `cli-helper` | `cli-helper` | `medium` | 1 | 42 | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/machine_devices_windows.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_environment_routes` | `cli-helper` | `cli-helper` | `medium` | 1 | 29 | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/machine_environment_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_mount_constants` | `cli-helper` | `cli-helper` | `medium` | 5 | 28 | - | src/stackops/scripts/python/helpers/helpers_webui/machine_mount_constants.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_mount_devices` | `cli-helper` | `cli-helper` | `medium` | 1 | 49 | funcs:2 | src/stackops/scripts/python/helpers/helpers_webui/machine_mount_devices.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_mount_linux` | `cli-helper` | `cli-helper` | `medium` | 1 | 98 | classes:1, funcs:3 | src/stackops/scripts/python/helpers/helpers_webui/machine_mount_linux.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_mount_macos` | `cli-helper` | `cli-helper` | `medium` | 1 | 65 | classes:1, funcs:3 | src/stackops/scripts/python/helpers/helpers_webui/machine_mount_macos.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_mount_model` | `cli-helper` | `cli-helper` | `medium` | 6 | 108 | classes:4, funcs:3 | src/stackops/scripts/python/helpers/helpers_webui/machine_mount_model.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_mount_places` | `cli-helper` | `cli-helper` | `medium` | 1 | 53 | classes:1, funcs:2 | src/stackops/scripts/python/helpers/helpers_webui/machine_mount_places.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_mount_routes` | `cli-helper` | `cli-helper` | `medium` | 1 | 35 | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/machine_mount_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_mount_windows` | `cli-helper` | `cli-helper` | `medium` | 1 | 35 | funcs:2 | src/stackops/scripts/python/helpers/helpers_webui/machine_mount_windows.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_processes_detail` | `cli-helper` | `cli-helper` | `medium` | 2 | 91 | classes:3, funcs:3 | src/stackops/scripts/python/helpers/helpers_webui/machine_processes_detail.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_processes_routes` | `cli-helper` | `cli-helper` | `medium` | 1 | 48 | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/machine_processes_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_processes_rows` | `cli-helper` | `cli-helper` | `medium` | 2 | 107 | classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_webui/machine_processes_rows.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_processes_scan` | `cli-helper` | `cli-helper` | `medium` | 1 | 132 | classes:3, funcs:5 | src/stackops/scripts/python/helpers/helpers_webui/machine_processes_scan.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_processes_stop` | `cli-helper` | `cli-helper` | `medium` | 2 | 103 | classes:3, funcs:4 | src/stackops/scripts/python/helpers/helpers_webui/machine_processes_stop.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_update_checkout` | `cli-helper` | `cli-helper` | `medium` | 2 | 135 | classes:2, funcs:5 | src/stackops/scripts/python/helpers/helpers_webui/machine_update_checkout.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_update_constants` | `cli-helper` | `cli-helper` | `medium` | 3 | 26 | - | src/stackops/scripts/python/helpers/helpers_webui/machine_update_constants.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_update_effects` | `cli-helper` | `cli-helper` | `medium` | 1 | 53 | classes:3, funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/machine_update_effects.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_update_install` | `cli-helper` | `cli-helper` | `medium` | 2 | 118 | classes:2, funcs:6 | src/stackops/scripts/python/helpers/helpers_webui/machine_update_install.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_update_latest` | `cli-helper` | `cli-helper` | `medium` | 1 | 198 | classes:6, funcs:6 | src/stackops/scripts/python/helpers/helpers_webui/machine_update_latest.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_update_routes` | `cli-helper` | `cli-helper` | `medium` | 1 | 29 | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/machine_update_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_update_state` | `cli-helper` | `cli-helper` | `medium` | 1 | 87 | classes:2, funcs:2 | src/stackops/scripts/python/helpers/helpers_webui/machine_update_state.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_windows_actions` | `cli-helper` | `cli-helper` | `medium` | 1 | 52 | funcs:2 | src/stackops/scripts/python/helpers/helpers_webui/machine_windows_actions.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_windows_constants` | `cli-helper` | `cli-helper` | `medium` | 4 | 14 | - | src/stackops/scripts/python/helpers/helpers_webui/machine_windows_constants.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_windows_listing` | `cli-helper` | `cli-helper` | `medium` | 2 | 88 | funcs:3 | src/stackops/scripts/python/helpers/helpers_webui/machine_windows_listing.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_windows_macos` | `cli-helper` | `cli-helper` | `medium` | 1 | 101 | classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_webui/machine_windows_macos.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_windows_models` | `cli-helper` | `cli-helper` | `medium` | 4 | 67 | classes:8 | src/stackops/scripts/python/helpers/helpers_webui/machine_windows_models.py |  |
| `stackops.scripts.python.helpers.helpers_webui.machine_windows_routes` | `cli-helper` | `cli-helper` | `medium` | 1 | 50 | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/machine_windows_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.network_constants` | `cli-helper` | `cli-helper` | `medium` | 10 | 40 | - | src/stackops/scripts/python/helpers/helpers_webui/network_constants.py |  |
| `stackops.scripts.python.helpers.helpers_webui.network_forwards` | `cli-helper` | `cli-helper` | `medium` | 2 | 142 | classes:6, funcs:6 | src/stackops/scripts/python/helpers/helpers_webui/network_forwards.py |  |
| `stackops.scripts.python.helpers.helpers_webui.network_glance` | `cli-helper` | `cli-helper` | `medium` | 1 | 36 | classes:1, funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/network_glance.py |  |
| `stackops.scripts.python.helpers.helpers_webui.network_routes` | `cli-helper` | `cli-helper` | `medium` | 1 | 105 | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/network_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.network_ssh_keys` | `cli-helper` | `cli-helper` | `medium` | 2 | 234 | classes:6, funcs:11 | src/stackops/scripts/python/helpers/helpers_webui/network_ssh_keys.py |  |
| `stackops.scripts.python.helpers.helpers_webui.network_ssh_setup` | `cli-helper` | `cli-helper` | `medium` | 1 | 89 | classes:2, funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/network_ssh_setup.py |  |
| `stackops.scripts.python.helpers.helpers_webui.network_system` | `cli-helper` | `cli-helper` | `medium` | 4 | 10 | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/network_system.py |  |
| `stackops.scripts.python.helpers.helpers_webui.network_tunnels` | `cli-helper` | `cli-helper` | `medium` | 3 | 150 | classes:4, funcs:5 | src/stackops/scripts/python/helpers/helpers_webui/network_tunnels.py |  |
| `stackops.scripts.python.helpers.helpers_webui.network_tunnels_account` | `cli-helper` | `cli-helper` | `medium` | 1 | 58 | classes:3, funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/network_tunnels_account.py |  |
| `stackops.scripts.python.helpers.helpers_webui.network_warp` | `cli-helper` | `cli-helper` | `medium` | 2 | 41 | classes:1, funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/network_warp.py |  |
| `stackops.scripts.python.helpers.helpers_webui.network_wifi` | `cli-helper` | `cli-helper` | `medium` | 2 | 127 | classes:3, funcs:6 | src/stackops/scripts/python/helpers/helpers_webui/network_wifi.py |  |
| `stackops.scripts.python.helpers.helpers_webui.network_wifi_linux` | `cli-helper` | `cli-helper` | `medium` | 1 | 56 | funcs:3 | src/stackops/scripts/python/helpers/helpers_webui/network_wifi_linux.py |  |
| `stackops.scripts.python.helpers.helpers_webui.network_wifi_macos` | `cli-helper` | `cli-helper` | `medium` | 1 | 66 | funcs:3 | src/stackops/scripts/python/helpers/helpers_webui/network_wifi_macos.py |  |
| `stackops.scripts.python.helpers.helpers_webui.network_wifi_model` | `cli-helper` | `cli-helper` | `medium` | 6 | 55 | classes:5, funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/network_wifi_model.py |  |
| `stackops.scripts.python.helpers.helpers_webui.network_wifi_windows` | `cli-helper` | `cli-helper` | `medium` | 1 | 27 | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/network_wifi_windows.py |  |
| `stackops.scripts.python.helpers.helpers_webui.other_machines_hosts` | `cli-helper` | `cli-helper` | `medium` | 4 | 66 | classes:2, funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/other_machines_hosts.py |  |
| `stackops.scripts.python.helpers.helpers_webui.other_machines_links` | `cli-helper` | `cli-helper` | `medium` | 3 | 225 | classes:3, funcs:8 | src/stackops/scripts/python/helpers/helpers_webui/other_machines_links.py |  |
| `stackops.scripts.python.helpers.helpers_webui.other_machines_marker` | `cli-helper` | `cli-helper` | `medium` | 4 | 34 | classes:2, funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/other_machines_marker.py |  |
| `stackops.scripts.python.helpers.helpers_webui.other_machines_prepare` | `cli-helper` | `cli-helper` | `medium` | 1 | 39 | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/other_machines_prepare.py |  |
| `stackops.scripts.python.helpers.helpers_webui.other_machines_routes` | `cli-helper` | `cli-helper` | `medium` | 1 | 149 | classes:2, funcs:2 | src/stackops/scripts/python/helpers/helpers_webui/other_machines_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.pages` | `cli-helper` | `cli-helper` | `medium` | 1 | 70 | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/pages.py |  |
| `stackops.scripts.python.helpers.helpers_webui.pty_process` | `cli-helper` | `cli-helper` | `medium` | 2 | 128 | classes:1, funcs:3 | src/stackops/scripts/python/helpers/helpers_webui/pty_process.py |  |
| `stackops.scripts.python.helpers.helpers_webui.run_requests` | `cli-helper` | `cli-helper` | `medium` | 1 | 92 | classes:3, funcs:4 | src/stackops/scripts/python/helpers/helpers_webui/run_requests.py |  |
| `stackops.scripts.python.helpers.helpers_webui.run_socket` | `cli-helper` | `cli-helper` | `medium` | 1 | 41 | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/run_socket.py |  |
| `stackops.scripts.python.helpers.helpers_webui.runs` | `cli-helper` | `cli-helper` | `medium` | 6 | 199 | classes:4, funcs:9 | src/stackops/scripts/python/helpers/helpers_webui/runs.py |  |
| `stackops.scripts.python.helpers.helpers_webui.scripts_files` | `cli-helper` | `cli-helper` | `medium` | 3 | 171 | classes:6, funcs:6 | src/stackops/scripts/python/helpers/helpers_webui/scripts_files.py |  |
| `stackops.scripts.python.helpers.helpers_webui.scripts_online` | `cli-helper` | `cli-helper` | `medium` | 1 | 55 | classes:3, funcs:2 | src/stackops/scripts/python/helpers/helpers_webui/scripts_online.py |  |
| `stackops.scripts.python.helpers.helpers_webui.scripts_routes` | `cli-helper` | `cli-helper` | `medium` | 1 | 45 | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/scripts_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.security_cloud_routes` | `cli-helper` | `cli-helper` | `medium` | 1 | 50 | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/security_cloud_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.security_cloud_state` | `cli-helper` | `cli-helper` | `medium` | 1 | 129 | classes:3, funcs:5 | src/stackops/scripts/python/helpers/helpers_webui/security_cloud_state.py |  |
| `stackops.scripts.python.helpers.helpers_webui.security_constants` | `cli-helper` | `cli-helper` | `medium` | 6 | 27 | - | src/stackops/scripts/python/helpers/helpers_webui/security_constants.py |  |
| `stackops.scripts.python.helpers.helpers_webui.security_drive_link` | `cli-helper` | `cli-helper` | `medium` | 1 | 105 | classes:2, funcs:6 | src/stackops/scripts/python/helpers/helpers_webui/security_drive_link.py |  |
| `stackops.scripts.python.helpers.helpers_webui.security_locker_keys` | `cli-helper` | `cli-helper` | `medium` | 1 | 106 | classes:2, funcs:6 | src/stackops/scripts/python/helpers/helpers_webui/security_locker_keys.py |  |
| `stackops.scripts.python.helpers.helpers_webui.security_locker_look` | `cli-helper` | `cli-helper` | `medium` | 2 | 133 | classes:2, funcs:5 | src/stackops/scripts/python/helpers/helpers_webui/security_locker_look.py |  |
| `stackops.scripts.python.helpers.helpers_webui.security_locker_routes` | `cli-helper` | `cli-helper` | `medium` | 1 | 48 | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/security_locker_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.security_locker_run` | `cli-helper` | `cli-helper` | `medium` | 1 | 94 | classes:3, funcs:4 | src/stackops/scripts/python/helpers/helpers_webui/security_locker_run.py |  |
| `stackops.scripts.python.helpers.helpers_webui.security_paths` | `cli-helper` | `cli-helper` | `medium` | 6 | 52 | classes:1, funcs:2 | src/stackops/scripts/python/helpers/helpers_webui/security_paths.py |  |
| `stackops.scripts.python.helpers.helpers_webui.security_routes` | `cli-helper` | `cli-helper` | `medium` | 1 | 11 | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/security_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.security_scan_export` | `cli-helper` | `cli-helper` | `medium` | 1 | 104 | classes:4, funcs:5 | src/stackops/scripts/python/helpers/helpers_webui/security_scan_export.py |  |
| `stackops.scripts.python.helpers.helpers_webui.security_scan_plans` | `cli-helper` | `cli-helper` | `medium` | 2 | 146 | classes:5, funcs:6 | src/stackops/scripts/python/helpers/helpers_webui/security_scan_plans.py |  |
| `stackops.scripts.python.helpers.helpers_webui.security_scan_routes` | `cli-helper` | `cli-helper` | `medium` | 1 | 62 | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/security_scan_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.server_app` | `cli-helper` | `cli-helper` | `medium` | 1 | 253 | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/server_app.py |  |
| `stackops.scripts.python.helpers.helpers_webui.server_main` | `cli-helper` | `cli-helper` | `medium` | 0 | 66 | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/server_main.py |  |
| `stackops.scripts.python.helpers.helpers_webui.settings_assets` | `cli-helper` | `cli-helper` | `medium` | 1 | 128 | classes:3, funcs:7 | src/stackops/scripts/python/helpers/helpers_webui/settings_assets.py |  |
| `stackops.scripts.python.helpers.helpers_webui.settings_constants` | `cli-helper` | `cli-helper` | `medium` | 2 | 20 | - | src/stackops/scripts/python/helpers/helpers_webui/settings_constants.py |  |
| `stackops.scripts.python.helpers.helpers_webui.settings_files` | `cli-helper` | `cli-helper` | `medium` | 1 | 196 | classes:6, funcs:11 | src/stackops/scripts/python/helpers/helpers_webui/settings_files.py |  |
| `stackops.scripts.python.helpers.helpers_webui.settings_routes` | `cli-helper` | `cli-helper` | `medium` | 1 | 84 | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/settings_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.settings_setup` | `cli-helper` | `cli-helper` | `medium` | 1 | 113 | classes:2, funcs:3 | src/stackops/scripts/python/helpers/helpers_webui/settings_setup.py |  |
| `stackops.scripts.python.helpers.helpers_webui.software_catalog` | `cli-helper` | `cli-helper` | `medium` | 1 | 105 | classes:5, funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/software_catalog.py |  |
| `stackops.scripts.python.helpers.helpers_webui.software_versions` | `cli-helper` | `cli-helper` | `medium` | 3 | 178 | classes:3, funcs:5 | src/stackops/scripts/python/helpers/helpers_webui/software_versions.py |  |
| `stackops.scripts.python.helpers.helpers_webui.terminal_ghostty_constants` | `cli-helper` | `cli-helper` | `medium` | 1 | 8 | - | src/stackops/scripts/python/helpers/helpers_webui/terminal_ghostty_constants.py |  |
| `stackops.scripts.python.helpers.helpers_webui.terminal_ghostty_routes` | `cli-helper` | `cli-helper` | `medium` | 1 | 14 | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/terminal_ghostty_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.terminal_ghostty_status` | `cli-helper` | `cli-helper` | `medium` | 1 | 52 | classes:2, funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/terminal_ghostty_status.py |  |
| `stackops.scripts.python.helpers.helpers_webui.terminal_layouts_routes` | `cli-helper` | `cli-helper` | `medium` | 1 | 32 | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/terminal_layouts_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.terminal_multiplexer_constants` | `cli-helper` | `cli-helper` | `medium` | 2 | 13 | - | src/stackops/scripts/python/helpers/helpers_webui/terminal_multiplexer_constants.py |  |
| `stackops.scripts.python.helpers.helpers_webui.terminal_multiplexer_routes` | `cli-helper` | `cli-helper` | `medium` | 1 | 37 | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/terminal_multiplexer_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.terminal_multiplexer_sessions` | `cli-helper` | `cli-helper` | `medium` | 1 | 65 | classes:1, funcs:2 | src/stackops/scripts/python/helpers/helpers_webui/terminal_multiplexer_sessions.py |  |
| `stackops.scripts.python.helpers.helpers_webui.terminal_multiplexer_store` | `cli` | `cli-module` | `high` | 1 | 42 | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/terminal_multiplexer_store.py |  |
| `stackops.scripts.python.helpers.helpers_webui.terminal_multiplexer_views` | `cli-helper` | `cli-helper` | `medium` | 3 | 171 | classes:4, funcs:6 | src/stackops/scripts/python/helpers/helpers_webui/terminal_multiplexer_views.py |  |
| `stackops.scripts.python.helpers.helpers_webui.terminal_shell_profile_constants` | `cli-helper` | `cli-helper` | `medium` | 2 | 33 | - | src/stackops/scripts/python/helpers/helpers_webui/terminal_shell_profile_constants.py |  |
| `stackops.scripts.python.helpers.helpers_webui.terminal_shell_profile_gives` | `cli-helper` | `cli-helper` | `medium` | 1 | 97 | classes:4, funcs:4 | src/stackops/scripts/python/helpers/helpers_webui/terminal_shell_profile_gives.py |  |
| `stackops.scripts.python.helpers.helpers_webui.terminal_shell_profile_routes` | `cli-helper` | `cli-helper` | `medium` | 1 | 20 | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/terminal_shell_profile_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.terminal_shell_profile_state` | `cli-helper` | `cli-helper` | `medium` | 1 | 181 | classes:4, funcs:7 | src/stackops/scripts/python/helpers/helpers_webui/terminal_shell_profile_state.py |  |
| `stackops.scripts.python.helpers.helpers_webui.terminal_starship_constants` | `cli-helper` | `cli-helper` | `medium` | 1 | 6 | - | src/stackops/scripts/python/helpers/helpers_webui/terminal_starship_constants.py |  |
| `stackops.scripts.python.helpers.helpers_webui.terminal_starship_routes` | `cli-helper` | `cli-helper` | `medium` | 1 | 79 | classes:1, funcs:2 | src/stackops/scripts/python/helpers/helpers_webui/terminal_starship_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.terminal_wezterm_routes` | `cli-helper` | `cli-helper` | `medium` | 1 | 28 | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/terminal_wezterm_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.terminal_wezterm_settings` | `cli-helper` | `cli-helper` | `medium` | 1 | 104 | classes:2, funcs:2 | src/stackops/scripts/python/helpers/helpers_webui/terminal_wezterm_settings.py |  |
| `stackops.scripts.python.helpers.helpers_webui.text_files` | `cli-helper` | `cli-helper` | `medium` | 1 | 72 | classes:2, funcs:2 | src/stackops/scripts/python/helpers/helpers_webui/text_files.py |  |
| `stackops.scripts.python.helpers.helpers_webui.vault_bitwarden_items` | `cli-helper` | `cli-helper` | `medium` | 1 | 145 | classes:4, funcs:3 | src/stackops/scripts/python/helpers/helpers_webui/vault_bitwarden_items.py |  |
| `stackops.scripts.python.helpers.helpers_webui.vault_bitwarden_routes` | `cli-helper` | `cli-helper` | `medium` | 1 | 52 | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/vault_bitwarden_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.vault_bitwarden_state` | `cli-helper` | `cli-helper` | `medium` | 2 | 150 | classes:4, funcs:4 | src/stackops/scripts/python/helpers/helpers_webui/vault_bitwarden_state.py |  |
| `stackops.scripts.python.helpers.helpers_webui.vault_file_constants` | `cli-helper` | `cli-helper` | `medium` | 3 | 44 | - | src/stackops/scripts/python/helpers/helpers_webui/vault_file_constants.py |  |
| `stackops.scripts.python.helpers.helpers_webui.vault_file_copy` | `cli` | `cli-module` | `high` | 1 | 115 | typer, classes:2, funcs:2 | src/stackops/scripts/python/helpers/helpers_webui/vault_file_copy.py |  |
| `stackops.scripts.python.helpers.helpers_webui.vault_file_fixes` | `cli-helper` | `cli-helper` | `medium` | 2 | 109 | classes:2, funcs:6 | src/stackops/scripts/python/helpers/helpers_webui/vault_file_fixes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.vault_file_health` | `cli` | `cli-module` | `high` | 1 | 174 | typer, classes:5, funcs:5 | src/stackops/scripts/python/helpers/helpers_webui/vault_file_health.py |  |
| `stackops.scripts.python.helpers.helpers_webui.vault_file_problem` | `cli-helper` | `cli-helper` | `medium` | 2 | 100 | classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_webui/vault_file_problem.py |  |
| `stackops.scripts.python.helpers.helpers_webui.vault_file_routes` | `cli-helper` | `cli-helper` | `medium` | 1 | 57 | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/vault_file_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.vault_form` | `cli-helper` | `cli-helper` | `medium` | 7 | 53 | classes:1, funcs:2 | src/stackops/scripts/python/helpers/helpers_webui/vault_form.py |  |
| `stackops.scripts.python.helpers.helpers_webui.vault_routes` | `cli-helper` | `cli-helper` | `medium` | 1 | 70 | funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/vault_routes.py |  |
| `stackops.scripts.python.helpers.helpers_webui.vault_store` | `cli-helper` | `cli-helper` | `medium` | 2 | 128 | classes:3, funcs:4 | src/stackops/scripts/python/helpers/helpers_webui/vault_store.py |  |
| `stackops.scripts.python.helpers.helpers_webui.vault_views` | `cli-helper` | `cli-helper` | `medium` | 4 | 87 | classes:3, funcs:4 | src/stackops/scripts/python/helpers/helpers_webui/vault_views.py |  |
| `stackops.scripts.python.helpers.helpers_webui.vendor_assets` | `cli-helper` | `cli-helper` | `medium` | 1 | 61 | classes:1, funcs:1 | src/stackops/scripts/python/helpers/helpers_webui/vendor_assets.py |  |
| `stackops.scripts.python.helpers.helpers_window.constants` | `cli-helper` | `cli-helper` | `medium` | 3 | 14 | - | src/stackops/scripts/python/helpers/helpers_window/constants.py |  |
| `stackops.scripts.python.helpers.helpers_window.window_linux` | `cli-helper` | `cli-helper` | `medium` | 2 | 71 | funcs:3 | src/stackops/scripts/python/helpers/helpers_window/window_linux.py |  |
| `stackops.scripts.python.helpers.helpers_window.window_macos` | `cli` | `cli-module` | `high` | 2 | 160 | typer, classes:3, funcs:4 | src/stackops/scripts/python/helpers/helpers_window/window_macos.py |  |
| `stackops.scripts.python.helpers.helpers_window.window_macos_api` | `cli-helper` | `cli-helper` | `medium` | 4 | 116 | classes:1, funcs:7 | src/stackops/scripts/python/helpers/helpers_window/window_macos_api.py |  |
| `stackops.scripts.python.helpers.helpers_window.window_models` | `cli-helper` | `cli-helper` | `medium` | 7 | 15 | classes:1 | src/stackops/scripts/python/helpers/helpers_window/window_models.py |  |
| `stackops.scripts.python.helpers.helpers_window.window_windows` | `cli-helper` | `cli-helper` | `medium` | 2 | 121 | classes:1, funcs:3 | src/stackops/scripts/python/helpers/helpers_window/window_windows.py |  |
| `stackops.scripts.python.preview` | `cli` | `cli-entrypoint` | `high` | 1 | 134 | entry:preview, typer, typer-app, cli-registration, main, __main__, funcs:6 | src/stackops/scripts/python/preview.py |  |
| `stackops.scripts.python.seek` | `cli` | `cli-entrypoint` | `high` | 1 | 139 | entry:seek, typer, typer-app, cli-registration, get_app, main, funcs:4 | src/stackops/scripts/python/seek.py |  |
| `stackops.scripts.python.stackops_entry` | `cli` | `cli-entrypoint` | `high` | 0 | 191 | entry:stackops, typer, typer-app, cli-registration, get_app, main, __main__, classes:1, funcs:13 | src/stackops/scripts/python/stackops_entry.py |  |
| `stackops.scripts.python.terminal` | `cli` | `cli-entrypoint` | `high` | 3 | 544 | entry:terminal, typer, typer-app, cli-registration, get_app, main, __main__, funcs:12 | src/stackops/scripts/python/terminal.py |  |
| `stackops.scripts.python.terminal_layout_commands` | `cli` | `cli-module` | `high` | 1 | 164 | typer, funcs:2 | src/stackops/scripts/python/terminal_layout_commands.py |  |
| `stackops.scripts.python.terminal_layout_files` | `cli` | `cli-module` | `high` | 2 | 99 | typer, funcs:5 | src/stackops/scripts/python/terminal_layout_files.py |  |
| `stackops.scripts.python.terminal_summary` | `cli` | `cli-module` | `high` | 2 | 735 | typer, classes:3, funcs:29 | src/stackops/scripts/python/terminal_summary.py |  |
| `stackops.scripts.python.terminal_summary_commands` | `cli` | `cli-module` | `high` | 1 | 42 | typer, funcs:1 | src/stackops/scripts/python/terminal_summary_commands.py |  |
| `stackops.scripts.python.terminal_summary_models` | `cli-helper` | `cli-helper` | `medium` | 1 | 4 | - | src/stackops/scripts/python/terminal_summary_models.py |  |
| `stackops.scripts.python.utils` | `cli` | `cli-entrypoint` | `high` | 1 | 76 | entry:utils, typer, typer-app, cli-registration, get_app, main, __main__, funcs:3 | src/stackops/scripts/python/utils.py |  |
| `stackops.scripts.setup.linux` | `package` | `package-marker` | `high` | 1 | 5 | - | src/stackops/scripts/setup/linux/__init__.py |  |
| `stackops.scripts.setup.macos` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/scripts/setup/macos/__init__.py |  |
| `stackops.scripts.setup.windows` | `package` | `package-marker` | `high` | 1 | 4 | - | src/stackops/scripts/setup/windows/__init__.py |  |
| `stackops.scripts.windows` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/scripts/windows/__init__.py |  |
| `stackops.secrets` | `package` | `package-marker` | `high` | 0 | 0 | api-doc | src/stackops/secrets/__init__.py | Was `secrets.py`; now a package with submodules. |
| `stackops.secrets.assets` | `api` | `python-api-candidate` | `medium` | 5 | 2 | - | src/stackops/secrets/assets.py |  |
| `stackops.secrets.constants` | `api` | `python-api-candidate` | `medium` | 4 | 1 | - | src/stackops/secrets/constants.py |  |
| `stackops.secrets.loader` | `api` | `python-api` | `high` | 16 | 229 | api-doc, classes:1, funcs:15 | src/stackops/secrets/loader.py |  |
| `stackops.secrets.models` | `api` | `python-api` | `high` | 21 | 38 | api-doc, classes:3 | src/stackops/secrets/models.py |  |
| `stackops.secrets.passwords` | `api-or-script` | `manual-review` | `medium` | 1 | 36 | typer, funcs:1 | src/stackops/secrets/passwords.py |  |
| `stackops.secrets.paths` | `api` | `python-api-candidate` | `medium` | 15 | 5 | - | src/stackops/secrets/paths.py |  |
| `stackops.secrets.readers` | `api` | `python-api-candidate` | `medium` | 6 | 67 | classes:1, funcs:2 | src/stackops/secrets/readers.py |  |
| `stackops.secrets.search` | `api` | `python-api` | `high` | 13 | 152 | api-doc, classes:2, funcs:7 | src/stackops/secrets/search.py |  |
| `stackops.secrets.writer` | `api` | `python-api` | `high` | 8 | 57 | api-doc, funcs:3 | src/stackops/secrets/writer.py |  |
| `stackops.settings` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/settings/__init__.py |  |
| `stackops.settings.atuin` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/settings/atuin/__init__.py |  |
| `stackops.settings.atuin.themes` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/settings/atuin/themes/__init__.py |  |
| `stackops.settings.broot` | `package` | `package-marker` | `high` | 0 | 3 | - | src/stackops/settings/broot/__init__.py |  |
| `stackops.settings.glow` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/settings/glow/__init__.py |  |
| `stackops.settings.gromit-mpx` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/settings/gromit-mpx/__init__.py |  |
| `stackops.settings.helix` | `package` | `package-marker` | `high` | 0 | 3 | - | src/stackops/settings/helix/__init__.py |  |
| `stackops.settings.herdr` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/settings/herdr/__init__.py |  |
| `stackops.settings.keras` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/settings/keras/__init__.py |  |
| `stackops.settings.keyboard.espanso.config` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/settings/keyboard/espanso/config/__init__.py |  |
| `stackops.settings.keyboard.espanso.match` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/settings/keyboard/espanso/match/__init__.py |  |
| `stackops.settings.keyboard.kanata` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/settings/keyboard/kanata/__init__.py |  |
| `stackops.settings.lf.linux` | `package` | `package-marker` | `high` | 0 | 3 | - | src/stackops/settings/lf/linux/__init__.py |  |
| `stackops.settings.lf.linux.autocall` | `package` | `package-marker` | `high` | 0 | 7 | - | src/stackops/settings/lf/linux/autocall/__init__.py |  |
| `stackops.settings.lf.linux.exe` | `package` | `package-marker` | `high` | 0 | 5 | - | src/stackops/settings/lf/linux/exe/__init__.py |  |
| `stackops.settings.lf.windows` | `package` | `package-marker` | `high` | 0 | 11 | - | src/stackops/settings/lf/windows/__init__.py |  |
| `stackops.settings.lf.windows.autocall` | `package` | `package-marker` | `high` | 0 | 7 | - | src/stackops/settings/lf/windows/autocall/__init__.py |  |
| `stackops.settings.linters` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/settings/linters/__init__.py |  |
| `stackops.settings.lvim.linux` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/settings/lvim/linux/__init__.py |  |
| `stackops.settings.lvim.windows` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/settings/lvim/windows/__init__.py |  |
| `stackops.settings.lvim.windows.archive` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/settings/lvim/windows/archive/__init__.py |  |
| `stackops.settings.lvim.windows.lua.user` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/settings/lvim/windows/lua/user/__init__.py |  |
| `stackops.settings.marimo` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/settings/marimo/__init__.py |  |
| `stackops.settings.marimo.snippets.globalize` | `asset` | `config-asset` | `high` | 0 | 34 | __main__, funcs:3 | src/stackops/settings/marimo/snippets/globalize.py |  |
| `stackops.settings.mprocs.windows` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/settings/mprocs/windows/__init__.py |  |
| `stackops.settings.ollama` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/settings/ollama/__init__.py |  |
| `stackops.settings.pistol` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/settings/pistol/__init__.py |  |
| `stackops.settings.presenterm` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/settings/presenterm/__init__.py |  |
| `stackops.settings.psmux` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/settings/psmux/__init__.py |  |
| `stackops.settings.pudb` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/settings/pudb/__init__.py |  |
| `stackops.settings.rofi` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/settings/rofi/__init__.py |  |
| `stackops.settings.shells.alacritty` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/settings/shells/alacritty/__init__.py |  |
| `stackops.settings.shells.bash_zsh` | `package` | `package-marker` | `high` | 2 | 1 | - | src/stackops/settings/shells/bash_zsh/__init__.py |  |
| `stackops.settings.shells.ghostty` | `package` | `package-marker` | `high` | 2 | 1 | - | src/stackops/settings/shells/ghostty/__init__.py |  |
| `stackops.settings.shells.ipy.profiles.default` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/settings/shells/ipy/profiles/default/__init__.py |  |
| `stackops.settings.shells.ipy.profiles.default.startup` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/settings/shells/ipy/profiles/default/startup/__init__.py |  |
| `stackops.settings.shells.ipy.profiles.default.startup.playext` | `asset` | `config-asset` | `high` | 0 | 84 | - | src/stackops/settings/shells/ipy/profiles/default/startup/playext.py |  |
| `stackops.settings.shells.kitty` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/settings/shells/kitty/__init__.py |  |
| `stackops.settings.shells.nushell` | `package` | `package-marker` | `high` | 2 | 3 | - | src/stackops/settings/shells/nushell/__init__.py |  |
| `stackops.settings.shells.pwsh` | `package` | `package-marker` | `high` | 2 | 2 | - | src/stackops/settings/shells/pwsh/__init__.py |  |
| `stackops.settings.shells.starship` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/settings/shells/starship/__init__.py |  |
| `stackops.settings.shells.vtm` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/settings/shells/vtm/__init__.py |  |
| `stackops.settings.shells.wezterm` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/settings/shells/wezterm/__init__.py |  |
| `stackops.settings.shells.wt` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/settings/shells/wt/__init__.py |  |
| `stackops.settings.streamlit` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/settings/streamlit/__init__.py |  |
| `stackops.settings.svim.linux` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/settings/svim/linux/__init__.py |  |
| `stackops.settings.svim.windows` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/settings/svim/windows/__init__.py |  |
| `stackops.settings.television.cable_unix` | `package` | `package-marker` | `high` | 0 | 54 | - | src/stackops/settings/television/cable_unix/__init__.py |  |
| `stackops.settings.television.cable_windows` | `package` | `package-marker` | `high` | 0 | 14 | - | src/stackops/settings/television/cable_windows/__init__.py |  |
| `stackops.settings.tere` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/settings/tere/__init__.py |  |
| `stackops.settings.tmux` | `package` | `package-marker` | `high` | 1 | 1 | - | src/stackops/settings/tmux/__init__.py |  |
| `stackops.settings.tv` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/settings/tv/__init__.py |  |
| `stackops.settings.tv.themes` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/settings/tv/themes/__init__.py |  |
| `stackops.settings.wt` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/settings/wt/__init__.py |  |
| `stackops.settings.wt.set_wt_settings` | `asset` | `config-asset` | `high` | 1 | 128 | main, __main__, funcs:3 | src/stackops/settings/wt/set_wt_settings.py |  |
| `stackops.settings.yazi` | `package` | `package-marker` | `high` | 0 | 8 | - | src/stackops/settings/yazi/__init__.py |  |
| `stackops.settings.yazi.scripts` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/settings/yazi/scripts/__init__.py |  |
| `stackops.settings.yazi.scripts.compress_selected` | `script-asset` | `script-asset` | `medium` | 0 | 69 | main, __main__, funcs:6 | src/stackops/settings/yazi/scripts/compress_selected.py |  |
| `stackops.settings.yazi.scripts.copy_file_content` | `script-asset` | `script-asset` | `medium` | 0 | 82 | main, __main__, funcs:4 | src/stackops/settings/yazi/scripts/copy_file_content.py |  |
| `stackops.settings.yazi.scripts.fullscreen_preview` | `script-asset` | `script-asset` | `medium` | 1 | 370 | main, __main__, funcs:26 | src/stackops/settings/yazi/scripts/fullscreen_preview.py |  |
| `stackops.settings.yazi.scripts.interactive_view` | `script-asset` | `script-asset` | `medium` | 1 | 159 | main, __main__, funcs:10 | src/stackops/settings/yazi/scripts/interactive_view.py |  |
| `stackops.settings.yazi.scripts.open_db_readonly` | `script-asset` | `script-asset` | `medium` | 0 | 76 | main, __main__, funcs:7 | src/stackops/settings/yazi/scripts/open_db_readonly.py |  |
| `stackops.settings.yazi.scripts.open_default_app` | `script-asset` | `script-asset` | `medium` | 0 | 290 | main, __main__, classes:1, funcs:16 | src/stackops/settings/yazi/scripts/open_default_app.py |  |
| `stackops.settings.yazi.scripts.serve_browser_file` | `script-asset` | `script-asset` | `medium` | 1 | 253 | main, __main__, classes:1, funcs:12 | src/stackops/settings/yazi/scripts/serve_browser_file.py |  |
| `stackops.settings.yazi.scripts.serve_directory` | `script-asset` | `script-asset` | `medium` | 0 | 112 | typer, main, __main__, classes:1, funcs:3 | src/stackops/settings/yazi/scripts/serve_directory.py |  |
| `stackops.settings.yazi.shell` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/settings/yazi/shell/__init__.py |  |
| `stackops.settings.zed` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/settings/zed/__init__.py |  |
| `stackops.utils` | `package` | `package-marker` | `high` | 16 | 0 | api-doc | src/stackops/utils/__init__.py |  |
| `stackops.utils.accessories` | `api` | `python-api` | `high` | 37 | 130 | api-doc, funcs:8 | src/stackops/utils/accessories.py |  |
| `stackops.utils.cli_utils` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/utils/cli_utils/__init__.py |  |
| `stackops.utils.cli_utils.alias_markers` | `cli-helper` | `cli-helper` | `medium` | 12 | 81 | typer, funcs:5 | src/stackops/utils/cli_utils/alias_markers.py |  |
| `stackops.utils.cli_utils.command_lookup` | `cli-helper` | `cli-helper` | `medium` | 16 | 60 | funcs:2 | src/stackops/utils/cli_utils/command_lookup.py |  |
| `stackops.utils.cli_utils.hierarchy` | `cli-helper` | `cli-helper` | `medium` | 0 | 1370 | - | src/stackops/utils/cli_utils/hierarchy.py |  |
| `stackops.utils.cli_utils.hierarchy_types` | `cli-helper` | `cli-helper` | `medium` | 1 | 1626 | - | src/stackops/utils/cli_utils/hierarchy_types.py |  |
| `stackops.utils.cli_utils.interaction` | `api-or-cli-helper` | `manual-review` | `low` | 81 | 38 | api-doc, typer, funcs:4 | src/stackops/utils/cli_utils/interaction.py |  |
| `stackops.utils.cli_utils.lazy_group` | `cli-helper` | `cli-helper` | `medium` | 1 | 90 | typer, funcs:8 | src/stackops/utils/cli_utils/lazy_group.py |  |
| `stackops.utils.cli_utils.ordered_group` | `cli-helper` | `cli-helper` | `medium` | 5 | 15 | typer, funcs:1 | src/stackops/utils/cli_utils/ordered_group.py |  |
| `stackops.utils.cli_utils.secret_input` | `cli-helper` | `cli-helper` | `medium` | 13 | 32 | typer, funcs:1 | src/stackops/utils/cli_utils/secret_input.py |  |
| `stackops.utils.cli_utils.standard_streams` | `cli-helper` | `cli-helper` | `medium` | 9 | 8 | funcs:1 | src/stackops/utils/cli_utils/standard_streams.py |  |
| `stackops.utils.cli_utils.terminal` | `api-or-cli-helper` | `manual-review` | `low` | 3 | 102 | api-doc, classes:2 | src/stackops/utils/cli_utils/terminal.py | Was `utils.terminal`; moved under `cli_utils/`. |
| `stackops.utils.cloud` | `package` | `package-marker` | `high` | 6 | 1 | - | src/stackops/utils/cloud/__init__.py |  |
| `stackops.utils.cloud.default_remote` | `api` | `python-api` | `high` | 9 | 29 | api-doc, classes:1, funcs:2 | src/stackops/utils/cloud/default_remote.py |  |
| `stackops.utils.cloud.defaults` | `api` | `python-api` | `high` | 5 | 29 | api-doc, classes:1, funcs:1 | src/stackops/utils/cloud/defaults.py | Was `utils.cloud_defaults`; moved under `cloud/`. |
| `stackops.utils.cloud.encryption` | `api` | `python-api` | `high` | 10 | 19 | api-doc, funcs:1 | src/stackops/utils/cloud/encryption.py | Was `utils.encryption`; moved under `cloud/`. |
| `stackops.utils.cloud.onedrive` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/utils/cloud/onedrive/__init__.py |  |
| `stackops.utils.cloud.onedrive.accounts` | `api` | `python-api-candidate` | `medium` | 2 | 133 | classes:2, funcs:6 | src/stackops/utils/cloud/onedrive/accounts.py |  |
| `stackops.utils.cloud.onedrive.auth` | `api` | `api-cli-bridge` | `medium` | 3 | 165 | api-doc, typer, classes:1, funcs:10 | src/stackops/utils/cloud/onedrive/auth.py |  |
| `stackops.utils.cloud.onedrive.cli` | `api-or-script` | `manual-review` | `medium` | 1 | 199 | typer, typer-app, cli-registration, get_app, funcs:12 | src/stackops/utils/cloud/onedrive/cli.py |  |
| `stackops.utils.cloud.onedrive.constants` | `api` | `python-api-candidate` | `medium` | 5 | 13 | - | src/stackops/utils/cloud/onedrive/constants.py |  |
| `stackops.utils.cloud.onedrive.credentials` | `api` | `python-api-candidate` | `medium` | 1 | 71 | classes:1, funcs:3 | src/stackops/utils/cloud/onedrive/credentials.py |  |
| `stackops.utils.cloud.onedrive.errors` | `api-or-script` | `manual-review` | `medium` | 6 | 15 | typer, classes:1, funcs:1 | src/stackops/utils/cloud/onedrive/errors.py |  |
| `stackops.utils.cloud.onedrive.file_ops` | `api` | `api-cli-bridge` | `medium` | 1 | 104 | api-doc, typer, funcs:3 | src/stackops/utils/cloud/onedrive/file_ops.py |  |
| `stackops.utils.cloud.onedrive.items` | `api` | `python-api-candidate` | `medium` | 1 | 151 | funcs:4 | src/stackops/utils/cloud/onedrive/items.py |  |
| `stackops.utils.cloud.onedrive.output` | `api-or-script` | `manual-review` | `medium` | 3 | 28 | typer, funcs:2 | src/stackops/utils/cloud/onedrive/output.py |  |
| `stackops.utils.cloud.rclone` | `api` | `python-api` | `high` | 10 | 309 | api-doc, classes:2, funcs:20 | src/stackops/utils/cloud/rclone.py | Was `utils.rclone`; moved under `cloud/`. |
| `stackops.utils.cloud.rclone_wrapper` | `api` | `python-api` | `high` | 6 | 182 | api-doc, funcs:8 | src/stackops/utils/cloud/rclone_wrapper.py | Was `utils.rclone_wrapper`; moved under `cloud/`. |
| `stackops.utils.cloud.share_models` | `api` | `python-api-candidate` | `medium` | 5 | 12 | classes:1 | src/stackops/utils/cloud/share_models.py |  |
| `stackops.utils.cloud.target_conflict` | `api` | `python-api-candidate` | `medium` | 1 | 107 | classes:1, funcs:9 | src/stackops/utils/cloud/target_conflict.py |  |
| `stackops.utils.code` | `api` | `python-api` | `high` | 45 | 237 | api-doc, funcs:10 | src/stackops/utils/code.py |  |
| `stackops.utils.constants` | `api` | `python-api-candidate` | `medium` | 28 | 6 | - | src/stackops/utils/constants.py |  |
| `stackops.utils.dashboards` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/utils/dashboards/__init__.py |  |
| `stackops.utils.dashboards.constants` | `api` | `python-api-candidate` | `medium` | 3 | 9 | - | src/stackops/utils/dashboards/constants.py |  |
| `stackops.utils.dashboards.lifecycle` | `api` | `python-api-candidate` | `medium` | 0 | 89 | funcs:2 | src/stackops/utils/dashboards/lifecycle.py |  |
| `stackops.utils.dashboards.ownership` | `api` | `python-api-candidate` | `medium` | 1 | 51 | classes:1, funcs:4 | src/stackops/utils/dashboards/ownership.py |  |
| `stackops.utils.default_agent` | `api` | `python-api-candidate` | `medium` | 5 | 15 | funcs:1 | src/stackops/utils/default_agent.py |  |
| `stackops.utils.default_multiplexer` | `api` | `python-api-candidate` | `medium` | 15 | 57 | funcs:3 | src/stackops/utils/default_multiplexer.py |  |
| `stackops.utils.file_editor_cli` | `api-or-script` | `manual-review` | `medium` | 2 | 31 | typer, funcs:2 | src/stackops/utils/file_editor_cli.py |  |
| `stackops.utils.files` | `package` | `package-marker` | `high` | 1 | 1 | - | src/stackops/utils/files/__init__.py |  |
| `stackops.utils.files.art` | `package` | `package-marker` | `high` | 0 | 4 | - | src/stackops/utils/files/art/__init__.py |  |
| `stackops.utils.files.ascii_art` | `api` | `api-cli-bridge` | `medium` | 1 | 117 | api-doc, __main__, classes:3, funcs:4 | src/stackops/utils/files/ascii_art.py |  |
| `stackops.utils.files.compression` | `api` | `python-api` | `high` | 5 | 393 | api-doc, __all__, funcs:19 | src/stackops/utils/files/compression.py |  |
| `stackops.utils.files.compression_constants` | `api` | `python-api-candidate` | `medium` | 3 | 14 | - | src/stackops/utils/files/compression_constants.py |  |
| `stackops.utils.files.dbms` | `api-or-script` | `manual-review` | `medium` | 1 | 305 | __main__, classes:1, funcs:3 | src/stackops/utils/files/dbms.py |  |
| `stackops.utils.files.download` | `api-or-script` | `manual-review` | `medium` | 4 | 157 | typer, __main__, funcs:1 | src/stackops/utils/files/download.py |  |
| `stackops.utils.files.f` | `api` | `python-api-candidate` | `medium` | 0 | 25 | classes:1, funcs:1 | src/stackops/utils/files/f.py |  |
| `stackops.utils.files.headers` | `api` | `python-api` | `high` | 1 | 109 | api-doc, funcs:6 | src/stackops/utils/files/headers.py |  |
| `stackops.utils.files.notebook` | `api` | `python-api` | `high` | 0 | 48 | api-doc, funcs:1 | src/stackops/utils/files/notebook.py |  |
| `stackops.utils.files.ouch` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/utils/files/ouch/__init__.py |  |
| `stackops.utils.files.ouch.decompress` | `api` | `python-api` | `high` | 0 | 44 | api-doc, funcs:1 | src/stackops/utils/files/ouch/decompress.py |  |
| `stackops.utils.files.read` | `api` | `api-cli-bridge` | `medium` | 17 | 199 | api-doc, __main__, funcs:18 | src/stackops/utils/files/read.py |  |
| `stackops.utils.html_report` | `api` | `python-api-candidate` | `medium` | 4 | 39 | funcs:1 | src/stackops/utils/html_report.py |  |
| `stackops.utils.installer_utils` | `package` | `package-marker` | `high` | 7 | 1 | api-doc | src/stackops/utils/installer_utils/__init__.py |  |
| `stackops.utils.installer_utils.apt_archive_download` | `api` | `python-api` | `high` | 3 | 33 | api-doc, funcs:1 | src/stackops/utils/installer_utils/apt_archive_download.py |  |
| `stackops.utils.installer_utils.constants` | `api` | `python-api` | `high` | 8 | 32 | api-doc | src/stackops/utils/installer_utils/constants.py |  |
| `stackops.utils.installer_utils.github_commit_dates_constants` | `api` | `python-api` | `high` | 5 | 14 | api-doc | src/stackops/utils/installer_utils/github_commit_dates_constants.py |  |
| `stackops.utils.installer_utils.github_commit_dates_fetch` | `api` | `python-api` | `high` | 1 | 111 | api-doc, classes:1, funcs:2 | src/stackops/utils/installer_utils/github_commit_dates_fetch.py |  |
| `stackops.utils.installer_utils.github_commit_dates_output` | `api` | `python-api` | `high` | 1 | 54 | api-doc, classes:2, funcs:2 | src/stackops/utils/installer_utils/github_commit_dates_output.py |  |
| `stackops.utils.installer_utils.github_commit_dates_report` | `api` | `python-api` | `high` | 2 | 99 | api-doc, classes:2, funcs:6 | src/stackops/utils/installer_utils/github_commit_dates_report.py |  |
| `stackops.utils.installer_utils.github_release_bulk` | `api` | `python-api` | `high` | 3 | 143 | api-doc, classes:3, funcs:6 | src/stackops/utils/installer_utils/github_release_bulk.py |  |
| `stackops.utils.installer_utils.github_release_scraper` | `api` | `python-api` | `high` | 1 | 97 | api-doc, funcs:5 | src/stackops/utils/installer_utils/github_release_scraper.py |  |
| `stackops.utils.installer_utils.install_from_url` | `api` | `python-api` | `high` | 1 | 254 | api-doc, classes:1, funcs:7 | src/stackops/utils/installer_utils/install_from_url.py |  |
| `stackops.utils.installer_utils.install_request_logic` | `api` | `python-api` | `high` | 7 | 309 | api-doc, classes:2, funcs:12 | src/stackops/utils/installer_utils/install_request_logic.py |  |
| `stackops.utils.installer_utils.installer_bulk_display` | `api` | `python-api` | `high` | 2 | 203 | api-doc, funcs:10 | src/stackops/utils/installer_utils/installer_bulk_display.py |  |
| `stackops.utils.installer_utils.installer_bulk_models` | `api` | `python-api` | `high` | 5 | 57 | api-doc, classes:6 | src/stackops/utils/installer_utils/installer_bulk_models.py |  |
| `stackops.utils.installer_utils.installer_bulk_plan` | `api` | `python-api` | `high` | 2 | 95 | api-doc, funcs:3 | src/stackops/utils/installer_utils/installer_bulk_plan.py |  |
| `stackops.utils.installer_utils.installer_bulk_runner` | `api` | `python-api` | `high` | 1 | 208 | api-doc, funcs:4 | src/stackops/utils/installer_utils/installer_bulk_runner.py |  |
| `stackops.utils.installer_utils.installer_bulk_steps` | `api` | `python-api` | `high` | 1 | 41 | api-doc, funcs:3 | src/stackops/utils/installer_utils/installer_bulk_steps.py |  |
| `stackops.utils.installer_utils.installer_bulk_worker` | `api` | `api-cli-bridge` | `medium` | 1 | 18 | api-doc, __main__, funcs:1 | src/stackops/utils/installer_utils/installer_bulk_worker.py |  |
| `stackops.utils.installer_utils.installer_catalog` | `api` | `python-api` | `high` | 13 | 209 | api-doc, classes:1, funcs:12 | src/stackops/utils/installer_utils/installer_catalog.py |  |
| `stackops.utils.installer_utils.installer_class` | `api` | `python-api` | `high` | 23 | 386 | api-doc, classes:1 | src/stackops/utils/installer_utils/installer_class.py |  |
| `stackops.utils.installer_utils.installer_cli` | `api` | `api-cli-bridge` | `medium` | 17 | 328 | api-doc, typer, funcs:9 | src/stackops/utils/installer_utils/installer_cli.py |  |
| `stackops.utils.installer_utils.installer_explore` | `api` | `api-cli-bridge` | `medium` | 1 | 175 | api-doc, typer, funcs:6 | src/stackops/utils/installer_utils/installer_explore.py |  |
| `stackops.utils.installer_utils.installer_explore_preview` | `api` | `python-api` | `high` | 2 | 76 | api-doc, funcs:3 | src/stackops/utils/installer_utils/installer_explore_preview.py |  |
| `stackops.utils.installer_utils.installer_helper` | `api` | `python-api` | `high` | 3 | 192 | api-doc, funcs:6 | src/stackops/utils/installer_utils/installer_helper.py |  |
| `stackops.utils.installer_utils.installer_locator_utils` | `api` | `python-api` | `high` | 10 | 383 | api-doc, funcs:14 | src/stackops/utils/installer_utils/installer_locator_utils.py |  |
| `stackops.utils.installer_utils.installer_main_protocol` | `api` | `python-api` | `high` | 28 | 67 | api-doc, classes:1, funcs:2 | src/stackops/utils/installer_utils/installer_main_protocol.py |  |
| `stackops.utils.installer_utils.installer_offline` | `api` | `api-cli-bridge` | `medium` | 1 | 71 | api-doc, __main__, funcs:1 | src/stackops/utils/installer_utils/installer_offline.py |  |
| `stackops.utils.installer_utils.installer_offline_constants` | `api` | `python-api` | `high` | 5 | 71 | api-doc, funcs:2 | src/stackops/utils/installer_utils/installer_offline_constants.py |  |
| `stackops.utils.installer_utils.installer_offline_models` | `api` | `python-api` | `high` | 6 | 40 | api-doc, classes:4 | src/stackops/utils/installer_utils/installer_offline_models.py |  |
| `stackops.utils.installer_utils.installer_offline_publish` | `api` | `python-api` | `high` | 1 | 107 | api-doc, funcs:6 | src/stackops/utils/installer_utils/installer_offline_publish.py |  |
| `stackops.utils.installer_utils.installer_offline_render` | `api` | `python-api` | `high` | 1 | 68 | api-doc, funcs:3 | src/stackops/utils/installer_utils/installer_offline_render.py |  |
| `stackops.utils.installer_utils.installer_offline_scripts` | `api` | `python-api` | `high` | 1 | 142 | api-doc, funcs:1 | src/stackops/utils/installer_utils/installer_offline_scripts.py |  |
| `stackops.utils.installer_utils.installer_offline_steps` | `api` | `python-api` | `high` | 1 | 45 | api-doc, funcs:3 | src/stackops/utils/installer_utils/installer_offline_steps.py |  |
| `stackops.utils.installer_utils.installer_offline_uv` | `api` | `python-api` | `high` | 1 | 109 | api-doc, funcs:6 | src/stackops/utils/installer_utils/installer_offline_uv.py |  |
| `stackops.utils.installer_utils.installer_removal` | `api` | `python-api` | `high` | 2 | 95 | api-doc, classes:3, funcs:2 | src/stackops/utils/installer_utils/installer_removal.py |  |
| `stackops.utils.installer_utils.installer_runner` | `api` | `python-api` | `high` | 9 | 144 | api-doc, funcs:5 | src/stackops/utils/installer_utils/installer_runner.py |  |
| `stackops.utils.installer_utils.installer_scripts` | `api` | `python-api` | `high` | 5 | 39 | api-doc, funcs:3 | src/stackops/utils/installer_utils/installer_scripts.py |  |
| `stackops.utils.installer_utils.installer_summary` | `api` | `python-api` | `high` | 2 | 123 | api-doc, funcs:8 | src/stackops/utils/installer_utils/installer_summary.py |  |
| `stackops.utils.installer_utils.installer_uninstall_command` | `api` | `python-api` | `high` | 1 | 69 | api-doc, funcs:1 | src/stackops/utils/installer_utils/installer_uninstall_command.py |  |
| `stackops.utils.installer_utils.linux_package_file` | `api` | `python-api` | `high` | 4 | 66 | api-doc, classes:1, funcs:4 | src/stackops/utils/installer_utils/linux_package_file.py |  |
| `stackops.utils.installer_utils.linux_package_manager` | `api` | `api-cli-bridge` | `medium` | 19 | 229 | api-doc, main, __main__, classes:5, funcs:12 | src/stackops/utils/installer_utils/linux_package_manager.py |  |
| `stackops.utils.installer_utils.package_manager_installation` | `api` | `python-api` | `high` | 2 | 82 | api-doc, funcs:3 | src/stackops/utils/installer_utils/package_manager_installation.py |  |
| `stackops.utils.installer_utils.update_github_commit_dates` | `api` | `api-cli-bridge` | `medium` | 2 | 137 | api-doc, main, __main__, classes:1, funcs:3 | src/stackops/utils/installer_utils/update_github_commit_dates.py |  |
| `stackops.utils.io` | `api` | `python-api` | `high` | 20 | 325 | api-doc, classes:1, funcs:22 | src/stackops/utils/io.py |  |
| `stackops.utils.machine` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/utils/machine/__init__.py |  |
| `stackops.utils.machine.specs` | `api` | `python-api-candidate` | `medium` | 5 | 60 | classes:1, funcs:1 | src/stackops/utils/machine/specs.py |  |
| `stackops.utils.managed_agent_files` | `api` | `python-api-candidate` | `medium` | 5 | 94 | funcs:4 | src/stackops/utils/managed_agent_files.py |  |
| `stackops.utils.managed_file_cli` | `api-or-script` | `manual-review` | `medium` | 13 | 71 | typer, funcs:2 | src/stackops/utils/managed_file_cli.py |  |
| `stackops.utils.managed_file_commands` | `api-or-script` | `manual-review` | `medium` | 2 | 44 | typer, cli-registration, funcs:1 | src/stackops/utils/managed_file_commands.py |  |
| `stackops.utils.managed_file_operations` | `api` | `python-api-candidate` | `medium` | 10 | 157 | funcs:5 | src/stackops/utils/managed_file_operations.py |  |
| `stackops.utils.managed_files` | `api` | `python-api-candidate` | `medium` | 24 | 131 | classes:1, funcs:4 | src/stackops/utils/managed_files.py |  |
| `stackops.utils.meta` | `api` | `api-cli-bridge` | `medium` | 25 | 280 | api-doc, __main__, funcs:3 | src/stackops/utils/meta.py |  |
| `stackops.utils.network` | `package` | `package-marker` | `high` | 1 | 0 | - | src/stackops/utils/network/__init__.py |  |
| `stackops.utils.network.address` | `api` | `api-cli-bridge` | `medium` | 17 | 264 | api-doc, __main__, classes:6, funcs:10 | src/stackops/utils/network/address.py |  |
| `stackops.utils.optional_dependencies` | `api` | `python-api-candidate` | `medium` | 2 | 5 | - | src/stackops/utils/optional_dependencies.py |  |
| `stackops.utils.options_utils` | `package` | `package-marker` | `high` | 4 | 0 | - | src/stackops/utils/options_utils/__init__.py |  |
| `stackops.utils.options_utils.options` | `api` | `python-api` | `high` | 23 | 319 | api-doc, funcs:8 | src/stackops/utils/options_utils/options.py | Was `utils.options`; moved under `options_utils/`. |
| `stackops.utils.options_utils.options_tv_linux` | `api-or-script` | `manual-review` | `medium` | 1 | 234 | __main__, funcs:9 | src/stackops/utils/options_utils/options_tv_linux.py |  |
| `stackops.utils.options_utils.options_tv_windows` | `api-or-script` | `manual-review` | `medium` | 1 | 100 | __main__, funcs:5 | src/stackops/utils/options_utils/options_tv_windows.py |  |
| `stackops.utils.options_utils.textual_options_form` | `api` | `api-cli-bridge` | `medium` | 0 | 421 | api-doc, __main__, classes:5, funcs:14 | src/stackops/utils/options_utils/textual_options_form.py |  |
| `stackops.utils.options_utils.textual_options_form_types` | `api` | `python-api` | `high` | 1 | 22 | api-doc, classes:2 | src/stackops/utils/options_utils/textual_options_form_types.py |  |
| `stackops.utils.options_utils.tv_options` | `api` | `api-cli-bridge` | `medium` | 27 | 46 | api-doc, __main__, funcs:3 | src/stackops/utils/options_utils/tv_options.py |  |
| `stackops.utils.path_core` | `api` | `python-api` | `high` | 30 | 425 | api-doc, __all__, funcs:22 | src/stackops/utils/path_core.py |  |
| `stackops.utils.path_reference` | `api` | `python-api` | `high` | 27 | 19 | api-doc, funcs:3 | src/stackops/utils/path_reference.py |  |
| `stackops.utils.python` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/utils/python/__init__.py |  |
| `stackops.utils.python.imports` | `api` | `python-api-candidate` | `medium` | 2 | 39 | funcs:2 | src/stackops/utils/python/imports.py |  |
| `stackops.utils.repos` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/utils/repos/__init__.py |  |
| `stackops.utils.repos.constants` | `api` | `python-api-candidate` | `medium` | 6 | 9 | - | src/stackops/utils/repos/constants.py |  |
| `stackops.utils.repos.project` | `api` | `python-api` | `high` | 8 | 27 | api-doc, funcs:1 | src/stackops/utils/repos/project.py |  |
| `stackops.utils.repos.stackops_paths` | `api` | `python-api` | `high` | 10 | 68 | api-doc, funcs:6 | src/stackops/utils/repos/stackops_paths.py |  |
| `stackops.utils.sandbox.containers` | `api` | `python-api-candidate` | `medium` | 7 | 67 | funcs:2 | src/stackops/utils/sandbox/containers.py |  |
| `stackops.utils.sandbox.host` | `api` | `python-api-candidate` | `medium` | 1 | 62 | funcs:1 | src/stackops/utils/sandbox/host.py |  |
| `stackops.utils.sandbox.launch` | `api` | `python-api-candidate` | `medium` | 3 | 92 | funcs:2 | src/stackops/utils/sandbox/launch.py |  |
| `stackops.utils.sandbox.openshell` | `api` | `python-api-candidate` | `medium` | 1 | 38 | funcs:1 | src/stackops/utils/sandbox/openshell.py |  |
| `stackops.utils.sandbox.openshell_run` | `api-or-script` | `manual-review` | `medium` | 0 | 143 | main, __main__, funcs:2 | src/stackops/utils/sandbox/openshell_run.py |  |
| `stackops.utils.sandbox.openshell_transfer` | `api` | `python-api-candidate` | `medium` | 1 | 50 | funcs:1 | src/stackops/utils/sandbox/openshell_transfer.py |  |
| `stackops.utils.sandbox.openshell_workspace` | `api` | `python-api-candidate` | `medium` | 1 | 154 | funcs:2 | src/stackops/utils/sandbox/openshell_workspace.py |  |
| `stackops.utils.sandbox.openshell_workspace_entries` | `api` | `python-api-candidate` | `medium` | 1 | 68 | classes:1, funcs:4 | src/stackops/utils/sandbox/openshell_workspace_entries.py |  |
| `stackops.utils.sandbox.options` | `api` | `python-api-candidate` | `medium` | 15 | 35 | classes:4 | src/stackops/utils/sandbox/options.py |  |
| `stackops.utils.sandbox.windows_srt` | `api-or-script` | `manual-review` | `medium` | 1 | 157 | main, __main__, funcs:4 | src/stackops/utils/sandbox/windows_srt.py |  |
| `stackops.utils.schemas` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/utils/schemas/__init__.py |  |
| `stackops.utils.schemas.agents` | `package` | `package-marker` | `high` | 2 | 1 | - | src/stackops/utils/schemas/agents/__init__.py |  |
| `stackops.utils.schemas.config` | `package` | `package-marker` | `high` | 1 | 14 | __all__ | src/stackops/utils/schemas/config/__init__.py |  |
| `stackops.utils.schemas.config.config_types` | `api` | `python-api` | `high` | 6 | 18 | api-doc, classes:2 | src/stackops/utils/schemas/config/config_types.py |  |
| `stackops.utils.schemas.config.constants` | `api` | `python-api-candidate` | `medium` | 3 | 6 | - | src/stackops/utils/schemas/config/constants.py |  |
| `stackops.utils.schemas.config.migration_until_2028_01_json_to_yaml` | `api` | `python-api-candidate` | `medium` | 9 | 46 | funcs:1 | src/stackops/utils/schemas/config/migration_until_2028_01_json_to_yaml.py |  |
| `stackops.utils.schemas.config.multiplexer_types` | `api` | `python-api` | `high` | 30 | 10 | api-doc | src/stackops/utils/schemas/config/multiplexer_types.py |  |
| `stackops.utils.schemas.fire_agents` | `package` | `package-marker` | `high` | 0 | 1 | - | src/stackops/utils/schemas/fire_agents/__init__.py |  |
| `stackops.utils.schemas.fire_agents.fire_agents_types` | `api` | `python-api-candidate` | `medium` | 43 | 76 | classes:2 | src/stackops/utils/schemas/fire_agents/fire_agents_types.py |  |
| `stackops.utils.schemas.installer` | `package` | `package-marker` | `high` | 2 | 2 | api-doc | src/stackops/utils/schemas/installer/__init__.py |  |
| `stackops.utils.schemas.installer.installer_categories` | `api` | `python-api` | `high` | 2 | 177 | api-doc, classes:1, funcs:1 | src/stackops/utils/schemas/installer/installer_categories.py |  |
| `stackops.utils.schemas.installer.installer_types` | `api` | `python-api` | `high` | 56 | 168 | api-doc, classes:11, funcs:2 | src/stackops/utils/schemas/installer/installer_types.py |  |
| `stackops.utils.schemas.installer.package_groups` | `api` | `python-api` | `high` | 5 | 317 | api-doc | src/stackops/utils/schemas/installer/package_groups.py |  |
| `stackops.utils.schemas.json_schema` | `api` | `python-api` | `high` | 1 | 54 | api-doc, funcs:1 | src/stackops/utils/schemas/json_schema.py |  |
| `stackops.utils.schemas.layouts` | `package` | `package-marker` | `high` | 1 | 2 | api-doc | src/stackops/utils/schemas/layouts/__init__.py |  |
| `stackops.utils.schemas.layouts.layout_arrangement` | `api` | `python-api` | `high` | 3 | 9 | api-doc, funcs:1 | src/stackops/utils/schemas/layouts/layout_arrangement.py |  |
| `stackops.utils.schemas.layouts.layout_constants` | `api` | `python-api` | `high` | 8 | 8 | api-doc | src/stackops/utils/schemas/layouts/layout_constants.py |  |
| `stackops.utils.schemas.layouts.layout_enabled` | `api` | `python-api` | `high` | 5 | 45 | api-doc, funcs:2 | src/stackops/utils/schemas/layouts/layout_enabled.py |  |
| `stackops.utils.schemas.layouts.layout_enabled_edit` | `api` | `python-api` | `high` | 1 | 86 | api-doc, classes:2, funcs:1 | src/stackops/utils/schemas/layouts/layout_enabled_edit.py |  |
| `stackops.utils.schemas.layouts.layout_file` | `api` | `python-api` | `high` | 10 | 126 | api-doc, funcs:6 | src/stackops/utils/schemas/layouts/layout_file.py |  |
| `stackops.utils.schemas.layouts.layout_types` | `api` | `python-api` | `high` | 40 | 62 | api-doc, classes:4, funcs:3 | src/stackops/utils/schemas/layouts/layout_types.py |  |
| `stackops.utils.schemas.mapper` | `package` | `package-marker` | `high` | 3 | 4 | - | src/stackops/utils/schemas/mapper/__init__.py |  |
| `stackops.utils.schemas.repos` | `package` | `package-marker` | `high` | 1 | 1 | - | src/stackops/utils/schemas/repos/__init__.py |  |
| `stackops.utils.schemas.repos.repos_types` | `api` | `python-api` | `high` | 17 | 41 | api-doc, classes:5 | src/stackops/utils/schemas/repos/repos_types.py |  |
| `stackops.utils.schemas.startup` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/utils/schemas/startup/__init__.py |  |
| `stackops.utils.schemas.startup.startup_constants` | `api` | `python-api-candidate` | `medium` | 5 | 9 | - | src/stackops/utils/schemas/startup/startup_constants.py |  |
| `stackops.utils.schemas.startup.startup_file` | `api` | `python-api-candidate` | `medium` | 2 | 55 | funcs:2 | src/stackops/utils/schemas/startup/startup_file.py |  |
| `stackops.utils.schemas.startup.startup_types` | `api` | `python-api-candidate` | `medium` | 10 | 19 | classes:2 | src/stackops/utils/schemas/startup/startup_types.py |  |
| `stackops.utils.schemas.yaml_document` | `api` | `python-api` | `high` | 9 | 18 | api-doc, classes:1, funcs:1 | src/stackops/utils/schemas/yaml_document.py |  |
| `stackops.utils.schemas.yaml_schema` | `api` | `python-api` | `high` | 9 | 43 | api-doc, funcs:4 | src/stackops/utils/schemas/yaml_schema.py | Was `utils.yaml_schema`; moved under `schemas/`. |
| `stackops.utils.source_of_truth` | `api` | `api-cli-bridge` | `medium` | 105 | 154 | api-doc, __main__, funcs:9 | src/stackops/utils/source_of_truth.py |  |
| `stackops.utils.ssh_utils` | `package` | `package-marker` | `high` | 0 | 0 | api-doc | src/stackops/utils/ssh_utils/__init__.py |  |
| `stackops.utils.ssh_utils.abc` | `api` | `python-api` | `high` | 7 | 28 | api-doc, classes:1 | src/stackops/utils/ssh_utils/abc.py |  |
| `stackops.utils.ssh_utils.connection_target` | `api` | `python-api` | `high` | 3 | 242 | api-doc, classes:2, funcs:9 | src/stackops/utils/ssh_utils/connection_target.py |  |
| `stackops.utils.ssh_utils.host_key_verification` | `api` | `python-api` | `high` | 2 | 175 | api-doc, classes:2, funcs:5 | src/stackops/utils/ssh_utils/host_key_verification.py |  |
| `stackops.utils.ssh_utils.open_ssh_command` | `api` | `python-api` | `high` | 3 | 65 | api-doc, classes:1, funcs:3 | src/stackops/utils/ssh_utils/open_ssh_command.py |  |
| `stackops.utils.ssh_utils.open_ssh_config` | `api` | `python-api` | `high` | 3 | 89 | api-doc, funcs:5 | src/stackops/utils/ssh_utils/open_ssh_config.py |  |
| `stackops.utils.ssh_utils.server_install` | `api` | `python-api` | `high` | 2 | 72 | api-doc, funcs:2 | src/stackops/utils/ssh_utils/server_install.py |  |
| `stackops.utils.ssh_utils.ssh` | `api` | `api-cli-bridge` | `medium` | 4 | 757 | api-doc, __main__, classes:1 | src/stackops/utils/ssh_utils/ssh.py | Was `utils.ssh`; moved under `ssh_utils/`. |
| `stackops.utils.ssh_utils.ssh_port_activation` | `api` | `python-api` | `high` | 1 | 54 | api-doc, funcs:1 | src/stackops/utils/ssh_utils/ssh_port_activation.py |  |
| `stackops.utils.ssh_utils.ssh_port_apply` | `api` | `python-api` | `high` | 1 | 168 | api-doc, classes:1, funcs:6 | src/stackops/utils/ssh_utils/ssh_port_apply.py |  |
| `stackops.utils.ssh_utils.ssh_port_change` | `api` | `python-api` | `high` | 1 | 80 | api-doc, funcs:2 | src/stackops/utils/ssh_utils/ssh_port_change.py |  |
| `stackops.utils.ssh_utils.ssh_port_commands` | `api` | `python-api` | `high` | 9 | 106 | api-doc, funcs:9 | src/stackops/utils/ssh_utils/ssh_port_commands.py |  |
| `stackops.utils.ssh_utils.ssh_port_firewall` | `api` | `python-api` | `high` | 1 | 235 | api-doc, funcs:6 | src/stackops/utils/ssh_utils/ssh_port_firewall.py |  |
| `stackops.utils.ssh_utils.ssh_port_packet_filter` | `api` | `python-api` | `high` | 1 | 60 | api-doc, funcs:2 | src/stackops/utils/ssh_utils/ssh_port_packet_filter.py |  |
| `stackops.utils.ssh_utils.ssh_port_preflight` | `api` | `python-api` | `high` | 6 | 194 | api-doc, classes:2, funcs:10 | src/stackops/utils/ssh_utils/ssh_port_preflight.py |  |
| `stackops.utils.ssh_utils.ssh_port_selinux` | `api` | `python-api` | `high` | 1 | 71 | api-doc, funcs:2 | src/stackops/utils/ssh_utils/ssh_port_selinux.py |  |
| `stackops.utils.ssh_utils.ssh_port_service` | `api` | `python-api` | `high` | 1 | 183 | api-doc, classes:1, funcs:5 | src/stackops/utils/ssh_utils/ssh_port_service.py |  |
| `stackops.utils.ssh_utils.ssh_port_wsl_firewall` | `api` | `python-api` | `high` | 1 | 157 | api-doc, funcs:1 | src/stackops/utils/ssh_utils/ssh_port_wsl_firewall.py |  |
| `stackops.utils.ssh_utils.transfer_archive` | `api` | `python-api` | `high` | 1 | 64 | api-doc, funcs:3 | src/stackops/utils/ssh_utils/transfer_archive.py |  |
| `stackops.utils.ssh_utils.windows_server_install` | `api` | `python-api` | `high` | 2 | 222 | api-doc, funcs:1 | src/stackops/utils/ssh_utils/windows_server_install.py |  |
| `stackops.utils.ssh_utils.wsl` | `api` | `api-cli-bridge` | `medium` | 3 | 115 | api-doc, __main__, funcs:7 | src/stackops/utils/ssh_utils/wsl.py |  |
| `stackops.utils.ssh_utils.wsl_helper` | `api` | `python-api` | `high` | 1 | 217 | api-doc, funcs:15 | src/stackops/utils/ssh_utils/wsl_helper.py |  |
| `stackops.version` | `api` | `python-api-candidate` | `medium` | 5 | 22 | funcs:1 | src/stackops/version.py |  |

## Next Manual Pass

1. Resolve every `api-or-*` row in the manual queue to `api`, `cli-helper`, or `script-asset`.
2. Promote only modules with stable function/class contracts to `api`; keep command glue and interactive workflows as `cli` or `cli-helper`.
3. After the table is corrected, add a source marker such as `__stackops_module_intent__ = "api"` near the top of each non-asset module.
4. Optionally keep this report as the source of truth for asset/config packages where a code marker would add noise.

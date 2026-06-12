# StackOps Python Module Intent Inventory

> **Staleness notice:** This report was generated against an earlier revision of the codebase.
> The source tree has since been restructured: modules were moved into subpackages
> (e.g. `utils.cloud.*`, `utils.ssh_utils.*`, `utils.schemas.*`, `utils.machine.*`,
> `utils.network.*`, `utils.python.*`, `utils.repos.*`, `profile.linking.*`),
> `stackops.secrets` became a package, new packages were added
> (`architecture_graph`, `settings.procs`, `settings.wsl`), and several top-level
> `utils.*` modules were relocated or removed. The per-module tables below still
> reflect the old layout and should be regenerated before making marker decisions.
> The total module count has been updated to match the current tree.

Generated first-pass report for deciding which Python modules are intended as downstream import API, CLI implementation, CLI helpers, or packaged assets.

This is intentionally a filter, not the final truth. Use the `Manual review queue` section to correct edge cases before adding source-level markers.

Scope: `src/stackops/**/*.py` only. This excludes `src/manual`, which is not part of the installed `stackops` package surface.

## Classification Rules

| Signal | Meaning |
| --- | --- |
| `pyproject.toml [project.scripts]` | Strong CLI entry point signal. |
| `stackops.scripts.python...` | CLI command tree. Direct Typer modules are CLI; non-Typer children are usually CLI helpers. |
| `docs/api` references and `:::: stackops...` directives | Strong public API signal. |
| `stackops.cluster`, `stackops.utils`, `stackops.jobs.installer` | Candidate API roots unless they are script assets or show direct CLI behavior. |
| `stackops.settings`, `stackops.scripts/setup`, installer script folders | Packaged assets or executable scripts, not dependency API by default. |
| `typer`, `get_app`, command registration, `main`, `if __name__ == "__main__"` | CLI/script signal; review if it appears outside the CLI tree. |

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

Total installed `stackops` Python modules: **652**

| First-pass label | Count |
| --- | ---: |
| `api-cli-bridge` | 24 |
| `cli-entrypoint` | 9 |
| `cli-helper` | 189 |
| `cli-module` | 65 |
| `config-asset` | 3 |
| `installer-script-asset` | 26 |
| `manual-review` | 36 |
| `package-marker` | 165 |
| `python-api` | 71 |
| `python-api-candidate` | 25 |
| `script-asset` | 9 |

| Suggested marker | Count |
| --- | ---: |
| `api` | 120 |
| `api-or-cli-helper` | 20 |
| `api-or-script` | 16 |
| `asset` | 3 |
| `cli` | 74 |
| `cli-helper` | 189 |
| `package` | 165 |
| `script-asset` | 35 |

| Confidence | Count |
| --- | ---: |
| `high` | 339 |
| `low` | 20 |
| `medium` | 263 |

## Manual Review Queue

These **60** modules need a human decision before source markers are added.

| Module | Suggested marker | Label | Signals | Reason | Notes |
| --- | --- | --- | --- | --- | --- |
| `stackops.cluster.sessions_managers.helpers.enhanced_command_runner` | `api` | `api-cli-bridge` | api-doc, __main__, funcs:2 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.cluster.sessions_managers.tmux.tmux_local` | `api` | `api-cli-bridge` | api-doc, __main__, classes:3, funcs:1 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.cluster.sessions_managers.windows_terminal.wt_local` | `api` | `api-cli-bridge` | api-doc, __main__, classes:1, funcs:3 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.cluster.sessions_managers.windows_terminal.wt_local_manager` | `api` | `api-cli-bridge` | api-doc, __main__, classes:2, funcs:1 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.cluster.sessions_managers.windows_terminal.wt_remote` | `api` | `api-cli-bridge` | api-doc, __main__, classes:1 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.cluster.sessions_managers.windows_terminal.wt_remote_manager` | `api` | `api-cli-bridge` | api-doc, __main__, classes:1 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.cluster.sessions_managers.windows_terminal.wt_utils.examples.wt_local_manager_demo` | `api` | `api-cli-bridge` | api-doc, __main__, funcs:1 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.cluster.sessions_managers.zellij.zellij_local` | `api` | `api-cli-bridge` | api-doc, __main__, classes:1, funcs:3 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.cluster.sessions_managers.zellij.zellij_local_manager` | `api` | `api-cli-bridge` | api-doc, __main__, classes:2, funcs:3 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.cluster.sessions_managers.zellij.zellij_remote` | `api` | `api-cli-bridge` | api-doc, __main__, classes:1 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.cluster.sessions_managers.zellij.zellij_utils.example_usage` | `api` | `api-cli-bridge` | api-doc, __main__, funcs:1 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.cluster.sessions_managers.zellij.zellij_utils.zellij_local_helper_with_panes` | `api` | `api-cli-bridge` | api-doc, __main__, funcs:8 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.jobs.installer.checks.check_installations` | `api` | `api-cli-bridge` | api-doc, main, __main__, funcs:12 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.jobs.installer.checks.security_cli` | `api` | `api-cli-bridge` | api-doc, typer, typer-app, cli-registration, get_app, funcs:12 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.jobs.installer.checks.security_helper` | `api` | `api-cli-bridge` | api-doc, typer, funcs:18 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.utils.accessories` | `api` | `api-cli-bridge` | api-doc, __main__, funcs:8 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.utils.installer_utils.installer_cli` | `api` | `api-cli-bridge` | api-doc, typer, classes:1, funcs:8 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.utils.installer_utils.installer_explore` | `api` | `api-cli-bridge` | api-doc, typer, classes:3, funcs:10 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.utils.installer_utils.installer_offline` | `api` | `api-cli-bridge` | api-doc, __main__, funcs:1 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.utils.meta` | `api` | `api-cli-bridge` | api-doc, __main__, funcs:2 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.utils.notifications` | `api` | `api-cli-bridge` | api-doc, __main__, classes:1, funcs:3 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.utils.options_utils.tv_options` | `api` | `api-cli-bridge` | api-doc, __main__, funcs:3 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.utils.source_of_truth` | `api` | `api-cli-bridge` | api-doc, __main__, funcs:11 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.utils.ssh` | `api` | `api-cli-bridge` | api-doc, __main__, classes:1 | Referenced by API docs but also has CLI/script signals; review marker wording. |  |
| `stackops.scripts.python.helpers.helpers_network.address` | `api-or-cli-helper` | `manual-review` | api-doc, __main__, classes:6, funcs:10 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.address_switch` | `api-or-cli-helper` | `manual-review` | api-doc, __main__, funcs:7 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.ftpx_impl` | `api-or-cli-helper` | `manual-review` | api-doc, funcs:7 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.onetimeshare` | `api-or-cli-helper` | `manual-review` | api-doc | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_add_key_windows` | `api-or-cli-helper` | `manual-review` | api-doc, funcs:1 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_add_ssh_key` | `api-or-cli-helper` | `manual-review` | api-doc, main, __main__, funcs:2 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_cloud_init` | `api-or-cli-helper` | `manual-review` | api-doc, funcs:2 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_darwin` | `api-or-cli-helper` | `manual-review` | api-doc, __main__, funcs:1 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_darwin_utils` | `api-or-cli-helper` | `manual-review` | api-doc, funcs:2 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_linux` | `api-or-cli-helper` | `manual-review` | api-doc, __main__, funcs:1 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_linux_utils` | `api-or-cli-helper` | `manual-review` | api-doc, funcs:3 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_windows` | `api-or-cli-helper` | `manual-review` | api-doc, __main__, funcs:1 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_windows_utils` | `api-or-cli-helper` | `manual-review` | api-doc, funcs:3 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_deploy_key_remote` | `api-or-cli-helper` | `manual-review` | api-doc, funcs:6 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.wifi_conn` | `api-or-cli-helper` | `manual-review` | api-doc, classes:1, funcs:10 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.wifi_conn_platforms.common` | `api-or-cli-helper` | `manual-review` | api-doc, classes:1, funcs:3 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.wifi_conn_platforms.darwin` | `api-or-cli-helper` | `manual-review` | api-doc, funcs:8 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.wifi_conn_platforms.linux` | `api-or-cli-helper` | `manual-review` | api-doc, classes:1, funcs:15 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.wifi_conn_platforms.unsupported` | `api-or-cli-helper` | `manual-review` | api-doc, funcs:7 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.scripts.python.helpers.helpers_network.wifi_conn_platforms.windows` | `api-or-cli-helper` | `manual-review` | api-doc, funcs:6 | CLI-tree module is referenced by API docs; decide whether it is stable public API. |  |
| `stackops.profile.create_links` | `api-or-script` | `manual-review` | __main__, classes:2, funcs:16 | Library-tree module has CLI/script signals; decide if those are demos, probes, or user-facing CLI. |  |
| `stackops.profile.create_links_export` | `api-or-script` | `manual-review` | typer, funcs:2 | Library-tree module has CLI/script signals; decide if those are demos, probes, or user-facing CLI. |  |
| `stackops.profile.create_shell_profile` | `api-or-script` | `manual-review` | __main__, funcs:6 | Library-tree module has CLI/script signals; decide if those are demos, probes, or user-facing CLI. |  |
| `stackops.utils.cloud.onedrive.setup_oauth` | `api-or-script` | `manual-review` | main, __main__, funcs:1 | Library-tree module has CLI/script signals; decide if those are demos, probes, or user-facing CLI. |  |
| `stackops.utils.files.ascii_art` | `api-or-script` | `manual-review` | __main__, classes:3, funcs:4 | Library-tree module has CLI/script signals; decide if those are demos, probes, or user-facing CLI. |  |
| `stackops.utils.files.dbms` | `api-or-script` | `manual-review` | __main__, classes:1, funcs:3 | Library-tree module has CLI/script signals; decide if those are demos, probes, or user-facing CLI. |  |
| `stackops.utils.files.read` | `api-or-script` | `manual-review` | __main__, funcs:16 | Library-tree module has CLI/script signals; decide if those are demos, probes, or user-facing CLI. |  |
| `stackops.utils.options_utils.options_tv_linux` | `api-or-script` | `manual-review` | __main__, funcs:7 | Library-tree module has CLI/script signals; decide if those are demos, probes, or user-facing CLI. |  |
| `stackops.utils.options_utils.options_tv_windows` | `api-or-script` | `manual-review` | __main__, funcs:5 | Library-tree module has CLI/script signals; decide if those are demos, probes, or user-facing CLI. |  |
| `stackops.utils.options_utils.textual_options_form_types` | `api-or-script` | `manual-review` | __main__, classes:2, funcs:2 | Library-tree module has CLI/script signals; decide if those are demos, probes, or user-facing CLI. |  |
| `stackops.utils.ssh_utils.wsl` | `api-or-script` | `manual-review` | __main__, funcs:7 | Library-tree module has CLI/script signals; decide if those are demos, probes, or user-facing CLI. |  |

## Clear API Candidates

These **96** modules are the strongest candidates for `api` markers after manual review of the queue above.

| Module | Label | Confidence | Signals | Path | Notes |
| --- | --- | --- | --- | --- | --- |
| `stackops.cluster.remote.cloud_manager` | `python-api` | `high` | api-doc, classes:2, funcs:9 | src/stackops/cluster/remote/cloud_manager.py |  |
| `stackops.cluster.remote.data_transfer` | `python-api` | `high` | api-doc, funcs:3 | src/stackops/cluster/remote/data_transfer.py |  |
| `stackops.cluster.remote.distribute` | `python-api` | `high` | api-doc, classes:5, funcs:6 | src/stackops/cluster/remote/distribute.py |  |
| `stackops.cluster.remote.execution_script` | `python-api` | `high` | api-doc, funcs:1 | src/stackops/cluster/remote/execution_script.py |  |
| `stackops.cluster.remote.file_manager` | `python-api` | `high` | api-doc, classes:1, funcs:6 | src/stackops/cluster/remote/file_manager.py |  |
| `stackops.cluster.remote.job_params` | `python-api` | `high` | api-doc, classes:1, funcs:2 | src/stackops/cluster/remote/job_params.py |  |
| `stackops.cluster.remote.models` | `python-api` | `high` | api-doc, classes:6, funcs:4 | src/stackops/cluster/remote/models.py |  |
| `stackops.cluster.remote.notification` | `python-api` | `high` | api-doc, funcs:1 | src/stackops/cluster/remote/notification.py |  |
| `stackops.cluster.remote.remote_machine` | `python-api` | `high` | api-doc, classes:1, funcs:1 | src/stackops/cluster/remote/remote_machine.py |  |
| `stackops.cluster.sessions_managers.helpers.load_balancer_helper` | `python-api` | `high` | api-doc, funcs:8 | src/stackops/cluster/sessions_managers/helpers/load_balancer_helper.py |  |
| `stackops.cluster.sessions_managers.session_conflict` | `python-api` | `high` | api-doc, classes:2, funcs:8 | src/stackops/cluster/sessions_managers/session_conflict.py |  |
| `stackops.cluster.sessions_managers.session_exit_mode` | `python-api` | `high` | api-doc, funcs:6 | src/stackops/cluster/sessions_managers/session_exit_mode.py |  |
| `stackops.cluster.sessions_managers.tmux.tmux_local_manager` | `python-api` | `high` | api-doc, classes:2 | src/stackops/cluster/sessions_managers/tmux/tmux_local_manager.py |  |
| `stackops.cluster.sessions_managers.tmux.tmux_utils.tmux_common` | `python-api` | `high` | api-doc, funcs:3 | src/stackops/cluster/sessions_managers/tmux/tmux_utils/tmux_common.py |  |
| `stackops.cluster.sessions_managers.tmux.tmux_utils.tmux_execution` | `python-api` | `high` | api-doc, funcs:16 | src/stackops/cluster/sessions_managers/tmux/tmux_utils/tmux_execution.py |  |
| `stackops.cluster.sessions_managers.tmux.tmux_utils.tmux_layout` | `python-api` | `high` | api-doc, funcs:11 | src/stackops/cluster/sessions_managers/tmux/tmux_utils/tmux_layout.py |  |
| `stackops.cluster.sessions_managers.tmux.tmux_utils.tmux_status` | `python-api` | `high` | api-doc, classes:1, funcs:2 | src/stackops/cluster/sessions_managers/tmux/tmux_utils/tmux_status.py |  |
| `stackops.cluster.sessions_managers.utils.load_balancer` | `python-api` | `high` | api-doc, classes:1, funcs:3 | src/stackops/cluster/sessions_managers/utils/load_balancer.py |  |
| `stackops.cluster.sessions_managers.utils.maker` | `python-api` | `high` | api-doc, funcs:4 | src/stackops/cluster/sessions_managers/utils/maker.py |  |
| `stackops.cluster.sessions_managers.windows_terminal.wt_utils.layout_generator` | `python-api` | `high` | api-doc, classes:1 | src/stackops/cluster/sessions_managers/windows_terminal/wt_utils/layout_generator.py |  |
| `stackops.cluster.sessions_managers.windows_terminal.wt_utils.local_monitoring` | `python-api` | `high` | api-doc, classes:1, funcs:5 | src/stackops/cluster/sessions_managers/windows_terminal/wt_utils/local_monitoring.py |  |
| `stackops.cluster.sessions_managers.windows_terminal.wt_utils.manager_persistence` | `python-api` | `high` | api-doc, funcs:6 | src/stackops/cluster/sessions_managers/windows_terminal/wt_utils/manager_persistence.py |  |
| `stackops.cluster.sessions_managers.windows_terminal.wt_utils.monitoring_helpers` | `python-api` | `high` | api-doc, funcs:6 | src/stackops/cluster/sessions_managers/windows_terminal/wt_utils/monitoring_helpers.py |  |
| `stackops.cluster.sessions_managers.windows_terminal.wt_utils.process_monitor` | `python-api` | `high` | api-doc, classes:1 | src/stackops/cluster/sessions_managers/windows_terminal/wt_utils/process_monitor.py |  |
| `stackops.cluster.sessions_managers.windows_terminal.wt_utils.remote_executor` | `python-api` | `high` | api-doc, classes:1 | src/stackops/cluster/sessions_managers/windows_terminal/wt_utils/remote_executor.py |  |
| `stackops.cluster.sessions_managers.windows_terminal.wt_utils.session_manager` | `python-api` | `high` | api-doc, classes:7 | src/stackops/cluster/sessions_managers/windows_terminal/wt_utils/session_manager.py |  |
| `stackops.cluster.sessions_managers.windows_terminal.wt_utils.status_reporter` | `python-api` | `high` | api-doc, classes:1 | src/stackops/cluster/sessions_managers/windows_terminal/wt_utils/status_reporter.py |  |
| `stackops.cluster.sessions_managers.windows_terminal.wt_utils.status_reporting` | `python-api` | `high` | api-doc, funcs:5 | src/stackops/cluster/sessions_managers/windows_terminal/wt_utils/status_reporting.py |  |
| `stackops.cluster.sessions_managers.windows_terminal.wt_utils.wt_helpers` | `python-api` | `high` | api-doc, funcs:7 | src/stackops/cluster/sessions_managers/windows_terminal/wt_utils/wt_helpers.py |  |
| `stackops.cluster.sessions_managers.zellij.zellij_remote_manager` | `python-api` | `high` | api-doc, classes:2 | src/stackops/cluster/sessions_managers/zellij/zellij_remote_manager.py |  |
| `stackops.cluster.sessions_managers.zellij.zellij_utils.layout_generator` | `python-api` | `high` | api-doc, classes:1 | src/stackops/cluster/sessions_managers/zellij/zellij_utils/layout_generator.py |  |
| `stackops.cluster.sessions_managers.zellij.zellij_utils.monitoring_types` | `python-api` | `high` | api-doc, classes:12 | src/stackops/cluster/sessions_managers/zellij/zellij_utils/monitoring_types.py |  |
| `stackops.cluster.sessions_managers.zellij.zellij_utils.process_monitor` | `python-api` | `high` | api-doc, classes:1 | src/stackops/cluster/sessions_managers/zellij/zellij_utils/process_monitor.py |  |
| `stackops.cluster.sessions_managers.zellij.zellij_utils.remote_executor` | `python-api` | `high` | api-doc, classes:1 | src/stackops/cluster/sessions_managers/zellij/zellij_utils/remote_executor.py |  |
| `stackops.cluster.sessions_managers.zellij.zellij_utils.session_manager` | `python-api` | `high` | api-doc, classes:1 | src/stackops/cluster/sessions_managers/zellij/zellij_utils/session_manager.py |  |
| `stackops.cluster.sessions_managers.zellij.zellij_utils.status_reporter` | `python-api` | `high` | api-doc, classes:1 | src/stackops/cluster/sessions_managers/zellij/zellij_utils/status_reporter.py |  |
| `stackops.cluster.sessions_managers.zellij.zellij_utils.zellij_local_helper` | `python-api` | `high` | api-doc, funcs:10 | src/stackops/cluster/sessions_managers/zellij/zellij_utils/zellij_local_helper.py |  |
| `stackops.cluster.sessions_managers.zellij.zellij_utils.zellij_local_helper_restart` | `python-api` | `high` | api-doc, funcs:1 | src/stackops/cluster/sessions_managers/zellij/zellij_utils/zellij_local_helper_restart.py |  |
| `stackops.cluster.sessions_managers.zellij.zellij_utils.zellij_local_manager_helper` | `python-api` | `high` | api-doc, funcs:8 | src/stackops/cluster/sessions_managers/zellij/zellij_utils/zellij_local_manager_helper.py |  |
| `stackops.jobs.installer.checks.install_utils` | `python-api` | `high` | api-doc, funcs:7 | src/stackops/jobs/installer/checks/install_utils.py |  |
| `stackops.jobs.installer.checks.report_utils` | `python-api` | `high` | api-doc, classes:6, funcs:19 | src/stackops/jobs/installer/checks/report_utils.py |  |
| `stackops.jobs.installer.checks.vt_utils` | `python-api` | `high` | api-doc, classes:2, funcs:7 | src/stackops/jobs/installer/checks/vt_utils.py |  |
| `stackops.jobs.installer.package_groups` | `python-api` | `high` | api-doc | src/stackops/jobs/installer/package_groups.py |  |
| `stackops.logger` | `python-api` | `high` | api-doc, funcs:2 | src/stackops/logger.py |  |
| `stackops.profile.create_helper` | `python-api-candidate` | `medium` | funcs:2 | src/stackops/profile/create_helper.py |  |
| `stackops.profile.dotfiles_mapper` | `python-api-candidate` | `medium` | classes:1, funcs:11 | src/stackops/profile/dotfiles_mapper.py |  |
| `stackops.secrets` | `package` | `package-marker` | `medium` | __init__, assets, loader, models, paths, readers, search | src/stackops/secrets/__init__.py | Was a single module; now a package with submodules. |
| `stackops.utils.cloud.onedrive.auth` | `python-api-candidate` | `medium` | funcs:15 | src/stackops/utils/cloud/onedrive/auth.py |  |
| `stackops.utils.cloud.onedrive.file_ops` | `python-api-candidate` | `medium` | funcs:5 | src/stackops/utils/cloud/onedrive/file_ops.py |  |
| `stackops.utils.cloud.defaults` | `python-api` | `high` | api-doc, classes:1, funcs:1 | src/stackops/utils/cloud/defaults.py | Was `utils.cloud_defaults`; moved under `cloud/`. |
| `stackops.utils.code` | `python-api` | `high` | api-doc, funcs:11 | src/stackops/utils/code.py |  |
| `stackops.utils.cloud.encryption` | `python-api-candidate` | `medium` | funcs:1 | src/stackops/utils/cloud/encryption.py | Was `utils.encryption`; moved under `cloud/`. |
| `stackops.utils.files.f` | `python-api-candidate` | `medium` | classes:1, funcs:1 | src/stackops/utils/files/f.py |  |
| `stackops.utils.files.headers` | `python-api-candidate` | `medium` | funcs:2 | src/stackops/utils/files/headers.py |  |
| `stackops.utils.files.notebook` | `python-api-candidate` | `medium` | funcs:1 | src/stackops/utils/files/notebook.py |  |
| `stackops.utils.files.ouch.decompress` | `python-api-candidate` | `medium` | funcs:1 | src/stackops/utils/files/ouch/decompress.py |  |
| `stackops.utils.installer_utils.github_release_bulk` | `python-api` | `high` | api-doc, classes:3, funcs:6 | src/stackops/utils/installer_utils/github_release_bulk.py |  |
| `stackops.utils.installer_utils.github_release_scraper` | `python-api` | `high` | api-doc, funcs:5 | src/stackops/utils/installer_utils/github_release_scraper.py |  |
| `stackops.utils.installer_utils.install_from_url` | `python-api` | `high` | api-doc, classes:1, funcs:7 | src/stackops/utils/installer_utils/install_from_url.py |  |
| `stackops.utils.installer_utils.install_request_logic` | `python-api` | `high` | api-doc, classes:2, funcs:5 | src/stackops/utils/installer_utils/install_request_logic.py |  |
| `stackops.utils.installer_utils.installer_class` | `python-api` | `high` | api-doc, classes:1 | src/stackops/utils/installer_utils/installer_class.py |  |
| `stackops.utils.installer_utils.installer_helper` | `python-api` | `high` | api-doc, funcs:6 | src/stackops/utils/installer_utils/installer_helper.py |  |
| `stackops.utils.installer_utils.installer_locator_utils` | `python-api` | `high` | api-doc, funcs:13 | src/stackops/utils/installer_utils/installer_locator_utils.py |  |
| `stackops.utils.installer_utils.installer_offline_constants` | `python-api` | `high` | api-doc, funcs:2 | src/stackops/utils/installer_utils/installer_offline_constants.py |  |
| `stackops.utils.installer_utils.installer_offline_models` | `python-api` | `high` | api-doc, classes:4 | src/stackops/utils/installer_utils/installer_offline_models.py |  |
| `stackops.utils.installer_utils.installer_offline_publish` | `python-api` | `high` | api-doc, funcs:6 | src/stackops/utils/installer_utils/installer_offline_publish.py |  |
| `stackops.utils.installer_utils.installer_offline_render` | `python-api` | `high` | api-doc, funcs:3 | src/stackops/utils/installer_utils/installer_offline_render.py |  |
| `stackops.utils.installer_utils.installer_offline_scripts` | `python-api` | `high` | api-doc, funcs:1 | src/stackops/utils/installer_utils/installer_offline_scripts.py |  |
| `stackops.utils.installer_utils.installer_offline_steps` | `python-api` | `high` | api-doc, funcs:3 | src/stackops/utils/installer_utils/installer_offline_steps.py |  |
| `stackops.utils.installer_utils.installer_offline_uv` | `python-api` | `high` | api-doc, funcs:6 | src/stackops/utils/installer_utils/installer_offline_uv.py |  |
| `stackops.utils.installer_utils.installer_runner` | `python-api` | `high` | api-doc, funcs:6 | src/stackops/utils/installer_utils/installer_runner.py |  |
| `stackops.utils.installer_utils.installer_summary` | `python-api` | `high` | api-doc, funcs:8 | src/stackops/utils/installer_utils/installer_summary.py |  |
| `stackops.utils.io` | `python-api` | `high` | api-doc, classes:1, funcs:24 | src/stackops/utils/io.py |  |
| `stackops.utils.options` | `python-api` | `high` | api-doc, funcs:8 | src/stackops/utils/options_utils/options.py | Was `utils.options`; moved under `options_utils/`. |
| `stackops.utils.options_utils.textual_options_form` | `python-api-candidate` | `medium` | classes:5, funcs:12 | src/stackops/utils/options_utils/textual_options_form.py |  |
| `stackops.utils.path_core` | `python-api` | `high` | api-doc, __all__, funcs:20 | src/stackops/utils/path_core.py |  |
| `stackops.utils.path_reference` | `python-api` | `high` | api-doc, funcs:3 | src/stackops/utils/path_reference.py |  |
| `stackops.utils.cloud.rclone` | `python-api-candidate` | `medium` | classes:1, funcs:10 | src/stackops/utils/cloud/rclone.py | Was `utils.rclone`; moved under `cloud/`. |
| `stackops.utils.cloud.rclone_wrapper` | `python-api-candidate` | `medium` | funcs:8 | src/stackops/utils/cloud/rclone_wrapper.py | Was `utils.rclone_wrapper`; moved under `cloud/`. |
| `stackops.cluster.scheduler` | `python-api` | `high` | api-doc, classes:4, funcs:2 | src/stackops/cluster/scheduler.py | Was `utils.scheduler`; moved to `cluster/`. |
| `stackops.utils.schemas.config.config_types` | `python-api-candidate` | `medium` | - | src/stackops/utils/schemas/config/config_types.py |  |
| `stackops.utils.schemas.fire_agents.fire_agents_input` | `python-api-candidate` | `medium` | classes:6 | src/stackops/utils/schemas/fire_agents/fire_agents_input.py |  |
| `stackops.utils.schemas.installer.installer_types` | `python-api` | `high` | api-doc, classes:6, funcs:2 | src/stackops/utils/schemas/installer/installer_types.py |  |
| `stackops.utils.schemas.layouts.layout_types` | `python-api` | `high` | api-doc, classes:3, funcs:2 | src/stackops/utils/schemas/layouts/layout_types.py |  |
| `stackops.utils.schemas.repos.repos_types` | `python-api-candidate` | `medium` | classes:4 | src/stackops/utils/schemas/repos/repos_types.py |  |
| `stackops.utils.ssh_utils.abc` | `python-api-candidate` | `medium` | - | src/stackops/utils/ssh_utils/abc.py |  |
| `stackops.utils.ssh_utils.wsl_helper` | `python-api-candidate` | `medium` | funcs:15 | src/stackops/utils/ssh_utils/wsl_helper.py |  |
| `stackops.utils.cli_utils.terminal` | `python-api-candidate` | `medium` | classes:2 | src/stackops/utils/cli_utils/terminal.py | Was `utils.terminal`; moved under `cli_utils/`. |
| `stackops.utils.schemas.yaml_schema` | `python-api-candidate` | `medium` | funcs:3 | src/stackops/utils/schemas/yaml_schema.py | Was `utils.yaml_schema`; moved under `schemas/`. |

## Clear CLI And CLI Helpers

These **263** modules are likely direct CLI modules or CLI-only implementation helpers.

| Module | Marker | Label | Confidence | Signals | Path | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `stackops.scripts.python.agents` | `cli` | `cli-entrypoint` | `high` | entry:agents, typer, typer-app, cli-registration, get_app, main, __main__, funcs:10 | src/stackops/scripts/python/agents.py |  |
| `stackops.scripts.python.agents_browser` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:3 | src/stackops/scripts/python/agents_browser.py |  |
| `stackops.scripts.python.agents_parallel` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:1 | src/stackops/scripts/python/agents_parallel.py |  |
| `stackops.scripts.python.agents_parallel_commands` | `cli` | `cli-module` | `high` | typer, funcs:5 | src/stackops/scripts/python/agents_parallel_commands.py |  |
| `stackops.scripts.python.agents_parallel_run_command` | `cli` | `cli-module` | `high` | typer, funcs:1 | src/stackops/scripts/python/agents_parallel_run_command.py |  |
| `stackops.scripts.python.ai.initai` | `cli-helper` | `cli-helper` | `medium` | funcs:4 | src/stackops/scripts/python/ai/initai.py |  |
| `stackops.scripts.python.ai.scripts.dashboard` | `cli-helper` | `cli-helper` | `medium` | funcs:6 | src/stackops/scripts/python/ai/scripts/dashboard.py |  |
| `stackops.scripts.python.ai.scripts.lint_and_type_check` | `cli-helper` | `cli-helper` | `medium` | main, __main__, funcs:9 | src/stackops/scripts/python/ai/scripts/lint_and_type_check.py |  |
| `stackops.scripts.python.ai.scripts.models` | `cli-helper` | `cli-helper` | `medium` | __all__, classes:5 | src/stackops/scripts/python/ai/scripts/models.py |  |
| `stackops.scripts.python.ai.scripts.models_config` | `cli-helper` | `cli-helper` | `medium` | funcs:13 | src/stackops/scripts/python/ai/scripts/models_config.py |  |
| `stackops.scripts.python.ai.scripts.models_diagnostics` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:8 | src/stackops/scripts/python/ai/scripts/models_diagnostics.py |  |
| `stackops.scripts.python.ai.scripts.models_json` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:5 | src/stackops/scripts/python/ai/scripts/models_json.py |  |
| `stackops.scripts.python.ai.scripts.models_reports` | `cli-helper` | `cli-helper` | `medium` | funcs:12 | src/stackops/scripts/python/ai/scripts/models_reports.py |  |
| `stackops.scripts.python.ai.scripts.paths` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/ai/scripts/paths.py |  |
| `stackops.scripts.python.ai.solutions.antigravity.antigravity` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/ai/solutions/antigravity/antigravity.py |  |
| `stackops.scripts.python.ai.solutions.auggie.auggie` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/ai/solutions/auggie/auggie.py |  |
| `stackops.scripts.python.ai.solutions.claude.claude` | `cli-helper` | `cli-helper` | `medium` | funcs:4 | src/stackops/scripts/python/ai/solutions/claude/claude.py |  |
| `stackops.scripts.python.ai.solutions.cline.cline` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/ai/solutions/cline/cline.py |  |
| `stackops.scripts.python.ai.solutions.codex.codex` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/ai/solutions/codex/codex.py |  |
| `stackops.scripts.python.ai.solutions.copilot.github_copilot` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/ai/solutions/copilot/github_copilot.py |  |
| `stackops.scripts.python.ai.solutions.crush.crush` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/ai/solutions/crush/crush.py |  |
| `stackops.scripts.python.ai.solutions.cursor.cursors` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/ai/solutions/cursor/cursors.py |  |
| `stackops.scripts.python.ai.solutions.droid.droid` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/ai/solutions/droid/droid.py |  |
| `stackops.scripts.python.ai.solutions.forge.forge` | `cli-helper` | `cli-helper` | `medium` | funcs:4 | src/stackops/scripts/python/ai/solutions/forge/forge.py |  |
| `stackops.scripts.python.ai.solutions.kilocode.kilocode` | `cli-helper` | `cli-helper` | `medium` | funcs:4 | src/stackops/scripts/python/ai/solutions/kilocode/kilocode.py |  |
| `stackops.scripts.python.ai.solutions.opencode.opencode` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/ai/solutions/opencode/opencode.py |  |
| `stackops.scripts.python.ai.solutions.oz.oz` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/ai/solutions/oz/oz.py |  |
| `stackops.scripts.python.ai.solutions.pi.pi` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/ai/solutions/pi/pi.py |  |
| `stackops.scripts.python.ai.solutions.q.amazon_q` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/ai/solutions/q/amazon_q.py |  |
| `stackops.scripts.python.ai.solutions.qwen_code.qwen_code` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/ai/solutions/qwen_code/qwen_code.py |  |
| `stackops.scripts.python.ai.solutions.warp.warp` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/ai/solutions/warp/warp.py |  |
| `stackops.scripts.python.ai.utils.generate_files` | `cli` | `cli-module` | `high` | typer, cli-registration, __main__, funcs:16 | src/stackops/scripts/python/ai/utils/generate_files.py |  |
| `stackops.scripts.python.ai.utils.generic` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/ai/utils/generic.py |  |
| `stackops.scripts.python.ai.utils.shared` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/ai/utils/shared.py |  |
| `stackops.scripts.python.ai.utils.vscode_tasks` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/ai/utils/vscode_tasks.py |  |
| `stackops.scripts.python.cloud` | `cli` | `cli-entrypoint` | `high` | entry:cloud, typer, typer-app, cli-registration, get_app, main, __main__, funcs:6 | src/stackops/scripts/python/cloud.py |  |
| `stackops.scripts.python.devops` | `cli` | `cli-entrypoint` | `high` | entry:devops, typer, typer-app, cli-registration, get_app, main, classes:1, funcs:13 | src/stackops/scripts/python/devops.py |  |
| `stackops.scripts.python.enums` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/enums.py |  |
| `stackops.scripts.python.fire_jobs` | `cli` | `cli-entrypoint` | `high` | entry:fire, typer, typer-app, cli-registration, get_app, main, __main__, funcs:3 | src/stackops/scripts/python/fire_jobs.py |  |
| `stackops.scripts.python.ftpx` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, main, __main__, funcs:2 | src/stackops/scripts/python/ftpx.py |  |
| `stackops.scripts.python.graph.cli_graph_apps` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/graph/cli_graph_apps.py |  |
| `stackops.scripts.python.graph.cli_graph_eval` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/graph/cli_graph_eval.py |  |
| `stackops.scripts.python.graph.cli_graph_node_utils` | `cli-helper` | `cli-helper` | `medium` | funcs:6 | src/stackops/scripts/python/graph/cli_graph_node_utils.py |  |
| `stackops.scripts.python.graph.cli_graph_nodes` | `cli-helper` | `cli-helper` | `medium` | funcs:5 | src/stackops/scripts/python/graph/cli_graph_nodes.py |  |
| `stackops.scripts.python.graph.cli_graph_registration` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/graph/cli_graph_registration.py |  |
| `stackops.scripts.python.graph.cli_graph_resolver` | `cli-helper` | `cli-helper` | `medium` | funcs:12 | src/stackops/scripts/python/graph/cli_graph_resolver.py |  |
| `stackops.scripts.python.graph.cli_graph_shared` | `cli-helper` | `cli-helper` | `medium` | classes:6 | src/stackops/scripts/python/graph/cli_graph_shared.py |  |
| `stackops.scripts.python.graph.cli_graph_signature` | `cli-helper` | `cli-helper` | `medium` | funcs:9 | src/stackops/scripts/python/graph/cli_graph_signature.py |  |
| `stackops.scripts.python.graph.cli_graph_targets` | `cli-helper` | `cli-helper` | `medium` | funcs:8 | src/stackops/scripts/python/graph/cli_graph_targets.py |  |
| `stackops.scripts.python.graph.cli_graph_tree` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/graph/cli_graph_tree.py |  |
| `stackops.scripts.python.graph.cli_graph_values` | `cli-helper` | `cli-helper` | `medium` | funcs:5 | src/stackops/scripts/python/graph/cli_graph_values.py |  |
| `stackops.scripts.python.graph.generate_cli_graph` | `cli-helper` | `cli-helper` | `medium` | main, __main__, funcs:1 | src/stackops/scripts/python/graph/generate_cli_graph.py |  |
| `stackops.scripts.python.graph.visualize.cli_graph_app` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, main, __main__, funcs:7 | src/stackops/scripts/python/graph/visualize/cli_graph_app.py |  |
| `stackops.scripts.python.graph.visualize.cli_graph_search` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:30 | src/stackops/scripts/python/graph/visualize/cli_graph_search.py |  |
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
| `stackops.scripts.python.graph.visualize.plotly_views` | `cli-helper` | `cli-helper` | `medium` | __main__, funcs:2 | src/stackops/scripts/python/graph/visualize/plotly_views.py |  |
| `stackops.scripts.python.graph.visualize.rich_tree` | `cli-helper` | `cli-helper` | `medium` | funcs:4 | src/stackops/scripts/python/graph/visualize/rich_tree.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agent_impl_interactive.common` | `cli-helper` | `cli-helper` | `medium` | funcs:16 | src/stackops/scripts/python/helpers/helpers_agents/agent_impl_interactive/common.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agent_impl_interactive.create_options` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:25 | src/stackops/scripts/python/helpers/helpers_agents/agent_impl_interactive/create_options.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agent_impl_interactive.main` | `cli-helper` | `cli-helper` | `medium` | main, classes:1, funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agent_impl_interactive/main.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_codex` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agentic_frameworks/fire_codex.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_copilot` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agentic_frameworks/fire_copilot.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_crush` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agentic_frameworks/fire_crush.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_cursor_agents` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agentic_frameworks/fire_cursor_agents.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_pi` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agentic_frameworks/fire_pi.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_qwen` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agentic_frameworks/fire_qwen.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_ask_impl` | `cli-helper` | `cli-helper` | `medium` | funcs:13 | src/stackops/scripts/python/helpers/helpers_agents/agents_ask_impl.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_constants` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_constants.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_guides` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_guides.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_impl` | `cli-helper` | `cli-helper` | `medium` | classes:3, funcs:6 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_impl.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_resolution` | `cli-helper` | `cli-helper` | `medium` | funcs:11 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_resolution.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_create_artifacts` | `cli-helper` | `cli-helper` | `medium` | classes:4, funcs:10 | src/stackops/scripts/python/helpers/helpers_agents/agents_create_artifacts.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_create_inputs` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:5 | src/stackops/scripts/python/helpers/helpers_agents/agents_create_inputs.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_impl` | `cli` | `cli-module` | `high` | typer, funcs:12 | src/stackops/scripts/python/helpers/helpers_agents/agents_impl.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_mcp_impl` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_mcp_impl.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_parallel_add_entry` | `cli-helper` | `cli-helper` | `medium` | funcs:9 | src/stackops/scripts/python/helpers/helpers_agents/agents_parallel_add_entry.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_parallel_run_config` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:9 | src/stackops/scripts/python/helpers/helpers_agents/agents_parallel_run_config.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_parallel_run_impl` | `cli` | `cli-module` | `high` | typer, funcs:10 | src/stackops/scripts/python/helpers/helpers_agents/agents_parallel_run_impl.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_parallel_run_yaml` | `cli-helper` | `cli-helper` | `medium` | funcs:18 | src/stackops/scripts/python/helpers/helpers_agents/agents_parallel_run_yaml.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_parallel_yaml_defaults` | `cli-helper` | `cli-helper` | `medium` | classes:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_parallel_yaml_defaults.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_rich_output` | `cli-helper` | `cli-helper` | `medium` | funcs:12 | src/stackops/scripts/python/helpers/helpers_agents/agents_rich_output.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_run_context` | `cli` | `cli-module` | `high` | typer, funcs:17 | src/stackops/scripts/python/helpers/helpers_agents/agents_run_context.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_run_impl` | `cli` | `cli-module` | `high` | typer, funcs:12 | src/stackops/scripts/python/helpers/helpers_agents/agents_run_impl.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_shell` | `cli-helper` | `cli-helper` | `medium` | funcs:13 | src/stackops/scripts/python/helpers/helpers_agents/agents_shell.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_skill_impl` | `cli-helper` | `cli-helper` | `medium` | funcs:9 | src/stackops/scripts/python/helpers/helpers_agents/agents_skill_impl.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_yaml_schemas` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_yaml_schemas.py |  |
| `stackops.scripts.python.helpers.helpers_agents.fire_agents_help_launch` | `cli-helper` | `cli-helper` | `medium` | funcs:7 | src/stackops/scripts/python/helpers/helpers_agents/fire_agents_help_launch.py |  |
| `stackops.scripts.python.helpers.helpers_agents.fire_agents_help_search` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/fire_agents_help_search.py |  |
| `stackops.scripts.python.helpers.helpers_agents.fire_agents_helper_types` | `cli-helper` | `cli-helper` | `medium` | classes:2 | src/stackops/scripts/python/helpers/helpers_agents/fire_agents_helper_types.py |  |
| `stackops.scripts.python.helpers.helpers_agents.fire_agents_load_balancer` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/fire_agents_load_balancer.py |  |
| `stackops.scripts.python.helpers.helpers_agents.mcp_catalog` | `cli-helper` | `cli-helper` | `medium` | funcs:17 | src/stackops/scripts/python/helpers/helpers_agents/mcp_catalog.py |  |
| `stackops.scripts.python.helpers.helpers_agents.mcp_install` | `cli-helper` | `cli-helper` | `medium` | funcs:33 | src/stackops/scripts/python/helpers/helpers_agents/mcp_install.py |  |
| `stackops.scripts.python.helpers.helpers_agents.mcp_types` | `cli-helper` | `cli-helper` | `medium` | classes:5 | src/stackops/scripts/python/helpers/helpers_agents/mcp_types.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.auggie.auggie_privacy` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/auggie/auggie_privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.chatgpt.chatgpt_privacy` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/chatgpt/chatgpt_privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.cline.cline_privacy` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/cline/cline_privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.codex.codex_privacy` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/codex/codex_privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.common.privacy_orchestrator` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/common/privacy_orchestrator.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.cursor.cursor_privacy` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/cursor/cursor_privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.droid.droid_privacy` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/droid/droid_privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.kilocode.kilocode_privacy` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/kilocode/kilocode_privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.mods.mods_privacy` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/mods/mods_privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.q.q_privacy` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/q/q_privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.qwen.qwen_privacy` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/qwen/qwen_privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.privacy` | `cli-helper` | `cli-helper` | `medium` | __main__, __all__ | src/stackops/scripts/python/helpers/helpers_agents/privacy/privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.reasoning_capabilities` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:6 | src/stackops/scripts/python/helpers/helpers_agents/reasoning_capabilities.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.cloud_copy` | `cli-helper` | `cli-helper` | `medium` | main, classes:1, funcs:12 | src/stackops/scripts/python/helpers/helpers_cloud/cloud_copy.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.cloud_helpers` | `cli-helper` | `cli-helper` | `medium` | funcs:8 | src/stackops/scripts/python/helpers/helpers_cloud/cloud_helpers.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.cloud_mount` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, __main__, funcs:4 | src/stackops/scripts/python/helpers/helpers_cloud/cloud_mount.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.cloud_mount_tmux` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_cloud/cloud_mount_tmux.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.cloud_mount_zellij` | `cli-helper` | `cli-helper` | `medium` | funcs:5 | src/stackops/scripts/python/helpers/helpers_cloud/cloud_mount_zellij.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.cloud_path_resolver` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_cloud/cloud_path_resolver.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.cloud_sync` | `cli-helper` | `cli-helper` | `medium` | main, funcs:1 | src/stackops/scripts/python/helpers/helpers_cloud/cloud_sync.py |  |
| `stackops.scripts.python.helpers.helpers_devops.backup_config` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:20 | src/stackops/scripts/python/helpers/helpers_devops/backup_config.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_backup_retrieve` | `cli-helper` | `cli-helper` | `medium` | __main__, funcs:12 | src/stackops/scripts/python/helpers/helpers_devops/cli_backup_retrieve.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, classes:1, funcs:22 | src/stackops/scripts/python/helpers/helpers_devops/cli_config.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_mapper` | `cli` | `cli-module` | `high` | typer, cli-registration, __main__, funcs:16 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_dotfile_mapper.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_transfer` | `cli` | `cli-module` | `high` | typer, funcs:5 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_dotfile_transfer.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_mount` | `cli` | `cli-module` | `high` | typer, funcs:5 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_mount.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:7 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_actions` | `cli` | `cli-module` | `high` | typer, funcs:33 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets_actions.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_candidates` | `cli` | `cli-module` | `high` | typer, __all__, classes:2, funcs:20 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets_candidates.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_interactive` | `cli` | `cli-module` | `high` | typer, classes:1, funcs:7 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets_interactive.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_support` | `cli` | `cli-module` | `high` | typer, classes:2, funcs:32 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets_support.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_terminal` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:8 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_terminal.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_tmux` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, classes:1, funcs:20 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_tmux.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_data` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:8 | src/stackops/scripts/python/helpers/helpers_devops/cli_data.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_device` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:8 | src/stackops/scripts/python/helpers/helpers_devops/cli_device.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_nw` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/cli_nw.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_nw_vscode_share` | `cli-helper` | `cli-helper` | `medium` | funcs:7 | src/stackops/scripts/python/helpers/helpers_devops/cli_nw_vscode_share.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_repos` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:15 | src/stackops/scripts/python/helpers/helpers_devops/cli_repos.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:14 | src/stackops/scripts/python/helpers/helpers_devops/cli_self.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self_ai.app` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/cli_self_ai/app.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self_ai.update_docs` | `cli` | `cli-module` | `high` | typer, funcs:9 | src/stackops/scripts/python/helpers/helpers_devops/cli_self_ai/update_docs.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self_ai.update_installer` | `cli` | `cli-module` | `high` | typer, funcs:8 | src/stackops/scripts/python/helpers/helpers_devops/cli_self_ai/update_installer.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self_ai.update_logic` | `cli` | `cli-module` | `high` | typer, classes:1, funcs:11 | src/stackops/scripts/python/helpers/helpers_devops/cli_self_ai/update_logic.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self_ai.update_test` | `cli` | `cli-module` | `high` | typer, funcs:6 | src/stackops/scripts/python/helpers/helpers_devops/cli_self_ai/update_test.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self_ai.workflow_capture` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/cli_self_ai/workflow_capture.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self_ai.workflows_yaml` | `cli-helper` | `cli-helper` | `medium` | __main__, funcs:12 | src/stackops/scripts/python/helpers/helpers_devops/cli_self_ai/workflows_yaml.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self_assets` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/cli_self_assets.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self_docker` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:14 | src/stackops/scripts/python/helpers/helpers_devops/cli_self_docker.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self_docs` | `cli` | `cli-module` | `high` | typer, classes:1, funcs:10 | src/stackops/scripts/python/helpers/helpers_devops/cli_self_docs.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_share_file` | `cli` | `cli-module` | `high` | typer, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/cli_share_file.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_share_server` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, __main__, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/cli_share_server.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_share_temp` | `cli` | `cli-module` | `high` | typer, classes:1, funcs:5 | src/stackops/scripts/python/helpers/helpers_devops/cli_share_temp.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_share_terminal` | `cli` | `cli-module` | `high` | typer, cli-registration, __main__, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/cli_share_terminal.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_ssh` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:8 | src/stackops/scripts/python/helpers/helpers_devops/cli_ssh.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_vault` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:5 | src/stackops/scripts/python/helpers/helpers_devops/cli_vault.py |  |
| `stackops.scripts.python.helpers.helpers_devops.devops_status` | `cli-helper` | `cli-helper` | `medium` | main, __main__, funcs:10 | src/stackops/scripts/python/helpers/helpers_devops/devops_status.py |  |
| `stackops.scripts.python.helpers.helpers_devops.devops_status_checks` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:9 | src/stackops/scripts/python/helpers/helpers_devops/devops_status_checks.py |  |
| `stackops.scripts.python.helpers.helpers_devops.devops_status_display` | `cli-helper` | `cli-helper` | `medium` | funcs:9 | src/stackops/scripts/python/helpers/helpers_devops/devops_status_display.py |  |
| `stackops.scripts.python.helpers.helpers_devops.devops_update_repos` | `cli-helper` | `cli-helper` | `medium` | main, __main__, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/devops_update_repos.py |  |
| `stackops.scripts.python.helpers.helpers_devops.interactive` | `cli-helper` | `cli-helper` | `medium` | main, __main__, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/interactive.py |  |
| `stackops.scripts.python.helpers.helpers_devops.mount_helpers.commands` | `cli-helper` | `cli-helper` | `medium` | funcs:5 | src/stackops/scripts/python/helpers/helpers_devops/mount_helpers/commands.py |  |
| `stackops.scripts.python.helpers.helpers_devops.mount_helpers.device_entry` | `cli-helper` | `cli-helper` | `medium` | classes:1 | src/stackops/scripts/python/helpers/helpers_devops/mount_helpers/device_entry.py |  |
| `stackops.scripts.python.helpers.helpers_devops.mount_helpers.devices` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/mount_helpers/devices.py |  |
| `stackops.scripts.python.helpers.helpers_devops.mount_helpers.linux` | `cli-helper` | `cli-helper` | `medium` | funcs:10 | src/stackops/scripts/python/helpers/helpers_devops/mount_helpers/linux.py |  |
| `stackops.scripts.python.helpers.helpers_devops.mount_helpers.macos` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/mount_helpers/macos.py |  |
| `stackops.scripts.python.helpers.helpers_devops.mount_helpers.selection` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_devops/mount_helpers/selection.py |  |
| `stackops.scripts.python.helpers.helpers_devops.mount_helpers.utils` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/mount_helpers/utils.py |  |
| `stackops.scripts.python.helpers.helpers_devops.mount_helpers.windows` | `cli-helper` | `cli-helper` | `medium` | funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/mount_helpers/windows.py |  |
| `stackops.scripts.python.helpers.helpers_devops.register_interactive` | `cli` | `cli-module` | `high` | typer, funcs:6 | src/stackops/scripts/python/helpers/helpers_devops/register_interactive.py |  |
| `stackops.scripts.python.helpers.helpers_devops.run_script` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:5 | src/stackops/scripts/python/helpers/helpers_devops/run_script.py |  |
| `stackops.scripts.python.helpers.helpers_devops.themes.choose_wezterm_theme` | `cli-helper` | `cli-helper` | `medium` | main, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/themes/choose_wezterm_theme.py |  |
| `stackops.scripts.python.helpers.helpers_devops.vault` | `cli-helper` | `cli-helper` | `medium` | classes:4, funcs:23 | src/stackops/scripts/python/helpers/helpers_devops/vault.py |  |
| `stackops.scripts.python.helpers.helpers_env.env_manager_tui` | `cli-helper` | `cli-helper` | `medium` | main, __main__, classes:4, funcs:4 | src/stackops/scripts/python/helpers/helpers_env/env_manager_tui.py |  |
| `stackops.scripts.python.helpers.helpers_env.path_manager_backend` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_env/path_manager_backend.py |  |
| `stackops.scripts.python.helpers.helpers_env.path_manager_tui` | `cli-helper` | `cli-helper` | `medium` | main, __main__, classes:3, funcs:1 | src/stackops/scripts/python/helpers/helpers_env/path_manager_tui.py |  |
| `stackops.scripts.python.helpers.helpers_fire_command.cloud_manager` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_fire_command/cloud_manager.py |  |
| `stackops.scripts.python.helpers.helpers_fire_command.f` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_fire_command/f.py |  |
| `stackops.scripts.python.helpers.helpers_fire_command.file_wrangler` | `cli-helper` | `cli-helper` | `medium` | funcs:5 | src/stackops/scripts/python/helpers/helpers_fire_command/file_wrangler.py |  |
| `stackops.scripts.python.helpers.helpers_fire_command.fire_jobs_args_helper` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_fire_command/fire_jobs_args_helper.py |  |
| `stackops.scripts.python.helpers.helpers_fire_command.fire_jobs_impl` | `cli-helper` | `cli-helper` | `medium` | funcs:11 | src/stackops/scripts/python/helpers/helpers_fire_command/fire_jobs_impl.py |  |
| `stackops.scripts.python.helpers.helpers_fire_command.fire_jobs_route_helper` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_fire_command/fire_jobs_route_helper.py |  |
| `stackops.scripts.python.helpers.helpers_fire_command.fire_jobs_streamlit_helper` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_fire_command/fire_jobs_streamlit_helper.py |  |
| `stackops.scripts.python.helpers.helpers_preview.pomodoro` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_preview/pomodoro.py |  |
| `stackops.scripts.python.helpers.helpers_preview.preview_impl` | `cli-helper` | `cli-helper` | `medium` | funcs:5 | src/stackops/scripts/python/helpers/helpers_preview/preview_impl.py |  |
| `stackops.scripts.python.helpers.helpers_preview.preview_read` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_preview/preview_read.py |  |
| `stackops.scripts.python.helpers.helpers_preview.scheduler` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_preview/scheduler.py |  |
| `stackops.scripts.python.helpers.helpers_preview.start_slidev` | `cli` | `cli-module` | `high` | typer, cli-registration, main, __main__, funcs:4 | src/stackops/scripts/python/helpers/helpers_preview/start_slidev.py |  |
| `stackops.scripts.python.helpers.helpers_preview.viewer` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_preview/viewer.py |  |
| `stackops.scripts.python.helpers.helpers_preview.viewer_template` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_preview/viewer_template.py |  |
| `stackops.scripts.python.helpers.helpers_repos.action` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_repos/action.py |  |
| `stackops.scripts.python.helpers.helpers_repos.action_helper` | `cli-helper` | `cli-helper` | `medium` | classes:3, funcs:1 | src/stackops/scripts/python/helpers/helpers_repos/action_helper.py |  |
| `stackops.scripts.python.helpers.helpers_repos.clone` | `cli-helper` | `cli-helper` | `medium` | funcs:6 | src/stackops/scripts/python/helpers/helpers_repos/clone.py |  |
| `stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync` | `cli` | `cli-module` | `high` | typer, main, classes:1, funcs:15 | src/stackops/scripts/python/helpers/helpers_repos/cloud_repo_sync.py |  |
| `stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_conflicts` | `cli-helper` | `cli-helper` | `medium` | funcs:5 | src/stackops/scripts/python/helpers/helpers_repos/cloud_repo_sync_conflicts.py |  |
| `stackops.scripts.python.helpers.helpers_repos.grource` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, __main__, funcs:6 | src/stackops/scripts/python/helpers/helpers_repos/grource.py |  |
| `stackops.scripts.python.helpers.helpers_repos.record` | `cli` | `cli-module` | `high` | typer, funcs:12 | src/stackops/scripts/python/helpers/helpers_repos/record.py |  |
| `stackops.scripts.python.helpers.helpers_repos.repo_analyzer_1` | `cli-helper` | `cli-helper` | `medium` | funcs:5 | src/stackops/scripts/python/helpers/helpers_repos/repo_analyzer_1.py |  |
| `stackops.scripts.python.helpers.helpers_repos.repo_analyzer_2` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:2 | src/stackops/scripts/python/helpers/helpers_repos/repo_analyzer_2.py |  |
| `stackops.scripts.python.helpers.helpers_repos.spec_store` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:10 | src/stackops/scripts/python/helpers/helpers_repos/spec_store.py |  |
| `stackops.scripts.python.helpers.helpers_repos.sync` | `cli-helper` | `cli-helper` | `medium` | funcs:4 | src/stackops/scripts/python/helpers/helpers_repos/sync.py |  |
| `stackops.scripts.python.helpers.helpers_repos.update` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_repos/update.py |  |
| `stackops.scripts.python.helpers.helpers_search.ast_search` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:9 | src/stackops/scripts/python/helpers/helpers_search/ast_search.py |  |
| `stackops.scripts.python.helpers.helpers_search.qr_code` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_search/qr_code.py |  |
| `stackops.scripts.python.helpers.helpers_search.repo_rag` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_search/repo_rag.py |  |
| `stackops.scripts.python.helpers.helpers_search.script_help` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_search/script_help.py |  |
| `stackops.scripts.python.helpers.helpers_search.semantic_search` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/scripts/python/helpers/helpers_search/semantic_search.py |  |
| `stackops.scripts.python.helpers.helpers_seek.seek_impl` | `cli-helper` | `cli-helper` | `medium` | funcs:18 | src/stackops/scripts/python/helpers/helpers_seek/seek_impl.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._herdr_backend` | `cli-helper` | `cli-helper` | `medium` | funcs:25 | src/stackops/scripts/python/helpers/helpers_sessions/_herdr_backend.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._tmux_backend` | `cli-helper` | `cli-helper` | `medium` | funcs:7 | src/stackops/scripts/python/helpers/helpers_sessions/_tmux_backend.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._tmux_backend_options` | `cli-helper` | `cli-helper` | `medium` | funcs:7 | src/stackops/scripts/python/helpers/helpers_sessions/_tmux_backend_options.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._tmux_backend_preview` | `cli-helper` | `cli-helper` | `medium` | funcs:9 | src/stackops/scripts/python/helpers/helpers_sessions/_tmux_backend_preview.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._tmux_backend_processes` | `cli-helper` | `cli-helper` | `medium` | funcs:7 | src/stackops/scripts/python/helpers/helpers_sessions/_tmux_backend_processes.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._zellij_backend` | `cli-helper` | `cli-helper` | `medium` | funcs:10 | src/stackops/scripts/python/helpers/helpers_sessions/_zellij_backend.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._zellij_backend_focus` | `cli-helper` | `cli-helper` | `medium` | funcs:7 | src/stackops/scripts/python/helpers/helpers_sessions/_zellij_backend_focus.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._zellij_backend_layout` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:4 | src/stackops/scripts/python/helpers/helpers_sessions/_zellij_backend_layout.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._zellij_backend_metadata` | `cli-helper` | `cli-helper` | `medium` | funcs:10 | src/stackops/scripts/python/helpers/helpers_sessions/_zellij_backend_metadata.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._zellij_backend_options` | `cli-helper` | `cli-helper` | `medium` | funcs:7 | src/stackops/scripts/python/helpers/helpers_sessions/_zellij_backend_options.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._zellij_backend_preview` | `cli-helper` | `cli-helper` | `medium` | funcs:5 | src/stackops/scripts/python/helpers/helpers_sessions/_zellij_backend_preview.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.attach_impl` | `cli-helper` | `cli-helper` | `medium` | funcs:9 | src/stackops/scripts/python/helpers/helpers_sessions/attach_impl.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.kill_impl` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_sessions/kill_impl.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.session_trace_tmux` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:6 | src/stackops/scripts/python/helpers/helpers_sessions/session_trace_tmux.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.session_trace_zellij` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_sessions/session_trace_zellij.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_aoe_impl` | `cli-helper` | `cli-helper` | `medium` | classes:2, funcs:12 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_aoe_impl.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_cli_common` | `cli` | `cli-module` | `high` | typer, funcs:6 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_cli_common.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_cli_run` | `cli` | `cli-module` | `high` | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_cli_run.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_cli_run_all` | `cli` | `cli-module` | `high` | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_cli_run_all.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_cli_run_aoe` | `cli` | `cli-module` | `high` | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_cli_run_aoe.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_dynamic` | `cli-helper` | `cli-helper` | `medium` | funcs:7 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_dynamic.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_dynamic_display` | `cli-helper` | `cli-helper` | `medium` | classes:3, funcs:11 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_dynamic_display.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_dynamic_tmux` | `cli-helper` | `cli-helper` | `medium` | funcs:9 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_dynamic_tmux.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_dynamic_zellij` | `cli-helper` | `cli-helper` | `medium` | funcs:6 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_dynamic_zellij.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_impl` | `cli-helper` | `cli-helper` | `medium` | __main__, funcs:5 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_impl.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_layout_source` | `cli` | `cli-module` | `high` | typer, classes:1, funcs:8 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_layout_source.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_multiprocess` | `cli` | `cli-module` | `high` | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_multiprocess.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_test_layouts` | `cli-helper` | `cli-helper` | `medium` | classes:1, funcs:5 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_test_layouts.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_trace` | `cli` | `cli-module` | `high` | typer, __all__, funcs:14 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_trace.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.utils` | `cli-helper` | `cli-helper` | `medium` | funcs:2 | src/stackops/scripts/python/helpers/helpers_sessions/utils.py |  |
| `stackops.scripts.python.helpers.helpers_utils.download` | `cli` | `cli-module` | `high` | typer, __main__, funcs:1 | src/stackops/scripts/python/helpers/helpers_utils/download.py |  |
| `stackops.scripts.python.helpers.helpers_utils.file_utils_app` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:8 | src/stackops/scripts/python/helpers/helpers_utils/file_utils_app.py |  |
| `stackops.scripts.python.helpers.helpers_utils.machine_utils_app` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:6 | src/stackops/scripts/python/helpers/helpers_utils/machine_utils_app.py |  |
| `stackops.scripts.python.helpers.helpers_utils.path_reference_validation` | `cli-helper` | `cli-helper` | `medium` | classes:4, funcs:14 | src/stackops/scripts/python/helpers/helpers_utils/path_reference_validation.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pdf` | `cli` | `cli-module` | `high` | typer, funcs:2 | src/stackops/scripts/python/helpers/helpers_utils/pdf.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_app` | `cli` | `cli-module` | `high` | typer, typer-app, cli-registration, get_app, funcs:12 | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_app.py |  |
| `stackops.scripts.python.helpers.helpers_utils.python` | `cli` | `cli-module` | `high` | typer, __main__, classes:1, funcs:12 | src/stackops/scripts/python/helpers/helpers_utils/python.py |  |
| `stackops.scripts.python.helpers.helpers_utils.read_db_cli_tui` | `cli-helper` | `cli-helper` | `medium` | funcs:1 | src/stackops/scripts/python/helpers/helpers_utils/read_db_cli_tui.py |  |
| `stackops.scripts.python.helpers.helpers_utils.read_db_cli_tui_backend` | `cli` | `cli-module` | `high` | typer, funcs:22 | src/stackops/scripts/python/helpers/helpers_utils/read_db_cli_tui_backend.py |  |
| `stackops.scripts.python.helpers.helpers_utils.scrape` | `cli` | `cli-module` | `high` | typer, funcs:3 | src/stackops/scripts/python/helpers/helpers_utils/scrape.py |  |
| `stackops.scripts.python.helpers.helpers_utils.specs` | `cli-helper` | `cli-helper` | `medium` | main, __main__, funcs:8 | src/stackops/scripts/python/helpers/helpers_utils/specs.py |  |
| `stackops.scripts.python.helpers.helpers_utils.surya` | `cli-helper` | `cli-helper` | `medium` | funcs:3 | src/stackops/scripts/python/helpers/helpers_utils/surya.py |  |
| `stackops.scripts.python.helpers.helpers_utils.test_runtime` | `cli` | `cli-module` | `high` | typer, typer-app, get_app, classes:1, funcs:11 | src/stackops/scripts/python/helpers/helpers_utils/test_runtime.py |  |
| `stackops.scripts.python.helpers.helpers_utils.type_fix` | `cli` | `cli-module` | `high` | typer, typer-app, get_app, funcs:5 | src/stackops/scripts/python/helpers/helpers_utils/type_fix.py |  |
| `stackops.scripts.python.preview` | `cli` | `cli-entrypoint` | `high` | entry:preview, typer, cli-registration, main, __main__, funcs:6 | src/stackops/scripts/python/preview.py |  |
| `stackops.scripts.python.seek` | `cli` | `cli-entrypoint` | `high` | entry:seek, typer, typer-app, cli-registration, get_app, main, funcs:4 | src/stackops/scripts/python/seek.py |  |
| `stackops.scripts.python.stackops_entry` | `cli` | `cli-entrypoint` | `high` | entry:stackops, typer, typer-app, cli-registration, get_app, main, __main__, funcs:11 | src/stackops/scripts/python/stackops_entry.py |  |
| `stackops.scripts.python.terminal` | `cli` | `cli-entrypoint` | `high` | entry:terminal, typer, typer-app, cli-registration, get_app, main, __main__, funcs:14 | src/stackops/scripts/python/terminal.py |  |
| `stackops.scripts.python.utils` | `cli` | `cli-entrypoint` | `high` | entry:utils, typer, typer-app, cli-registration, get_app, main, __main__, funcs:3 | src/stackops/scripts/python/utils.py |  |
| `stackops.utils.cli_utils.hierarchy` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/utils/cli_utils/hierarchy.py |  |
| `stackops.utils.cli_utils.hierarchy_types` | `cli-helper` | `cli-helper` | `medium` | - | src/stackops/utils/cli_utils/hierarchy_types.py |  |

## Assets And Package Markers

These **203** modules are package markers, settings/config packages, or executable assets.

| Module | Marker | Label | Confidence | Signals | Path | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `stackops` | `package` | `package-marker` | `high` | - | src/stackops/__init__.py |  |
| `stackops.cluster` | `package` | `package-marker` | `high` | api-doc | src/stackops/cluster/__init__.py |  |
| `stackops.cluster.remote` | `package` | `package-marker` | `high` | api-doc, __all__ | src/stackops/cluster/remote/__init__.py |  |
| `stackops.cluster.sessions_managers` | `package` | `package-marker` | `high` | api-doc | src/stackops/cluster/sessions_managers/__init__.py |  |
| `stackops.cluster.sessions_managers.tmux` | `package` | `package-marker` | `high` | api-doc | src/stackops/cluster/sessions_managers/tmux/__init__.py |  |
| `stackops.cluster.sessions_managers.utils` | `package` | `package-marker` | `high` | api-doc | src/stackops/cluster/sessions_managers/utils/__init__.py |  |
| `stackops.cluster.sessions_managers.windows_terminal` | `package` | `package-marker` | `high` | api-doc | src/stackops/cluster/sessions_managers/windows_terminal/__init__.py |  |
| `stackops.cluster.sessions_managers.windows_terminal.wt_utils.examples` | `package` | `package-marker` | `high` | api-doc | src/stackops/cluster/sessions_managers/windows_terminal/wt_utils/examples/__init__.py |  |
| `stackops.cluster.sessions_managers.zellij` | `package` | `package-marker` | `high` | api-doc | src/stackops/cluster/sessions_managers/zellij/__init__.py |  |
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
| `stackops.jobs.installer.python_scripts.brave` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:1 | src/stackops/jobs/installer/python_scripts/brave.py |  |
| `stackops.jobs.installer.python_scripts.bypass_paywall` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:1 | src/stackops/jobs/installer/python_scripts/bypass_paywall.py |  |
| `stackops.jobs.installer.python_scripts.cloudflare_warp_cli` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:1 | src/stackops/jobs/installer/python_scripts/cloudflare_warp_cli.py |  |
| `stackops.jobs.installer.python_scripts.code` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:1 | src/stackops/jobs/installer/python_scripts/code.py |  |
| `stackops.jobs.installer.python_scripts.cursor` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:3 | src/stackops/jobs/installer/python_scripts/cursor.py |  |
| `stackops.jobs.installer.python_scripts.docker` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:3 | src/stackops/jobs/installer/python_scripts/docker.py |  |
| `stackops.jobs.installer.python_scripts.dubdb_adbc` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:1 | src/stackops/jobs/installer/python_scripts/dubdb_adbc.py |  |
| `stackops.jobs.installer.python_scripts.espanso` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:4 | src/stackops/jobs/installer/python_scripts/espanso.py |  |
| `stackops.jobs.installer.python_scripts.goes` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, funcs:1 | src/stackops/jobs/installer/python_scripts/goes.py |  |
| `stackops.jobs.installer.python_scripts.hx` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:1 | src/stackops/jobs/installer/python_scripts/hx.py |  |
| `stackops.jobs.installer.python_scripts.lvim` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:1 | src/stackops/jobs/installer/python_scripts/lvim.py |  |
| `stackops.jobs.installer.python_scripts.main_protocol` | `script-asset` | `installer-script-asset` | `high` | api-doc, classes:1, funcs:2 | src/stackops/jobs/installer/python_scripts/main_protocol.py |  |
| `stackops.jobs.installer.python_scripts.nerdfont` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:17 | src/stackops/jobs/installer/python_scripts/nerdfont.py |  |
| `stackops.jobs.installer.python_scripts.orca` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:10 | src/stackops/jobs/installer/python_scripts/orca.py |  |
| `stackops.jobs.installer.python_scripts.poppler` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:2 | src/stackops/jobs/installer/python_scripts/poppler.py |  |
| `stackops.jobs.installer.python_scripts.redis` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:1 | src/stackops/jobs/installer/python_scripts/redis.py |  |
| `stackops.jobs.installer.python_scripts.rmpc` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:25 | src/stackops/jobs/installer/python_scripts/rmpc.py |  |
| `stackops.jobs.installer.python_scripts.sysabc` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:1 | src/stackops/jobs/installer/python_scripts/sysabc.py |  |
| `stackops.jobs.installer.python_scripts.termusic` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:20 | src/stackops/jobs/installer/python_scripts/termusic.py |  |
| `stackops.jobs.installer.python_scripts.wezterm` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:1 | src/stackops/jobs/installer/python_scripts/wezterm.py |  |
| `stackops.jobs.installer.python_scripts.winget` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:5 | src/stackops/jobs/installer/python_scripts/winget.py |  |
| `stackops.jobs.installer.python_scripts.yazi` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:1 | src/stackops/jobs/installer/python_scripts/yazi.py |  |
| `stackops.jobs.installer.python_scripts.youtube_tui` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:15 | src/stackops/jobs/installer/python_scripts/youtube_tui.py |  |
| `stackops.jobs.installer.python_scripts.ytui_music` | `script-asset` | `installer-script-asset` | `high` | api-doc, main, __main__, funcs:25 | src/stackops/jobs/installer/python_scripts/ytui_music.py |  |
| `stackops.jobs.scripts.bash_scripts` | `package` | `package-marker` | `high` | - | src/stackops/jobs/scripts/bash_scripts/__init__.py |  |
| `stackops.jobs.scripts.powershell_scripts` | `package` | `package-marker` | `high` | - | src/stackops/jobs/scripts/powershell_scripts/__init__.py |  |
| `stackops.jobs.scripts_dynamic` | `package` | `package-marker` | `high` | - | src/stackops/jobs/scripts_dynamic/__init__.py |  |
| `stackops.jobs.scripts_dynamic.download_stackops_offline_installer` | `script-asset` | `script-asset` | `medium` | main, __main__, classes:1, funcs:7 | src/stackops/jobs/scripts_dynamic/download_stackops_offline_installer.py |  |
| `stackops.jobs.scripts_dynamic.system_compute_analyzer` | `script-asset` | `script-asset` | `medium` | main, __main__, classes:4, funcs:2 | src/stackops/jobs/scripts_dynamic/system_compute_analyzer.py |  |
| `stackops.profile` | `package` | `package-marker` | `high` | - | src/stackops/profile/__init__.py |  |
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
| `stackops.scripts.python.ai.solutions.droid` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/ai/solutions/droid/__init__.py |  |
| `stackops.scripts.python.ai.solutions.forge` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/ai/solutions/forge/__init__.py |  |
| `stackops.scripts.python.ai.solutions.kilocode` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/ai/solutions/kilocode/__init__.py |  |
| `stackops.scripts.python.ai.solutions.opencode` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/ai/solutions/opencode/__init__.py |  |
| `stackops.scripts.python.ai.solutions.oz` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/ai/solutions/oz/__init__.py |  |
| `stackops.scripts.python.ai.solutions.pi` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/ai/solutions/pi/__init__.py |  |
| `stackops.scripts.python.ai.solutions.q` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/ai/solutions/q/__init__.py |  |
| `stackops.scripts.python.ai.solutions.qwen_code` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/ai/solutions/qwen_code/__init__.py |  |
| `stackops.scripts.python.ai.solutions.warp` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/ai/solutions/warp/__init__.py |  |
| `stackops.scripts.python.ai.utils` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/ai/utils/__init__.py |  |
| `stackops.scripts.python.graph` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/graph/__init__.py |  |
| `stackops.scripts.python.graph.visualize` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/graph/visualize/__init__.py |  |
| `stackops.scripts.python.graph.visualize.helpers_navigator` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/graph/visualize/helpers_navigator/__init__.py |  |
| `stackops.scripts.python.helpers` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_agents/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agent_impl_interactive` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_agents/agent_impl_interactive/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agentic_frameworks` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_agents/agentic_frameworks/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.browser_guides` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_agents/browser_guides/__init__.py |  |
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
| `stackops.scripts.python.helpers.helpers_agents.templates` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_agents/templates/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_cloud` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_cloud/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_devops` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_devops/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self_ai` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_devops/cli_self_ai/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_devops.mount_helpers` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_devops/mount_helpers/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_devops.themes` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_devops/themes/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_env` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_env/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_fire_command` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_fire_command/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_network` | `package` | `package-marker` | `high` | api-doc | src/stackops/scripts/python/helpers/helpers_network/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_network.ssh` | `package` | `package-marker` | `high` | api-doc, __all__, funcs:1 | src/stackops/scripts/python/helpers/helpers_network/ssh/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_preview` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_preview/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_seek` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_seek/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_seek.scripts_linux` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_seek/scripts_linux/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_seek.scripts_macos` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_seek/scripts_macos/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_seek.scripts_windows` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_seek/scripts_windows/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_sessions` | `package` | `package-marker` | `high` | - | src/stackops/scripts/python/helpers/helpers_sessions/__init__.py |  |
| `stackops.scripts.setup.linux` | `package` | `package-marker` | `high` | - | src/stackops/scripts/setup/linux/__init__.py |  |
| `stackops.scripts.setup.macos` | `package` | `package-marker` | `high` | - | src/stackops/scripts/setup/macos/__init__.py |  |
| `stackops.scripts.setup.windows` | `package` | `package-marker` | `high` | - | src/stackops/scripts/setup/windows/__init__.py |  |
| `stackops.scripts.windows` | `package` | `package-marker` | `high` | - | src/stackops/scripts/windows/__init__.py |  |
| `stackops.settings` | `package` | `package-marker` | `high` | - | src/stackops/settings/__init__.py |  |
| `stackops.settings.atuin` | `package` | `package-marker` | `high` | - | src/stackops/settings/atuin/__init__.py |  |
| `stackops.settings.atuin.themes` | `package` | `package-marker` | `high` | - | src/stackops/settings/atuin/themes/__init__.py |  |
| `stackops.settings.broot` | `package` | `package-marker` | `high` | - | src/stackops/settings/broot/__init__.py |  |
| `stackops.settings.glow` | `package` | `package-marker` | `high` | - | src/stackops/settings/glow/__init__.py |  |
| `stackops.settings.gromit-mpx` | `package` | `package-marker` | `high` | - | src/stackops/settings/gromit-mpx/__init__.py |  |
| `stackops.settings.helix` | `package` | `package-marker` | `high` | - | src/stackops/settings/helix/__init__.py |  |
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
| `stackops.settings.shells.bash` | `package` | `package-marker` | `high` | - | src/stackops/settings/shells/bash/__init__.py |  |
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
| `stackops.settings.shells.zsh` | `package` | `package-marker` | `high` | - | src/stackops/settings/shells/zsh/__init__.py |  |
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
| `stackops.settings.yazi.scripts.fullscreen_preview` | `script-asset` | `script-asset` | `medium` | main, __main__, funcs:25 | src/stackops/settings/yazi/scripts/fullscreen_preview.py |  |
| `stackops.settings.yazi.scripts.interactive_view` | `script-asset` | `script-asset` | `medium` | main, __main__, funcs:9 | src/stackops/settings/yazi/scripts/interactive_view.py |  |
| `stackops.settings.yazi.scripts.open_db_readonly` | `script-asset` | `script-asset` | `medium` | main, __main__, funcs:7 | src/stackops/settings/yazi/scripts/open_db_readonly.py |  |
| `stackops.settings.yazi.scripts.open_default_app` | `script-asset` | `script-asset` | `medium` | main, __main__, classes:1, funcs:16 | src/stackops/settings/yazi/scripts/open_default_app.py |  |
| `stackops.settings.yazi.scripts.serve_browser_file` | `script-asset` | `script-asset` | `medium` | main, __main__, classes:1, funcs:12 | src/stackops/settings/yazi/scripts/serve_browser_file.py |  |
| `stackops.settings.yazi.shell` | `package` | `package-marker` | `high` | - | src/stackops/settings/yazi/shell/__init__.py |  |
| `stackops.settings.zed` | `package` | `package-marker` | `high` | - | src/stackops/settings/zed/__init__.py |  |
| `stackops.settings.zellij` | `package` | `package-marker` | `high` | - | src/stackops/settings/zellij/__init__.py |  |
| `stackops.settings.zellij.commands` | `package` | `package-marker` | `high` | - | src/stackops/settings/zellij/commands/__init__.py |  |
| `stackops.settings.zellij.layouts` | `package` | `package-marker` | `high` | - | src/stackops/settings/zellij/layouts/__init__.py |  |
| `stackops.utils` | `package` | `package-marker` | `high` | api-doc | src/stackops/utils/__init__.py |  |
| `stackops.utils.ai` | `package` | `package-marker` | `high` | - | src/stackops/utils/ai/__init__.py |  |
| `stackops.utils.cli_utils` | `package` | `package-marker` | `high` | - | src/stackops/utils/cli_utils/__init__.py |  |
| `stackops.utils.cloud.onedrive` | `package` | `package-marker` | `high` | - | src/stackops/utils/cloud/onedrive/__init__.py |  |
| `stackops.utils.files.art` | `package` | `package-marker` | `high` | - | src/stackops/utils/files/art/__init__.py |  |
| `stackops.utils.files.ouch` | `package` | `package-marker` | `high` | - | src/stackops/utils/files/ouch/__init__.py |  |
| `stackops.utils.installer_utils` | `package` | `package-marker` | `high` | api-doc | src/stackops/utils/installer_utils/__init__.py |  |
| `stackops.utils.options_utils` | `package` | `package-marker` | `high` | - | src/stackops/utils/options_utils/__init__.py |  |
| `stackops.utils.schemas` | `package` | `package-marker` | `high` | - | src/stackops/utils/schemas/__init__.py |  |
| `stackops.utils.schemas.agents` | `package` | `package-marker` | `high` | - | src/stackops/utils/schemas/agents/__init__.py |  |
| `stackops.utils.schemas.config` | `package` | `package-marker` | `high` | __all__ | src/stackops/utils/schemas/config/__init__.py |  |
| `stackops.utils.schemas.installer` | `package` | `package-marker` | `high` | api-doc | src/stackops/utils/schemas/installer/__init__.py |  |
| `stackops.utils.schemas.layouts` | `package` | `package-marker` | `high` | - | src/stackops/utils/schemas/layouts/__init__.py |  |
| `stackops.utils.schemas.mapper` | `package` | `package-marker` | `high` | - | src/stackops/utils/schemas/mapper/__init__.py |  |
| `stackops.utils.schemas.repos` | `package` | `package-marker` | `high` | - | src/stackops/utils/schemas/repos/__init__.py |  |
| `stackops.utils.schemas.secrets` | `package` | `package-marker` | `high` | - | src/stackops/utils/schemas/secrets/__init__.py |  |

## Full Inventory

| Module | Marker | Label | Confidence | Imported by | LOC | Signals | Path | Notes |
| --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| `stackops` | `package` | `package-marker` | `high` | 1 | 0 | - | src/stackops/__init__.py |  |
| `stackops.cluster` | `package` | `package-marker` | `high` | 0 | 0 | api-doc | src/stackops/cluster/__init__.py |  |
| `stackops.cluster.remote` | `package` | `package-marker` | `high` | 0 | 44 | api-doc, __all__ | src/stackops/cluster/remote/__init__.py |  |
| `stackops.cluster.remote.cloud_manager` | `api` | `python-api` | `high` | 1 | 372 | api-doc, classes:2, funcs:9 | src/stackops/cluster/remote/cloud_manager.py |  |
| `stackops.cluster.remote.data_transfer` | `api` | `python-api` | `high` | 1 | 46 | api-doc, funcs:3 | src/stackops/cluster/remote/data_transfer.py |  |
| `stackops.cluster.remote.distribute` | `api` | `python-api` | `high` | 1 | 303 | api-doc, classes:5, funcs:6 | src/stackops/cluster/remote/distribute.py |  |
| `stackops.cluster.remote.execution_script` | `api` | `python-api` | `high` | 1 | 95 | api-doc, funcs:1 | src/stackops/cluster/remote/execution_script.py |  |
| `stackops.cluster.remote.file_manager` | `api` | `python-api` | `high` | 3 | 244 | api-doc, classes:1, funcs:6 | src/stackops/cluster/remote/file_manager.py |  |
| `stackops.cluster.remote.job_params` | `api` | `python-api` | `high` | 3 | 133 | api-doc, classes:1, funcs:2 | src/stackops/cluster/remote/job_params.py |  |
| `stackops.cluster.remote.models` | `api` | `python-api` | `high` | 8 | 244 | api-doc, classes:6, funcs:4 | src/stackops/cluster/remote/models.py |  |
| `stackops.cluster.remote.notification` | `api` | `python-api` | `high` | 1 | 33 | api-doc, funcs:1 | src/stackops/cluster/remote/notification.py |  |
| `stackops.cluster.remote.remote_machine` | `api` | `python-api` | `high` | 3 | 275 | api-doc, classes:1, funcs:1 | src/stackops/cluster/remote/remote_machine.py |  |
| `stackops.cluster.sessions_managers` | `package` | `package-marker` | `high` | 0 | 0 | api-doc | src/stackops/cluster/sessions_managers/__init__.py |  |
| `stackops.cluster.sessions_managers.helpers.enhanced_command_runner` | `api` | `api-cli-bridge` | `medium` | 2 | 137 | api-doc, __main__, funcs:2 | src/stackops/cluster/sessions_managers/helpers/enhanced_command_runner.py |  |
| `stackops.cluster.sessions_managers.helpers.load_balancer_helper` | `api` | `python-api` | `high` | 1 | 159 | api-doc, funcs:8 | src/stackops/cluster/sessions_managers/helpers/load_balancer_helper.py |  |
| `stackops.cluster.sessions_managers.session_conflict` | `api` | `python-api` | `high` | 13 | 375 | api-doc, classes:2, funcs:8 | src/stackops/cluster/sessions_managers/session_conflict.py |  |
| `stackops.cluster.sessions_managers.session_exit_mode` | `api` | `python-api` | `high` | 8 | 94 | api-doc, funcs:6 | src/stackops/cluster/sessions_managers/session_exit_mode.py |  |
| `stackops.cluster.sessions_managers.tmux` | `package` | `package-marker` | `high` | 0 | 0 | api-doc | src/stackops/cluster/sessions_managers/tmux/__init__.py |  |
| `stackops.cluster.sessions_managers.tmux.tmux_local` | `api` | `api-cli-bridge` | `medium` | 2 | 248 | api-doc, __main__, classes:3, funcs:1 | src/stackops/cluster/sessions_managers/tmux/tmux_local.py |  |
| `stackops.cluster.sessions_managers.tmux.tmux_local_manager` | `api` | `python-api` | `high` | 1 | 184 | api-doc, classes:2 | src/stackops/cluster/sessions_managers/tmux/tmux_local_manager.py |  |
| `stackops.cluster.sessions_managers.tmux.tmux_utils.tmux_common` | `api` | `python-api` | `high` | 2 | 18 | api-doc, funcs:3 | src/stackops/cluster/sessions_managers/tmux/tmux_utils/tmux_common.py |  |
| `stackops.cluster.sessions_managers.tmux.tmux_utils.tmux_execution` | `api` | `python-api` | `high` | 5 | 260 | api-doc, funcs:16 | src/stackops/cluster/sessions_managers/tmux/tmux_utils/tmux_execution.py |  |
| `stackops.cluster.sessions_managers.tmux.tmux_utils.tmux_layout` | `api` | `python-api` | `high` | 1 | 295 | api-doc, funcs:11 | src/stackops/cluster/sessions_managers/tmux/tmux_utils/tmux_layout.py |  |
| `stackops.cluster.sessions_managers.tmux.tmux_utils.tmux_status` | `api` | `python-api` | `high` | 3 | 76 | api-doc, classes:1, funcs:2 | src/stackops/cluster/sessions_managers/tmux/tmux_utils/tmux_status.py |  |
| `stackops.cluster.sessions_managers.utils` | `package` | `package-marker` | `high` | 0 | 2 | api-doc | src/stackops/cluster/sessions_managers/utils/__init__.py |  |
| `stackops.cluster.sessions_managers.utils.load_balancer` | `api` | `python-api` | `high` | 1 | 57 | api-doc, classes:1, funcs:3 | src/stackops/cluster/sessions_managers/utils/load_balancer.py |  |
| `stackops.cluster.sessions_managers.utils.maker` | `api` | `python-api` | `high` | 0 | 105 | api-doc, funcs:4 | src/stackops/cluster/sessions_managers/utils/maker.py |  |
| `stackops.cluster.sessions_managers.windows_terminal` | `package` | `package-marker` | `high` | 0 | 0 | api-doc | src/stackops/cluster/sessions_managers/windows_terminal/__init__.py |  |
| `stackops.cluster.sessions_managers.windows_terminal.wt_local` | `api` | `api-cli-bridge` | `medium` | 2 | 254 | api-doc, __main__, classes:1, funcs:3 | src/stackops/cluster/sessions_managers/windows_terminal/wt_local.py |  |
| `stackops.cluster.sessions_managers.windows_terminal.wt_local_manager` | `api` | `api-cli-bridge` | `medium` | 2 | 372 | api-doc, __main__, classes:2, funcs:1 | src/stackops/cluster/sessions_managers/windows_terminal/wt_local_manager.py |  |
| `stackops.cluster.sessions_managers.windows_terminal.wt_remote` | `api` | `api-cli-bridge` | `medium` | 1 | 212 | api-doc, __main__, classes:1 | src/stackops/cluster/sessions_managers/windows_terminal/wt_remote.py |  |
| `stackops.cluster.sessions_managers.windows_terminal.wt_remote_manager` | `api` | `api-cli-bridge` | `medium` | 0 | 315 | api-doc, __main__, classes:1 | src/stackops/cluster/sessions_managers/windows_terminal/wt_remote_manager.py |  |
| `stackops.cluster.sessions_managers.windows_terminal.wt_utils.examples` | `package` | `package-marker` | `high` | 0 | 0 | api-doc | src/stackops/cluster/sessions_managers/windows_terminal/wt_utils/examples/__init__.py |  |
| `stackops.cluster.sessions_managers.windows_terminal.wt_utils.examples.wt_local_manager_demo` | `api` | `api-cli-bridge` | `medium` | 1 | 79 | api-doc, __main__, funcs:1 | src/stackops/cluster/sessions_managers/windows_terminal/wt_utils/examples/wt_local_manager_demo.py |  |
| `stackops.cluster.sessions_managers.windows_terminal.wt_utils.layout_generator` | `api` | `python-api` | `high` | 1 | 176 | api-doc, classes:1 | src/stackops/cluster/sessions_managers/windows_terminal/wt_utils/layout_generator.py |  |
| `stackops.cluster.sessions_managers.windows_terminal.wt_utils.local_monitoring` | `api` | `python-api` | `high` | 1 | 84 | api-doc, classes:1, funcs:5 | src/stackops/cluster/sessions_managers/windows_terminal/wt_utils/local_monitoring.py |  |
| `stackops.cluster.sessions_managers.windows_terminal.wt_utils.manager_persistence` | `api` | `python-api` | `high` | 2 | 53 | api-doc, funcs:6 | src/stackops/cluster/sessions_managers/windows_terminal/wt_utils/manager_persistence.py |  |
| `stackops.cluster.sessions_managers.windows_terminal.wt_utils.monitoring_helpers` | `api` | `python-api` | `high` | 1 | 51 | api-doc, funcs:6 | src/stackops/cluster/sessions_managers/windows_terminal/wt_utils/monitoring_helpers.py |  |
| `stackops.cluster.sessions_managers.windows_terminal.wt_utils.process_monitor` | `api` | `python-api` | `high` | 2 | 324 | api-doc, classes:1 | src/stackops/cluster/sessions_managers/windows_terminal/wt_utils/process_monitor.py |  |
| `stackops.cluster.sessions_managers.windows_terminal.wt_utils.remote_executor` | `api` | `python-api` | `high` | 3 | 143 | api-doc, classes:1 | src/stackops/cluster/sessions_managers/windows_terminal/wt_utils/remote_executor.py |  |
| `stackops.cluster.sessions_managers.windows_terminal.wt_utils.session_manager` | `api` | `python-api` | `high` | 2 | 271 | api-doc, classes:7 | src/stackops/cluster/sessions_managers/windows_terminal/wt_utils/session_manager.py |  |
| `stackops.cluster.sessions_managers.windows_terminal.wt_utils.status_reporter` | `api` | `python-api` | `high` | 1 | 205 | api-doc, classes:1 | src/stackops/cluster/sessions_managers/windows_terminal/wt_utils/status_reporter.py |  |
| `stackops.cluster.sessions_managers.windows_terminal.wt_utils.status_reporting` | `api` | `python-api` | `high` | 3 | 77 | api-doc, funcs:5 | src/stackops/cluster/sessions_managers/windows_terminal/wt_utils/status_reporting.py |  |
| `stackops.cluster.sessions_managers.windows_terminal.wt_utils.wt_helpers` | `api` | `python-api` | `high` | 4 | 211 | api-doc, funcs:7 | src/stackops/cluster/sessions_managers/windows_terminal/wt_utils/wt_helpers.py |  |
| `stackops.cluster.sessions_managers.zellij` | `package` | `package-marker` | `high` | 0 | 0 | api-doc | src/stackops/cluster/sessions_managers/zellij/__init__.py |  |
| `stackops.cluster.sessions_managers.zellij.zellij_local` | `api` | `api-cli-bridge` | `medium` | 4 | 239 | api-doc, __main__, classes:1, funcs:3 | src/stackops/cluster/sessions_managers/zellij/zellij_local.py |  |
| `stackops.cluster.sessions_managers.zellij.zellij_local_manager` | `api` | `api-cli-bridge` | `medium` | 3 | 448 | api-doc, __main__, classes:2, funcs:3 | src/stackops/cluster/sessions_managers/zellij/zellij_local_manager.py |  |
| `stackops.cluster.sessions_managers.zellij.zellij_remote` | `api` | `api-cli-bridge` | `medium` | 2 | 195 | api-doc, __main__, classes:1 | src/stackops/cluster/sessions_managers/zellij/zellij_remote.py |  |
| `stackops.cluster.sessions_managers.zellij.zellij_remote_manager` | `api` | `python-api` | `high` | 0 | 197 | api-doc, classes:2 | src/stackops/cluster/sessions_managers/zellij/zellij_remote_manager.py |  |
| `stackops.cluster.sessions_managers.zellij.zellij_utils.example_usage` | `api` | `api-cli-bridge` | `medium` | 1 | 73 | api-doc, __main__, funcs:1 | src/stackops/cluster/sessions_managers/zellij/zellij_utils/example_usage.py |  |
| `stackops.cluster.sessions_managers.zellij.zellij_utils.layout_generator` | `api` | `python-api` | `high` | 2 | 127 | api-doc, classes:1 | src/stackops/cluster/sessions_managers/zellij/zellij_utils/layout_generator.py |  |
| `stackops.cluster.sessions_managers.zellij.zellij_utils.monitoring_types` | `api` | `python-api` | `high` | 11 | 105 | api-doc, classes:12 | src/stackops/cluster/sessions_managers/zellij/zellij_utils/monitoring_types.py |  |
| `stackops.cluster.sessions_managers.zellij.zellij_utils.process_monitor` | `api` | `python-api` | `high` | 3 | 287 | api-doc, classes:1 | src/stackops/cluster/sessions_managers/zellij/zellij_utils/process_monitor.py |  |
| `stackops.cluster.sessions_managers.zellij.zellij_utils.remote_executor` | `api` | `python-api` | `high` | 4 | 65 | api-doc, classes:1 | src/stackops/cluster/sessions_managers/zellij/zellij_utils/remote_executor.py |  |
| `stackops.cluster.sessions_managers.zellij.zellij_utils.session_manager` | `api` | `python-api` | `high` | 2 | 92 | api-doc, classes:1 | src/stackops/cluster/sessions_managers/zellij/zellij_utils/session_manager.py |  |
| `stackops.cluster.sessions_managers.zellij.zellij_utils.status_reporter` | `api` | `python-api` | `high` | 1 | 90 | api-doc, classes:1 | src/stackops/cluster/sessions_managers/zellij/zellij_utils/status_reporter.py |  |
| `stackops.cluster.sessions_managers.zellij.zellij_utils.zellij_local_helper` | `api` | `python-api` | `high` | 3 | 345 | api-doc, funcs:10 | src/stackops/cluster/sessions_managers/zellij/zellij_utils/zellij_local_helper.py |  |
| `stackops.cluster.sessions_managers.zellij.zellij_utils.zellij_local_helper_restart` | `api` | `python-api` | `high` | 1 | 78 | api-doc, funcs:1 | src/stackops/cluster/sessions_managers/zellij/zellij_utils/zellij_local_helper_restart.py |  |
| `stackops.cluster.sessions_managers.zellij.zellij_utils.zellij_local_helper_with_panes` | `api` | `api-cli-bridge` | `medium` | 0 | 229 | api-doc, __main__, funcs:8 | src/stackops/cluster/sessions_managers/zellij/zellij_utils/zellij_local_helper_with_panes.py |  |
| `stackops.cluster.sessions_managers.zellij.zellij_utils.zellij_local_manager_helper` | `api` | `python-api` | `high` | 1 | 166 | api-doc, funcs:8 | src/stackops/cluster/sessions_managers/zellij/zellij_utils/zellij_local_manager_helper.py |  |
| `stackops.jobs` | `package` | `package-marker` | `high` | 2 | 0 | api-doc | src/stackops/jobs/__init__.py |  |
| `stackops.jobs.agents.mcps` | `package` | `package-marker` | `high` | 1 | 3 | - | src/stackops/jobs/agents/mcps/__init__.py |  |
| `stackops.jobs.installer` | `package` | `package-marker` | `high` | 1 | 2 | api-doc | src/stackops/jobs/installer/__init__.py |  |
| `stackops.jobs.installer.checks` | `package` | `package-marker` | `high` | 0 | 0 | api-doc | src/stackops/jobs/installer/checks/__init__.py |  |
| `stackops.jobs.installer.checks.check_installations` | `api` | `api-cli-bridge` | `medium` | 2 | 243 | api-doc, main, __main__, funcs:12 | src/stackops/jobs/installer/checks/check_installations.py |  |
| `stackops.jobs.installer.checks.install_utils` | `api` | `python-api` | `high` | 3 | 159 | api-doc, funcs:7 | src/stackops/jobs/installer/checks/install_utils.py |  |
| `stackops.jobs.installer.checks.report_utils` | `api` | `python-api` | `high` | 3 | 390 | api-doc, classes:6, funcs:19 | src/stackops/jobs/installer/checks/report_utils.py |  |
| `stackops.jobs.installer.checks.security_cli` | `api` | `api-cli-bridge` | `medium` | 1 | 213 | api-doc, typer, typer-app, cli-registration, get_app, funcs:12 | src/stackops/jobs/installer/checks/security_cli.py |  |
| `stackops.jobs.installer.checks.security_helper` | `api` | `api-cli-bridge` | `medium` | 1 | 327 | api-doc, typer, funcs:18 | src/stackops/jobs/installer/checks/security_helper.py |  |
| `stackops.jobs.installer.checks.vt_utils` | `api` | `python-api` | `high` | 3 | 180 | api-doc, classes:2, funcs:7 | src/stackops/jobs/installer/checks/vt_utils.py |  |
| `stackops.jobs.installer.linux_scripts` | `package` | `package-marker` | `high` | 6 | 12 | api-doc | src/stackops/jobs/installer/linux_scripts/__init__.py |  |
| `stackops.jobs.installer.macos_scripts` | `package` | `package-marker` | `high` | 0 | 0 | api-doc | src/stackops/jobs/installer/macos_scripts/__init__.py |  |
| `stackops.jobs.installer.package_groups` | `api` | `python-api` | `high` | 5 | 311 | api-doc | src/stackops/jobs/installer/package_groups.py |  |
| `stackops.jobs.installer.powershell_scripts` | `package` | `package-marker` | `high` | 2 | 4 | api-doc | src/stackops/jobs/installer/powershell_scripts/__init__.py |  |
| `stackops.jobs.installer.python_scripts` | `package` | `package-marker` | `high` | 0 | 0 | api-doc | src/stackops/jobs/installer/python_scripts/__init__.py |  |
| `stackops.jobs.installer.python_scripts.alacritty` | `script-asset` | `installer-script-asset` | `high` | 0 | 93 | api-doc, main, __main__, funcs:1 | src/stackops/jobs/installer/python_scripts/alacritty.py |  |
| `stackops.jobs.installer.python_scripts.boxes` | `script-asset` | `installer-script-asset` | `high` | 0 | 69 | api-doc, main, __main__, funcs:1 | src/stackops/jobs/installer/python_scripts/boxes.py |  |
| `stackops.jobs.installer.python_scripts.brave` | `script-asset` | `installer-script-asset` | `high` | 0 | 94 | api-doc, main, __main__, funcs:1 | src/stackops/jobs/installer/python_scripts/brave.py |  |
| `stackops.jobs.installer.python_scripts.bypass_paywall` | `script-asset` | `installer-script-asset` | `high` | 0 | 85 | api-doc, main, __main__, funcs:1 | src/stackops/jobs/installer/python_scripts/bypass_paywall.py |  |
| `stackops.jobs.installer.python_scripts.cloudflare_warp_cli` | `script-asset` | `installer-script-asset` | `high` | 0 | 35 | api-doc, main, __main__, funcs:1 | src/stackops/jobs/installer/python_scripts/cloudflare_warp_cli.py |  |
| `stackops.jobs.installer.python_scripts.code` | `script-asset` | `installer-script-asset` | `high` | 0 | 77 | api-doc, main, __main__, funcs:1 | src/stackops/jobs/installer/python_scripts/code.py |  |
| `stackops.jobs.installer.python_scripts.cursor` | `script-asset` | `installer-script-asset` | `high` | 0 | 125 | api-doc, main, __main__, funcs:3 | src/stackops/jobs/installer/python_scripts/cursor.py |  |
| `stackops.jobs.installer.python_scripts.docker` | `script-asset` | `installer-script-asset` | `high` | 0 | 190 | api-doc, main, __main__, funcs:3 | src/stackops/jobs/installer/python_scripts/docker.py |  |
| `stackops.jobs.installer.python_scripts.dubdb_adbc` | `script-asset` | `installer-script-asset` | `high` | 0 | 40 | api-doc, main, __main__, funcs:1 | src/stackops/jobs/installer/python_scripts/dubdb_adbc.py |  |
| `stackops.jobs.installer.python_scripts.espanso` | `script-asset` | `installer-script-asset` | `high` | 0 | 175 | api-doc, main, __main__, funcs:4 | src/stackops/jobs/installer/python_scripts/espanso.py |  |
| `stackops.jobs.installer.python_scripts.goes` | `script-asset` | `installer-script-asset` | `high` | 0 | 69 | api-doc, main, funcs:1 | src/stackops/jobs/installer/python_scripts/goes.py |  |
| `stackops.jobs.installer.python_scripts.hx` | `script-asset` | `installer-script-asset` | `high` | 0 | 235 | api-doc, main, __main__, funcs:1 | src/stackops/jobs/installer/python_scripts/hx.py |  |
| `stackops.jobs.installer.python_scripts.lvim` | `script-asset` | `installer-script-asset` | `high` | 0 | 96 | api-doc, main, __main__, funcs:1 | src/stackops/jobs/installer/python_scripts/lvim.py |  |
| `stackops.jobs.installer.python_scripts.main_protocol` | `script-asset` | `installer-script-asset` | `high` | 25 | 68 | api-doc, classes:1, funcs:2 | src/stackops/jobs/installer/python_scripts/main_protocol.py |  |
| `stackops.jobs.installer.python_scripts.nerdfont` | `script-asset` | `installer-script-asset` | `high` | 0 | 365 | api-doc, main, __main__, funcs:17 | src/stackops/jobs/installer/python_scripts/nerdfont.py |  |
| `stackops.jobs.installer.python_scripts.orca` | `script-asset` | `installer-script-asset` | `high` | 0 | 149 | api-doc, main, __main__, funcs:10 | src/stackops/jobs/installer/python_scripts/orca.py |  |
| `stackops.jobs.installer.python_scripts.poppler` | `script-asset` | `installer-script-asset` | `high` | 0 | 69 | api-doc, main, __main__, funcs:2 | src/stackops/jobs/installer/python_scripts/poppler.py |  |
| `stackops.jobs.installer.python_scripts.redis` | `script-asset` | `installer-script-asset` | `high` | 0 | 84 | api-doc, main, __main__, funcs:1 | src/stackops/jobs/installer/python_scripts/redis.py |  |
| `stackops.jobs.installer.python_scripts.rmpc` | `script-asset` | `installer-script-asset` | `high` | 0 | 475 | api-doc, main, __main__, funcs:25 | src/stackops/jobs/installer/python_scripts/rmpc.py |  |
| `stackops.jobs.installer.python_scripts.sysabc` | `script-asset` | `installer-script-asset` | `high` | 0 | 51 | api-doc, main, __main__, funcs:1 | src/stackops/jobs/installer/python_scripts/sysabc.py |  |
| `stackops.jobs.installer.python_scripts.termusic` | `script-asset` | `installer-script-asset` | `high` | 0 | 352 | api-doc, main, __main__, funcs:20 | src/stackops/jobs/installer/python_scripts/termusic.py |  |
| `stackops.jobs.installer.python_scripts.wezterm` | `script-asset` | `installer-script-asset` | `high` | 0 | 84 | api-doc, main, __main__, funcs:1 | src/stackops/jobs/installer/python_scripts/wezterm.py |  |
| `stackops.jobs.installer.python_scripts.winget` | `script-asset` | `installer-script-asset` | `high` | 0 | 183 | api-doc, main, __main__, funcs:5 | src/stackops/jobs/installer/python_scripts/winget.py |  |
| `stackops.jobs.installer.python_scripts.yazi` | `script-asset` | `installer-script-asset` | `high` | 0 | 115 | api-doc, main, __main__, funcs:1 | src/stackops/jobs/installer/python_scripts/yazi.py |  |
| `stackops.jobs.installer.python_scripts.youtube_tui` | `script-asset` | `installer-script-asset` | `high` | 0 | 357 | api-doc, main, __main__, funcs:15 | src/stackops/jobs/installer/python_scripts/youtube_tui.py |  |
| `stackops.jobs.installer.python_scripts.ytui_music` | `script-asset` | `installer-script-asset` | `high` | 0 | 413 | api-doc, main, __main__, funcs:25 | src/stackops/jobs/installer/python_scripts/ytui_music.py |  |
| `stackops.jobs.scripts.bash_scripts` | `package` | `package-marker` | `high` | 0 | 3 | - | src/stackops/jobs/scripts/bash_scripts/__init__.py |  |
| `stackops.jobs.scripts.powershell_scripts` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/jobs/scripts/powershell_scripts/__init__.py |  |
| `stackops.jobs.scripts_dynamic` | `package` | `package-marker` | `high` | 1 | 4 | - | src/stackops/jobs/scripts_dynamic/__init__.py |  |
| `stackops.jobs.scripts_dynamic.download_stackops_offline_installer` | `script-asset` | `script-asset` | `medium` | 0 | 114 | main, __main__, classes:1, funcs:7 | src/stackops/jobs/scripts_dynamic/download_stackops_offline_installer.py |  |
| `stackops.jobs.scripts_dynamic.system_compute_analyzer` | `script-asset` | `script-asset` | `medium` | 0 | 438 | main, __main__, classes:4, funcs:2 | src/stackops/jobs/scripts_dynamic/system_compute_analyzer.py |  |
| `stackops.logger` | `api` | `python-api` | `high` | 2 | 49 | api-doc, funcs:2 | src/stackops/logger.py |  |
| `stackops.profile` | `package` | `package-marker` | `high` | 2 | 7 | - | src/stackops/profile/__init__.py |  |
| `stackops.profile.create_helper` | `api` | `python-api-candidate` | `medium` | 2 | 76 | funcs:2 | src/stackops/profile/create_helper.py |  |
| `stackops.profile.create_links` | `api-or-script` | `manual-review` | `medium` | 2 | 480 | __main__, classes:2, funcs:16 | src/stackops/profile/create_links.py |  |
| `stackops.profile.create_links_export` | `api-or-script` | `manual-review` | `medium` | 7 | 148 | typer, funcs:2 | src/stackops/profile/create_links_export.py |  |
| `stackops.profile.create_shell_profile` | `api-or-script` | `manual-review` | `medium` | 4 | 195 | __main__, funcs:6 | src/stackops/profile/create_shell_profile.py |  |
| `stackops.profile.dotfiles_mapper` | `api` | `python-api-candidate` | `medium` | 6 | 147 | classes:1, funcs:11 | src/stackops/profile/dotfiles_mapper.py |  |
| `stackops.scripts` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/scripts/__init__.py |  |
| `stackops.scripts.linux` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/scripts/linux/__init__.py |  |
| `stackops.scripts.nu` | `package` | `package-marker` | `high` | 1 | 2 | - | src/stackops/scripts/nu/__init__.py |  |
| `stackops.scripts.python` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/scripts/python/__init__.py |  |
| `stackops.scripts.python.agents` | `cli` | `cli-entrypoint` | `high` | 1 | 326 | entry:agents, typer, typer-app, cli-registration, get_app, main, __main__, funcs:10 | src/stackops/scripts/python/agents.py |  |
| `stackops.scripts.python.agents_browser` | `cli` | `cli-module` | `high` | 1 | 84 | typer, typer-app, cli-registration, get_app, funcs:3 | src/stackops/scripts/python/agents_browser.py |  |
| `stackops.scripts.python.agents_parallel` | `cli` | `cli-module` | `high` | 1 | 62 | typer, typer-app, cli-registration, get_app, funcs:1 | src/stackops/scripts/python/agents_parallel.py |  |
| `stackops.scripts.python.agents_parallel_commands` | `cli` | `cli-module` | `high` | 3 | 195 | typer, funcs:5 | src/stackops/scripts/python/agents_parallel_commands.py |  |
| `stackops.scripts.python.agents_parallel_run_command` | `cli` | `cli-module` | `high` | 1 | 111 | typer, funcs:1 | src/stackops/scripts/python/agents_parallel_run_command.py |  |
| `stackops.scripts.python.ai` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/scripts/python/ai/__init__.py |  |
| `stackops.scripts.python.ai.initai` | `cli-helper` | `cli-helper` | `medium` | 1 | 189 | funcs:4 | src/stackops/scripts/python/ai/initai.py |  |
| `stackops.scripts.python.ai.scripts` | `package` | `package-marker` | `high` | 5 | 6 | - | src/stackops/scripts/python/ai/scripts/__init__.py |  |
| `stackops.scripts.python.ai.scripts.dashboard` | `cli-helper` | `cli-helper` | `medium` | 0 | 262 | funcs:6 | src/stackops/scripts/python/ai/scripts/dashboard.py |  |
| `stackops.scripts.python.ai.scripts.lint_and_type_check` | `cli-helper` | `cli-helper` | `medium` | 0 | 381 | main, __main__, funcs:9 | src/stackops/scripts/python/ai/scripts/lint_and_type_check.py |  |
| `stackops.scripts.python.ai.scripts.models` | `cli-helper` | `cli-helper` | `medium` | 2 | 187 | __all__, classes:5 | src/stackops/scripts/python/ai/scripts/models.py |  |
| `stackops.scripts.python.ai.scripts.models_config` | `cli-helper` | `cli-helper` | `medium` | 0 | 330 | funcs:13 | src/stackops/scripts/python/ai/scripts/models_config.py |  |
| `stackops.scripts.python.ai.scripts.models_diagnostics` | `cli-helper` | `cli-helper` | `medium` | 0 | 220 | classes:2, funcs:8 | src/stackops/scripts/python/ai/scripts/models_diagnostics.py |  |
| `stackops.scripts.python.ai.scripts.models_json` | `cli-helper` | `cli-helper` | `medium` | 2 | 92 | classes:1, funcs:5 | src/stackops/scripts/python/ai/scripts/models_json.py |  |
| `stackops.scripts.python.ai.scripts.models_reports` | `cli-helper` | `cli-helper` | `medium` | 0 | 187 | funcs:12 | src/stackops/scripts/python/ai/scripts/models_reports.py |  |
| `stackops.scripts.python.ai.scripts.paths` | `cli-helper` | `cli-helper` | `medium` | 3 | 17 | - | src/stackops/scripts/python/ai/scripts/paths.py |  |
| `stackops.scripts.python.ai.solutions` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/scripts/python/ai/solutions/__init__.py |  |
| `stackops.scripts.python.ai.solutions.antigravity` | `package` | `package-marker` | `high` | 1 | 2 | - | src/stackops/scripts/python/ai/solutions/antigravity/__init__.py |  |
| `stackops.scripts.python.ai.solutions.antigravity.antigravity` | `cli-helper` | `cli-helper` | `medium` | 0 | 21 | funcs:2 | src/stackops/scripts/python/ai/solutions/antigravity/antigravity.py |  |
| `stackops.scripts.python.ai.solutions.auggie` | `package` | `package-marker` | `high` | 1 | 0 | - | src/stackops/scripts/python/ai/solutions/auggie/__init__.py |  |
| `stackops.scripts.python.ai.solutions.auggie.auggie` | `cli-helper` | `cli-helper` | `medium` | 0 | 16 | funcs:1 | src/stackops/scripts/python/ai/solutions/auggie/auggie.py |  |
| `stackops.scripts.python.ai.solutions.claude.claude` | `cli-helper` | `cli-helper` | `medium` | 1 | 78 | funcs:4 | src/stackops/scripts/python/ai/solutions/claude/claude.py |  |
| `stackops.scripts.python.ai.solutions.cline.cline` | `cli-helper` | `cli-helper` | `medium` | 1 | 14 | funcs:1 | src/stackops/scripts/python/ai/solutions/cline/cline.py |  |
| `stackops.scripts.python.ai.solutions.codex` | `package` | `package-marker` | `high` | 1 | 2 | - | src/stackops/scripts/python/ai/solutions/codex/__init__.py |  |
| `stackops.scripts.python.ai.solutions.codex.codex` | `cli-helper` | `cli-helper` | `medium` | 0 | 29 | funcs:3 | src/stackops/scripts/python/ai/solutions/codex/codex.py |  |
| `stackops.scripts.python.ai.solutions.copilot` | `package` | `package-marker` | `high` | 2 | 0 | - | src/stackops/scripts/python/ai/solutions/copilot/__init__.py |  |
| `stackops.scripts.python.ai.solutions.copilot.agents` | `package` | `package-marker` | `high` | 0 | 4 | - | src/stackops/scripts/python/ai/solutions/copilot/agents/__init__.py |  |
| `stackops.scripts.python.ai.solutions.copilot.github_copilot` | `cli-helper` | `cli-helper` | `medium` | 0 | 54 | funcs:1 | src/stackops/scripts/python/ai/solutions/copilot/github_copilot.py |  |
| `stackops.scripts.python.ai.solutions.copilot.instructions.archive` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/scripts/python/ai/solutions/copilot/instructions/archive/__init__.py |  |
| `stackops.scripts.python.ai.solutions.copilot.instructions.python` | `package` | `package-marker` | `high` | 1 | 3 | - | src/stackops/scripts/python/ai/solutions/copilot/instructions/python/__init__.py |  |
| `stackops.scripts.python.ai.solutions.copilot.prompts` | `package` | `package-marker` | `high` | 0 | 3 | - | src/stackops/scripts/python/ai/solutions/copilot/prompts/__init__.py |  |
| `stackops.scripts.python.ai.solutions.crush` | `package` | `package-marker` | `high` | 1 | 3 | - | src/stackops/scripts/python/ai/solutions/crush/__init__.py |  |
| `stackops.scripts.python.ai.solutions.crush.crush` | `cli-helper` | `cli-helper` | `medium` | 0 | 28 | funcs:1 | src/stackops/scripts/python/ai/solutions/crush/crush.py |  |
| `stackops.scripts.python.ai.solutions.cursor.cursors` | `cli-helper` | `cli-helper` | `medium` | 1 | 14 | funcs:1 | src/stackops/scripts/python/ai/solutions/cursor/cursors.py |  |
| `stackops.scripts.python.ai.solutions.droid` | `package` | `package-marker` | `high` | 1 | 0 | - | src/stackops/scripts/python/ai/solutions/droid/__init__.py |  |
| `stackops.scripts.python.ai.solutions.droid.droid` | `cli-helper` | `cli-helper` | `medium` | 0 | 13 | funcs:1 | src/stackops/scripts/python/ai/solutions/droid/droid.py |  |
| `stackops.scripts.python.ai.solutions.forge` | `package` | `package-marker` | `high` | 1 | 2 | - | src/stackops/scripts/python/ai/solutions/forge/__init__.py |  |
| `stackops.scripts.python.ai.solutions.forge.forge` | `cli-helper` | `cli-helper` | `medium` | 0 | 37 | funcs:4 | src/stackops/scripts/python/ai/solutions/forge/forge.py |  |
| `stackops.scripts.python.ai.solutions.kilocode` | `package` | `package-marker` | `high` | 2 | 2 | - | src/stackops/scripts/python/ai/solutions/kilocode/__init__.py |  |
| `stackops.scripts.python.ai.solutions.kilocode.kilocode` | `cli-helper` | `cli-helper` | `medium` | 0 | 53 | funcs:4 | src/stackops/scripts/python/ai/solutions/kilocode/kilocode.py |  |
| `stackops.scripts.python.ai.solutions.opencode` | `package` | `package-marker` | `high` | 2 | 2 | - | src/stackops/scripts/python/ai/solutions/opencode/__init__.py |  |
| `stackops.scripts.python.ai.solutions.opencode.opencode` | `cli-helper` | `cli-helper` | `medium` | 0 | 32 | funcs:1 | src/stackops/scripts/python/ai/solutions/opencode/opencode.py |  |
| `stackops.scripts.python.ai.solutions.oz` | `package` | `package-marker` | `high` | 1 | 2 | - | src/stackops/scripts/python/ai/solutions/oz/__init__.py |  |
| `stackops.scripts.python.ai.solutions.oz.oz` | `cli-helper` | `cli-helper` | `medium` | 0 | 13 | funcs:1 | src/stackops/scripts/python/ai/solutions/oz/oz.py |  |
| `stackops.scripts.python.ai.solutions.pi` | `package` | `package-marker` | `high` | 1 | 2 | - | src/stackops/scripts/python/ai/solutions/pi/__init__.py |  |
| `stackops.scripts.python.ai.solutions.pi.pi` | `cli-helper` | `cli-helper` | `medium` | 0 | 29 | funcs:3 | src/stackops/scripts/python/ai/solutions/pi/pi.py |  |
| `stackops.scripts.python.ai.solutions.q` | `package` | `package-marker` | `high` | 1 | 0 | - | src/stackops/scripts/python/ai/solutions/q/__init__.py |  |
| `stackops.scripts.python.ai.solutions.q.amazon_q` | `cli-helper` | `cli-helper` | `medium` | 0 | 15 | funcs:1 | src/stackops/scripts/python/ai/solutions/q/amazon_q.py |  |
| `stackops.scripts.python.ai.solutions.qwen_code` | `package` | `package-marker` | `high` | 1 | 0 | - | src/stackops/scripts/python/ai/solutions/qwen_code/__init__.py |  |
| `stackops.scripts.python.ai.solutions.qwen_code.qwen_code` | `cli-helper` | `cli-helper` | `medium` | 0 | 13 | funcs:1 | src/stackops/scripts/python/ai/solutions/qwen_code/qwen_code.py |  |
| `stackops.scripts.python.ai.solutions.warp` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/scripts/python/ai/solutions/warp/__init__.py |  |
| `stackops.scripts.python.ai.solutions.warp.warp` | `cli-helper` | `cli-helper` | `medium` | 0 | 13 | funcs:1 | src/stackops/scripts/python/ai/solutions/warp/warp.py |  |
| `stackops.scripts.python.ai.utils` | `package` | `package-marker` | `high` | 2 | 0 | - | src/stackops/scripts/python/ai/utils/__init__.py |  |
| `stackops.scripts.python.ai.utils.generate_files` | `cli` | `cli-module` | `high` | 2 | 372 | typer, cli-registration, __main__, funcs:16 | src/stackops/scripts/python/ai/utils/generate_files.py |  |
| `stackops.scripts.python.ai.utils.generic` | `cli-helper` | `cli-helper` | `medium` | 0 | 83 | funcs:3 | src/stackops/scripts/python/ai/utils/generic.py |  |
| `stackops.scripts.python.ai.utils.shared` | `cli-helper` | `cli-helper` | `medium` | 17 | 19 | funcs:1 | src/stackops/scripts/python/ai/utils/shared.py |  |
| `stackops.scripts.python.ai.utils.vscode_tasks` | `cli-helper` | `cli-helper` | `medium` | 1 | 47 | funcs:1 | src/stackops/scripts/python/ai/utils/vscode_tasks.py |  |
| `stackops.scripts.python.cloud` | `cli` | `cli-entrypoint` | `high` | 1 | 118 | entry:cloud, typer, typer-app, cli-registration, get_app, main, __main__, funcs:6 | src/stackops/scripts/python/cloud.py |  |
| `stackops.scripts.python.devops` | `cli` | `cli-entrypoint` | `high` | 2 | 178 | entry:devops, typer, typer-app, cli-registration, get_app, main, classes:1, funcs:13 | src/stackops/scripts/python/devops.py |  |
| `stackops.scripts.python.enums` | `cli-helper` | `cli-helper` | `medium` | 3 | 86 | - | src/stackops/scripts/python/enums.py |  |
| `stackops.scripts.python.fire_jobs` | `cli` | `cli-entrypoint` | `high` | 1 | 81 | entry:fire, typer, typer-app, cli-registration, get_app, main, __main__, funcs:3 | src/stackops/scripts/python/fire_jobs.py |  |
| `stackops.scripts.python.ftpx` | `cli` | `cli-module` | `high` | 1 | 40 | typer, typer-app, cli-registration, main, __main__, funcs:2 | src/stackops/scripts/python/ftpx.py |  |
| `stackops.scripts.python.graph` | `package` | `package-marker` | `high` | 3 | 2 | - | src/stackops/scripts/python/graph/__init__.py |  |
| `stackops.scripts.python.graph.cli_graph_apps` | `cli-helper` | `cli-helper` | `medium` | 2 | 147 | funcs:2 | src/stackops/scripts/python/graph/cli_graph_apps.py |  |
| `stackops.scripts.python.graph.cli_graph_eval` | `cli-helper` | `cli-helper` | `medium` | 2 | 35 | funcs:2 | src/stackops/scripts/python/graph/cli_graph_eval.py |  |
| `stackops.scripts.python.graph.cli_graph_node_utils` | `cli-helper` | `cli-helper` | `medium` | 1 | 57 | funcs:6 | src/stackops/scripts/python/graph/cli_graph_node_utils.py |  |
| `stackops.scripts.python.graph.cli_graph_nodes` | `cli-helper` | `cli-helper` | `medium` | 1 | 204 | funcs:5 | src/stackops/scripts/python/graph/cli_graph_nodes.py |  |
| `stackops.scripts.python.graph.cli_graph_registration` | `cli-helper` | `cli-helper` | `medium` | 1 | 87 | funcs:3 | src/stackops/scripts/python/graph/cli_graph_registration.py |  |
| `stackops.scripts.python.graph.cli_graph_resolver` | `cli-helper` | `cli-helper` | `medium` | 5 | 218 | funcs:12 | src/stackops/scripts/python/graph/cli_graph_resolver.py |  |
| `stackops.scripts.python.graph.cli_graph_shared` | `cli-helper` | `cli-helper` | `medium` | 11 | 85 | classes:6 | src/stackops/scripts/python/graph/cli_graph_shared.py |  |
| `stackops.scripts.python.graph.cli_graph_signature` | `cli-helper` | `cli-helper` | `medium` | 1 | 207 | funcs:9 | src/stackops/scripts/python/graph/cli_graph_signature.py |  |
| `stackops.scripts.python.graph.cli_graph_targets` | `cli-helper` | `cli-helper` | `medium` | 1 | 151 | funcs:8 | src/stackops/scripts/python/graph/cli_graph_targets.py |  |
| `stackops.scripts.python.graph.cli_graph_tree` | `cli-helper` | `cli-helper` | `medium` | 1 | 75 | funcs:1 | src/stackops/scripts/python/graph/cli_graph_tree.py |  |
| `stackops.scripts.python.graph.cli_graph_values` | `cli-helper` | `cli-helper` | `medium` | 2 | 232 | funcs:5 | src/stackops/scripts/python/graph/cli_graph_values.py |  |
| `stackops.scripts.python.graph.generate_cli_graph` | `cli-helper` | `cli-helper` | `medium` | 2 | 35 | main, __main__, funcs:1 | src/stackops/scripts/python/graph/generate_cli_graph.py |  |
| `stackops.scripts.python.graph.visualize` | `package` | `package-marker` | `high` | 1 | 0 | - | src/stackops/scripts/python/graph/visualize/__init__.py |  |
| `stackops.scripts.python.graph.visualize.cli_graph_app` | `cli` | `cli-module` | `high` | 1 | 212 | typer, typer-app, cli-registration, get_app, main, __main__, funcs:7 | src/stackops/scripts/python/graph/visualize/cli_graph_app.py |  |
| `stackops.scripts.python.graph.visualize.cli_graph_search` | `cli-helper` | `cli-helper` | `medium` | 1 | 435 | classes:1, funcs:30 | src/stackops/scripts/python/graph/visualize/cli_graph_search.py |  |
| `stackops.scripts.python.graph.visualize.cli_graph_typer_app` | `cli` | `cli-module` | `high` | 0 | 74 | typer, typer-app, cli-registration, funcs:1 | src/stackops/scripts/python/graph/visualize/cli_graph_typer_app.py |  |
| `stackops.scripts.python.graph.visualize.dot_export` | `cli-helper` | `cli-helper` | `medium` | 1 | 81 | funcs:5 | src/stackops/scripts/python/graph/visualize/dot_export.py |  |
| `stackops.scripts.python.graph.visualize.graph_data` | `cli-helper` | `cli-helper` | `medium` | 3 | 142 | classes:1, funcs:8 | src/stackops/scripts/python/graph/visualize/graph_data.py |  |
| `stackops.scripts.python.graph.visualize.graph_paths` | `cli-helper` | `cli-helper` | `medium` | 3 | 9 | - | src/stackops/scripts/python/graph/visualize/graph_paths.py |  |
| `stackops.scripts.python.graph.visualize.helpers_navigator` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/scripts/python/graph/visualize/helpers_navigator/__init__.py |  |
| `stackops.scripts.python.graph.visualize.helpers_navigator.cli_graph_loader` | `cli-helper` | `cli-helper` | `medium` | 1 | 232 | classes:1, funcs:14 | src/stackops/scripts/python/graph/visualize/helpers_navigator/cli_graph_loader.py |  |
| `stackops.scripts.python.graph.visualize.helpers_navigator.command_builder` | `cli-helper` | `cli-helper` | `medium` | 1 | 180 | classes:1 | src/stackops/scripts/python/graph/visualize/helpers_navigator/command_builder.py |  |
| `stackops.scripts.python.graph.visualize.helpers_navigator.command_detail` | `cli-helper` | `cli-helper` | `medium` | 1 | 153 | classes:1 | src/stackops/scripts/python/graph/visualize/helpers_navigator/command_detail.py |  |
| `stackops.scripts.python.graph.visualize.helpers_navigator.command_tree` | `cli-helper` | `cli-helper` | `medium` | 1 | 50 | classes:1 | src/stackops/scripts/python/graph/visualize/helpers_navigator/command_tree.py |  |
| `stackops.scripts.python.graph.visualize.helpers_navigator.data_models` | `cli-helper` | `cli-helper` | `medium` | 5 | 35 | classes:2 | src/stackops/scripts/python/graph/visualize/helpers_navigator/data_models.py |  |
| `stackops.scripts.python.graph.visualize.helpers_navigator.devops_navigator` | `cli-helper` | `cli-helper` | `medium` | 1 | 21 | main, __main__, funcs:1 | src/stackops/scripts/python/graph/visualize/helpers_navigator/devops_navigator.py |  |
| `stackops.scripts.python.graph.visualize.helpers_navigator.main_app` | `cli-helper` | `cli-helper` | `medium` | 1 | 274 | classes:1 | src/stackops/scripts/python/graph/visualize/helpers_navigator/main_app.py |  |
| `stackops.scripts.python.graph.visualize.helpers_navigator.search_bar` | `cli-helper` | `cli-helper` | `medium` | 1 | 15 | classes:1 | src/stackops/scripts/python/graph/visualize/helpers_navigator/search_bar.py |  |
| `stackops.scripts.python.graph.visualize.plotly_browser` | `cli-helper` | `cli-helper` | `medium` | 1 | 186 | classes:1, funcs:11 | src/stackops/scripts/python/graph/visualize/plotly_browser.py |  |
| `stackops.scripts.python.graph.visualize.plotly_views` | `cli-helper` | `cli-helper` | `medium` | 2 | 183 | __main__, funcs:2 | src/stackops/scripts/python/graph/visualize/plotly_views.py |  |
| `stackops.scripts.python.graph.visualize.rich_tree` | `cli-helper` | `cli-helper` | `medium` | 1 | 73 | funcs:4 | src/stackops/scripts/python/graph/visualize/rich_tree.py |  |
| `stackops.scripts.python.helpers` | `package` | `package-marker` | `high` | 1 | 0 | - | src/stackops/scripts/python/helpers/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/scripts/python/helpers/helpers_agents/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agent_impl_interactive` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/scripts/python/helpers/helpers_agents/agent_impl_interactive/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agent_impl_interactive.common` | `cli-helper` | `cli-helper` | `medium` | 2 | 198 | funcs:16 | src/stackops/scripts/python/helpers/helpers_agents/agent_impl_interactive/common.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agent_impl_interactive.create_options` | `cli-helper` | `cli-helper` | `medium` | 1 | 414 | classes:2, funcs:25 | src/stackops/scripts/python/helpers/helpers_agents/agent_impl_interactive/create_options.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agent_impl_interactive.main` | `cli-helper` | `cli-helper` | `medium` | 1 | 227 | main, classes:1, funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agent_impl_interactive/main.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agentic_frameworks` | `package` | `package-marker` | `high` | 1 | 2 | - | src/stackops/scripts/python/helpers/helpers_agents/agentic_frameworks/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_codex` | `cli-helper` | `cli-helper` | `medium` | 1 | 41 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agentic_frameworks/fire_codex.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_copilot` | `cli-helper` | `cli-helper` | `medium` | 1 | 33 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agentic_frameworks/fire_copilot.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_crush` | `cli-helper` | `cli-helper` | `medium` | 1 | 42 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agentic_frameworks/fire_crush.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_cursor_agents` | `cli-helper` | `cli-helper` | `medium` | 0 | 19 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agentic_frameworks/fire_cursor_agents.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_pi` | `cli-helper` | `cli-helper` | `medium` | 1 | 45 | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agentic_frameworks/fire_pi.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_qwen` | `cli-helper` | `cli-helper` | `medium` | 0 | 28 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/agentic_frameworks/fire_qwen.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_ask_impl` | `cli-helper` | `cli-helper` | `medium` | 1 | 172 | funcs:13 | src/stackops/scripts/python/helpers/helpers_agents/agents_ask_impl.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_constants` | `cli-helper` | `cli-helper` | `medium` | 4 | 18 | - | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_constants.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_guides` | `cli-helper` | `cli-helper` | `medium` | 1 | 62 | classes:1, funcs:3 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_guides.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_impl` | `cli-helper` | `cli-helper` | `medium` | 1 | 159 | classes:3, funcs:6 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_impl.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_browser_resolution` | `cli-helper` | `cli-helper` | `medium` | 1 | 128 | funcs:11 | src/stackops/scripts/python/helpers/helpers_agents/agents_browser_resolution.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_create_artifacts` | `cli-helper` | `cli-helper` | `medium` | 2 | 328 | classes:4, funcs:10 | src/stackops/scripts/python/helpers/helpers_agents/agents_create_artifacts.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_create_inputs` | `cli-helper` | `cli-helper` | `medium` | 1 | 219 | classes:2, funcs:5 | src/stackops/scripts/python/helpers/helpers_agents/agents_create_inputs.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_impl` | `cli` | `cli-module` | `high` | 8 | 522 | typer, funcs:12 | src/stackops/scripts/python/helpers/helpers_agents/agents_impl.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_mcp_impl` | `cli-helper` | `cli-helper` | `medium` | 1 | 116 | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_mcp_impl.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_parallel_add_entry` | `cli-helper` | `cli-helper` | `medium` | 2 | 96 | funcs:9 | src/stackops/scripts/python/helpers/helpers_agents/agents_parallel_add_entry.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_parallel_run_config` | `cli-helper` | `cli-helper` | `medium` | 6 | 204 | classes:2, funcs:9 | src/stackops/scripts/python/helpers/helpers_agents/agents_parallel_run_config.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_parallel_run_impl` | `cli` | `cli-module` | `high` | 1 | 176 | typer, funcs:10 | src/stackops/scripts/python/helpers/helpers_agents/agents_parallel_run_impl.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_parallel_run_yaml` | `cli-helper` | `cli-helper` | `medium` | 2 | 264 | funcs:18 | src/stackops/scripts/python/helpers/helpers_agents/agents_parallel_run_yaml.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_parallel_yaml_defaults` | `cli-helper` | `cli-helper` | `medium` | 4 | 57 | classes:1 | src/stackops/scripts/python/helpers/helpers_agents/agents_parallel_yaml_defaults.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_rich_output` | `cli-helper` | `cli-helper` | `medium` | 3 | 181 | funcs:12 | src/stackops/scripts/python/helpers/helpers_agents/agents_rich_output.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_run_context` | `cli` | `cli-module` | `high` | 3 | 364 | typer, funcs:17 | src/stackops/scripts/python/helpers/helpers_agents/agents_run_context.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_run_impl` | `cli` | `cli-module` | `high` | 4 | 253 | typer, funcs:12 | src/stackops/scripts/python/helpers/helpers_agents/agents_run_impl.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_shell` | `cli-helper` | `cli-helper` | `medium` | 5 | 95 | funcs:13 | src/stackops/scripts/python/helpers/helpers_agents/agents_shell.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_skill_impl` | `cli-helper` | `cli-helper` | `medium` | 2 | 99 | funcs:9 | src/stackops/scripts/python/helpers/helpers_agents/agents_skill_impl.py |  |
| `stackops.scripts.python.helpers.helpers_agents.agents_yaml_schemas` | `cli-helper` | `cli-helper` | `medium` | 5 | 29 | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/agents_yaml_schemas.py |  |
| `stackops.scripts.python.helpers.helpers_agents.browser_guides` | `package` | `package-marker` | `high` | 1 | 13 | - | src/stackops/scripts/python/helpers/helpers_agents/browser_guides/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.fire_agents_help_launch` | `cli-helper` | `cli-helper` | `medium` | 2 | 282 | funcs:7 | src/stackops/scripts/python/helpers/helpers_agents/fire_agents_help_launch.py |  |
| `stackops.scripts.python.helpers.helpers_agents.fire_agents_help_search` | `cli-helper` | `cli-helper` | `medium` | 0 | 82 | funcs:2 | src/stackops/scripts/python/helpers/helpers_agents/fire_agents_help_search.py |  |
| `stackops.scripts.python.helpers.helpers_agents.fire_agents_helper_types` | `cli-helper` | `cli-helper` | `medium` | 31 | 84 | classes:2 | src/stackops/scripts/python/helpers/helpers_agents/fire_agents_helper_types.py |  |
| `stackops.scripts.python.helpers.helpers_agents.fire_agents_load_balancer` | `cli-helper` | `cli-helper` | `medium` | 0 | 37 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/fire_agents_load_balancer.py |  |
| `stackops.scripts.python.helpers.helpers_agents.mcp_catalog` | `cli-helper` | `cli-helper` | `medium` | 2 | 351 | funcs:17 | src/stackops/scripts/python/helpers/helpers_agents/mcp_catalog.py |  |
| `stackops.scripts.python.helpers.helpers_agents.mcp_install` | `cli-helper` | `cli-helper` | `medium` | 3 | 638 | funcs:33 | src/stackops/scripts/python/helpers/helpers_agents/mcp_install.py |  |
| `stackops.scripts.python.helpers.helpers_agents.mcp_types` | `cli-helper` | `cli-helper` | `medium` | 4 | 47 | classes:5 | src/stackops/scripts/python/helpers/helpers_agents/mcp_types.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.aichat` | `package` | `package-marker` | `high` | 1 | 2 | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/aichat/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.auggie` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/auggie/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.auggie.auggie_privacy` | `cli-helper` | `cli-helper` | `medium` | 2 | 39 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/auggie/auggie_privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.chatgpt` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/chatgpt/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.chatgpt.chatgpt_privacy` | `cli-helper` | `cli-helper` | `medium` | 2 | 45 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/chatgpt/chatgpt_privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.cline` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/cline/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.cline.cline_privacy` | `cli-helper` | `cli-helper` | `medium` | 2 | 45 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/cline/cline_privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.codex` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/codex/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.codex.codex_privacy` | `cli-helper` | `cli-helper` | `medium` | 2 | 34 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/codex/codex_privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.common` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/common/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.common.privacy_orchestrator` | `cli-helper` | `cli-helper` | `medium` | 1 | 122 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/common/privacy_orchestrator.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.copilot` | `package` | `package-marker` | `high` | 1 | 2 | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/copilot/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.crush` | `package` | `package-marker` | `high` | 1 | 2 | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/crush/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.cursor` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/cursor/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.cursor.cursor_privacy` | `cli-helper` | `cli-helper` | `medium` | 2 | 52 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/cursor/cursor_privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.droid` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/droid/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.droid.droid_privacy` | `cli-helper` | `cli-helper` | `medium` | 2 | 28 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/droid/droid_privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.kilocode` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/kilocode/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.kilocode.kilocode_privacy` | `cli-helper` | `cli-helper` | `medium` | 2 | 34 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/kilocode/kilocode_privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.mods` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/mods/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.mods.mods_privacy` | `cli-helper` | `cli-helper` | `medium` | 2 | 36 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/mods/mods_privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.opencode` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/opencode/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.q` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/q/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.q.q_privacy` | `cli-helper` | `cli-helper` | `medium` | 2 | 55 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/q/q_privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.qwen` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/qwen/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.configs.qwen.qwen_privacy` | `cli-helper` | `cli-helper` | `medium` | 2 | 24 | funcs:1 | src/stackops/scripts/python/helpers/helpers_agents/privacy/configs/qwen/qwen_privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.privacy.privacy` | `cli-helper` | `cli-helper` | `medium` | 0 | 29 | __main__, __all__ | src/stackops/scripts/python/helpers/helpers_agents/privacy/privacy.py |  |
| `stackops.scripts.python.helpers.helpers_agents.reasoning_capabilities` | `cli-helper` | `cli-helper` | `medium` | 19 | 92 | classes:1, funcs:6 | src/stackops/scripts/python/helpers/helpers_agents/reasoning_capabilities.py |  |
| `stackops.scripts.python.helpers.helpers_agents.templates` | `package` | `package-marker` | `high` | 1 | 4 | - | src/stackops/scripts/python/helpers/helpers_agents/templates/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_cloud` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/scripts/python/helpers/helpers_cloud/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.cloud_copy` | `cli-helper` | `cli-helper` | `medium` | 2 | 453 | main, classes:1, funcs:12 | src/stackops/scripts/python/helpers/helpers_cloud/cloud_copy.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.cloud_helpers` | `cli-helper` | `cli-helper` | `medium` | 1 | 46 | funcs:8 | src/stackops/scripts/python/helpers/helpers_cloud/cloud_helpers.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.cloud_mount` | `cli` | `cli-module` | `high` | 2 | 198 | typer, typer-app, cli-registration, get_app, __main__, funcs:4 | src/stackops/scripts/python/helpers/helpers_cloud/cloud_mount.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.cloud_mount_tmux` | `cli-helper` | `cli-helper` | `medium` | 1 | 42 | funcs:1 | src/stackops/scripts/python/helpers/helpers_cloud/cloud_mount_tmux.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.cloud_mount_zellij` | `cli-helper` | `cli-helper` | `medium` | 1 | 90 | funcs:5 | src/stackops/scripts/python/helpers/helpers_cloud/cloud_mount_zellij.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.cloud_path_resolver` | `cli-helper` | `cli-helper` | `medium` | 5 | 92 | funcs:1 | src/stackops/scripts/python/helpers/helpers_cloud/cloud_path_resolver.py |  |
| `stackops.scripts.python.helpers.helpers_cloud.cloud_sync` | `cli-helper` | `cli-helper` | `medium` | 1 | 79 | main, funcs:1 | src/stackops/scripts/python/helpers/helpers_cloud/cloud_sync.py |  |
| `stackops.scripts.python.helpers.helpers_devops` | `package` | `package-marker` | `high` | 11 | 0 | - | src/stackops/scripts/python/helpers/helpers_devops/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_devops.backup_config` | `cli-helper` | `cli-helper` | `medium` | 3 | 324 | classes:1, funcs:20 | src/stackops/scripts/python/helpers/helpers_devops/backup_config.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_backup_retrieve` | `cli-helper` | `cli-helper` | `medium` | 3 | 439 | __main__, funcs:12 | src/stackops/scripts/python/helpers/helpers_devops/cli_backup_retrieve.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config` | `cli` | `cli-module` | `high` | 0 | 419 | typer, typer-app, cli-registration, get_app, classes:1, funcs:22 | src/stackops/scripts/python/helpers/helpers_devops/cli_config.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_mapper` | `cli` | `cli-module` | `high` | 1 | 450 | typer, cli-registration, __main__, funcs:16 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_dotfile_mapper.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_transfer` | `cli` | `cli-module` | `high` | 2 | 218 | typer, funcs:5 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_dotfile_transfer.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_mount` | `cli` | `cli-module` | `high` | 0 | 124 | typer, funcs:5 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_mount.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets` | `cli` | `cli-module` | `high` | 1 | 309 | typer, typer-app, cli-registration, get_app, funcs:7 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_actions` | `cli` | `cli-module` | `high` | 0 | 507 | typer, funcs:33 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets_actions.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_candidates` | `cli` | `cli-module` | `high` | 2 | 310 | typer, __all__, classes:2, funcs:20 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets_candidates.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_interactive` | `cli` | `cli-module` | `high` | 2 | 116 | typer, classes:1, funcs:7 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets_interactive.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_support` | `cli` | `cli-module` | `high` | 1 | 485 | typer, classes:2, funcs:32 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_secrets_support.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_terminal` | `cli` | `cli-module` | `high` | 0 | 168 | typer, typer-app, cli-registration, get_app, funcs:8 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_terminal.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_config_tmux` | `cli` | `cli-module` | `high` | 1 | 335 | typer, typer-app, cli-registration, get_app, classes:1, funcs:20 | src/stackops/scripts/python/helpers/helpers_devops/cli_config_tmux.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_data` | `cli` | `cli-module` | `high` | 0 | 317 | typer, typer-app, cli-registration, get_app, funcs:8 | src/stackops/scripts/python/helpers/helpers_devops/cli_data.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_device` | `cli` | `cli-module` | `high` | 0 | 233 | typer, typer-app, cli-registration, get_app, funcs:8 | src/stackops/scripts/python/helpers/helpers_devops/cli_device.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_nw` | `cli` | `cli-module` | `high` | 1 | 159 | typer, typer-app, cli-registration, get_app, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/cli_nw.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_nw_vscode_share` | `cli-helper` | `cli-helper` | `medium` | 1 | 160 | funcs:7 | src/stackops/scripts/python/helpers/helpers_devops/cli_nw_vscode_share.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_repos` | `cli` | `cli-module` | `high` | 0 | 423 | typer, typer-app, cli-registration, get_app, funcs:15 | src/stackops/scripts/python/helpers/helpers_devops/cli_repos.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self` | `cli` | `cli-module` | `high` | 1 | 427 | typer, typer-app, cli-registration, get_app, funcs:14 | src/stackops/scripts/python/helpers/helpers_devops/cli_self.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self_ai` | `package` | `package-marker` | `high` | 3 | 2 | - | src/stackops/scripts/python/helpers/helpers_devops/cli_self_ai/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self_ai.app` | `cli` | `cli-module` | `high` | 0 | 36 | typer, typer-app, cli-registration, get_app, funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/cli_self_ai/app.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self_ai.update_docs` | `cli` | `cli-module` | `high` | 0 | 185 | typer, funcs:9 | src/stackops/scripts/python/helpers/helpers_devops/cli_self_ai/update_docs.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self_ai.update_installer` | `cli` | `cli-module` | `high` | 0 | 176 | typer, funcs:8 | src/stackops/scripts/python/helpers/helpers_devops/cli_self_ai/update_installer.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self_ai.update_logic` | `cli` | `cli-module` | `high` | 0 | 254 | typer, classes:1, funcs:11 | src/stackops/scripts/python/helpers/helpers_devops/cli_self_ai/update_logic.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self_ai.update_test` | `cli` | `cli-module` | `high` | 0 | 187 | typer, funcs:6 | src/stackops/scripts/python/helpers/helpers_devops/cli_self_ai/update_test.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self_ai.workflow_capture` | `cli-helper` | `cli-helper` | `medium` | 1 | 100 | classes:2, funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/cli_self_ai/workflow_capture.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self_ai.workflows_yaml` | `cli-helper` | `cli-helper` | `medium` | 0 | 166 | __main__, funcs:12 | src/stackops/scripts/python/helpers/helpers_devops/cli_self_ai/workflows_yaml.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self_assets` | `cli` | `cli-module` | `high` | 0 | 57 | typer, typer-app, cli-registration, get_app, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/cli_self_assets.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self_docker` | `cli-helper` | `cli-helper` | `medium` | 0 | 250 | classes:2, funcs:14 | src/stackops/scripts/python/helpers/helpers_devops/cli_self_docker.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_self_docs` | `cli` | `cli-module` | `high` | 0 | 168 | typer, classes:1, funcs:10 | src/stackops/scripts/python/helpers/helpers_devops/cli_self_docs.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_share_file` | `cli` | `cli-module` | `high` | 1 | 219 | typer, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/cli_share_file.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_share_server` | `cli` | `cli-module` | `high` | 0 | 168 | typer, typer-app, cli-registration, __main__, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/cli_share_server.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_share_temp` | `cli` | `cli-module` | `high` | 0 | 108 | typer, classes:1, funcs:5 | src/stackops/scripts/python/helpers/helpers_devops/cli_share_temp.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_share_terminal` | `cli` | `cli-module` | `high` | 0 | 217 | typer, cli-registration, __main__, funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/cli_share_terminal.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_ssh` | `cli` | `cli-module` | `high` | 0 | 191 | typer, typer-app, cli-registration, get_app, funcs:8 | src/stackops/scripts/python/helpers/helpers_devops/cli_ssh.py |  |
| `stackops.scripts.python.helpers.helpers_devops.cli_vault` | `cli` | `cli-module` | `high` | 0 | 111 | typer, typer-app, cli-registration, get_app, funcs:5 | src/stackops/scripts/python/helpers/helpers_devops/cli_vault.py |  |
| `stackops.scripts.python.helpers.helpers_devops.devops_status` | `cli-helper` | `cli-helper` | `medium` | 1 | 128 | main, __main__, funcs:10 | src/stackops/scripts/python/helpers/helpers_devops/devops_status.py |  |
| `stackops.scripts.python.helpers.helpers_devops.devops_status_checks` | `cli-helper` | `cli-helper` | `medium` | 1 | 224 | classes:1, funcs:9 | src/stackops/scripts/python/helpers/helpers_devops/devops_status_checks.py |  |
| `stackops.scripts.python.helpers.helpers_devops.devops_status_display` | `cli-helper` | `cli-helper` | `medium` | 1 | 266 | funcs:9 | src/stackops/scripts/python/helpers/helpers_devops/devops_status_display.py |  |
| `stackops.scripts.python.helpers.helpers_devops.devops_update_repos` | `cli-helper` | `cli-helper` | `medium` | 0 | 232 | main, __main__, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/devops_update_repos.py |  |
| `stackops.scripts.python.helpers.helpers_devops.interactive` | `cli-helper` | `cli-helper` | `medium` | 1 | 248 | main, __main__, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/interactive.py |  |
| `stackops.scripts.python.helpers.helpers_devops.mount_helpers` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/scripts/python/helpers/helpers_devops/mount_helpers/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_devops.mount_helpers.commands` | `cli-helper` | `cli-helper` | `medium` | 3 | 31 | funcs:5 | src/stackops/scripts/python/helpers/helpers_devops/mount_helpers/commands.py |  |
| `stackops.scripts.python.helpers.helpers_devops.mount_helpers.device_entry` | `cli-helper` | `cli-helper` | `medium` | 7 | 18 | classes:1 | src/stackops/scripts/python/helpers/helpers_devops/mount_helpers/device_entry.py |  |
| `stackops.scripts.python.helpers.helpers_devops.mount_helpers.devices` | `cli-helper` | `cli-helper` | `medium` | 1 | 18 | funcs:1 | src/stackops/scripts/python/helpers/helpers_devops/mount_helpers/devices.py |  |
| `stackops.scripts.python.helpers.helpers_devops.mount_helpers.linux` | `cli-helper` | `cli-helper` | `medium` | 2 | 205 | funcs:10 | src/stackops/scripts/python/helpers/helpers_devops/mount_helpers/linux.py |  |
| `stackops.scripts.python.helpers.helpers_devops.mount_helpers.macos` | `cli-helper` | `cli-helper` | `medium` | 2 | 101 | funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/mount_helpers/macos.py |  |
| `stackops.scripts.python.helpers.helpers_devops.mount_helpers.selection` | `cli-helper` | `cli-helper` | `medium` | 2 | 50 | funcs:2 | src/stackops/scripts/python/helpers/helpers_devops/mount_helpers/selection.py |  |
| `stackops.scripts.python.helpers.helpers_devops.mount_helpers.utils` | `cli-helper` | `cli-helper` | `medium` | 4 | 29 | funcs:3 | src/stackops/scripts/python/helpers/helpers_devops/mount_helpers/utils.py |  |
| `stackops.scripts.python.helpers.helpers_devops.mount_helpers.windows` | `cli-helper` | `cli-helper` | `medium` | 2 | 87 | funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/mount_helpers/windows.py |  |
| `stackops.scripts.python.helpers.helpers_devops.register_interactive` | `cli` | `cli-module` | `high` | 3 | 55 | typer, funcs:6 | src/stackops/scripts/python/helpers/helpers_devops/register_interactive.py |  |
| `stackops.scripts.python.helpers.helpers_devops.run_script` | `cli` | `cli-module` | `high` | 1 | 239 | typer, typer-app, cli-registration, get_app, funcs:5 | src/stackops/scripts/python/helpers/helpers_devops/run_script.py |  |
| `stackops.scripts.python.helpers.helpers_devops.themes` | `package` | `package-marker` | `high` | 1 | 5 | - | src/stackops/scripts/python/helpers/helpers_devops/themes/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_devops.themes.choose_wezterm_theme` | `cli-helper` | `cli-helper` | `medium` | 0 | 113 | main, funcs:4 | src/stackops/scripts/python/helpers/helpers_devops/themes/choose_wezterm_theme.py |  |
| `stackops.scripts.python.helpers.helpers_devops.vault` | `cli-helper` | `cli-helper` | `medium` | 0 | 580 | classes:4, funcs:23 | src/stackops/scripts/python/helpers/helpers_devops/vault.py |  |
| `stackops.scripts.python.helpers.helpers_env` | `package` | `package-marker` | `high` | 0 | 3 | - | src/stackops/scripts/python/helpers/helpers_env/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_env.env_manager_tui` | `cli-helper` | `cli-helper` | `medium` | 0 | 228 | main, __main__, classes:4, funcs:4 | src/stackops/scripts/python/helpers/helpers_env/env_manager_tui.py |  |
| `stackops.scripts.python.helpers.helpers_env.path_manager_backend` | `cli-helper` | `cli-helper` | `medium` | 2 | 48 | funcs:3 | src/stackops/scripts/python/helpers/helpers_env/path_manager_backend.py |  |
| `stackops.scripts.python.helpers.helpers_env.path_manager_tui` | `cli-helper` | `cli-helper` | `medium` | 0 | 251 | main, __main__, classes:3, funcs:1 | src/stackops/scripts/python/helpers/helpers_env/path_manager_tui.py |  |
| `stackops.scripts.python.helpers.helpers_fire_command` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/scripts/python/helpers/helpers_fire_command/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_fire_command.cloud_manager` | `cli-helper` | `cli-helper` | `medium` | 0 | 76 | - | src/stackops/scripts/python/helpers/helpers_fire_command/cloud_manager.py |  |
| `stackops.scripts.python.helpers.helpers_fire_command.f` | `cli-helper` | `cli-helper` | `medium` | 0 | 0 | - | src/stackops/scripts/python/helpers/helpers_fire_command/f.py |  |
| `stackops.scripts.python.helpers.helpers_fire_command.file_wrangler` | `cli-helper` | `cli-helper` | `medium` | 3 | 152 | funcs:5 | src/stackops/scripts/python/helpers/helpers_fire_command/file_wrangler.py |  |
| `stackops.scripts.python.helpers.helpers_fire_command.fire_jobs_args_helper` | `cli-helper` | `cli-helper` | `medium` | 2 | 145 | classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_fire_command/fire_jobs_args_helper.py |  |
| `stackops.scripts.python.helpers.helpers_fire_command.fire_jobs_impl` | `cli-helper` | `cli-helper` | `medium` | 1 | 294 | funcs:11 | src/stackops/scripts/python/helpers/helpers_fire_command/fire_jobs_impl.py |  |
| `stackops.scripts.python.helpers.helpers_fire_command.fire_jobs_route_helper` | `cli-helper` | `cli-helper` | `medium` | 2 | 104 | funcs:2 | src/stackops/scripts/python/helpers/helpers_fire_command/fire_jobs_route_helper.py |  |
| `stackops.scripts.python.helpers.helpers_fire_command.fire_jobs_streamlit_helper` | `cli-helper` | `cli-helper` | `medium` | 0 | 0 | - | src/stackops/scripts/python/helpers/helpers_fire_command/fire_jobs_streamlit_helper.py |  |
| `stackops.scripts.python.helpers.helpers_network` | `package` | `package-marker` | `high` | 1 | 0 | api-doc | src/stackops/scripts/python/helpers/helpers_network/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_network.address` | `api-or-cli-helper` | `manual-review` | `low` | 11 | 265 | api-doc, __main__, classes:6, funcs:10 | src/stackops/scripts/python/helpers/helpers_network/address.py |  |
| `stackops.scripts.python.helpers.helpers_network.address_switch` | `api-or-cli-helper` | `manual-review` | `low` | 1 | 139 | api-doc, __main__, funcs:7 | src/stackops/scripts/python/helpers/helpers_network/address_switch.py |  |
| `stackops.scripts.python.helpers.helpers_network.ftpx_impl` | `api-or-cli-helper` | `manual-review` | `low` | 1 | 278 | api-doc, funcs:7 | src/stackops/scripts/python/helpers/helpers_network/ftpx_impl.py |  |
| `stackops.scripts.python.helpers.helpers_network.onetimeshare` | `api-or-cli-helper` | `manual-review` | `low` | 0 | 66 | api-doc | src/stackops/scripts/python/helpers/helpers_network/onetimeshare.py |  |
| `stackops.scripts.python.helpers.helpers_network.ssh` | `package` | `package-marker` | `high` | 0 | 22 | api-doc, __all__, funcs:1 | src/stackops/scripts/python/helpers/helpers_network/ssh/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_add_key_windows` | `api-or-cli-helper` | `manual-review` | `low` | 1 | 24 | api-doc, funcs:1 | src/stackops/scripts/python/helpers/helpers_network/ssh/ssh_add_key_windows.py |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_add_ssh_key` | `api-or-cli-helper` | `manual-review` | `low` | 1 | 230 | api-doc, main, __main__, funcs:2 | src/stackops/scripts/python/helpers/helpers_network/ssh/ssh_add_ssh_key.py |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_cloud_init` | `api-or-cli-helper` | `manual-review` | `low` | 1 | 34 | api-doc, funcs:2 | src/stackops/scripts/python/helpers/helpers_network/ssh/ssh_cloud_init.py |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_darwin` | `api-or-cli-helper` | `manual-review` | `low` | 2 | 297 | api-doc, __main__, funcs:1 | src/stackops/scripts/python/helpers/helpers_network/ssh/ssh_debug_darwin.py |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_darwin_utils` | `api-or-cli-helper` | `manual-review` | `low` | 1 | 22 | api-doc, funcs:2 | src/stackops/scripts/python/helpers/helpers_network/ssh/ssh_debug_darwin_utils.py |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_linux` | `api-or-cli-helper` | `manual-review` | `low` | 2 | 343 | api-doc, __main__, funcs:1 | src/stackops/scripts/python/helpers/helpers_network/ssh/ssh_debug_linux.py |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_linux_utils` | `api-or-cli-helper` | `manual-review` | `low` | 1 | 36 | api-doc, funcs:3 | src/stackops/scripts/python/helpers/helpers_network/ssh/ssh_debug_linux_utils.py |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_windows` | `api-or-cli-helper` | `manual-review` | `low` | 2 | 246 | api-doc, __main__, funcs:1 | src/stackops/scripts/python/helpers/helpers_network/ssh/ssh_debug_windows.py |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_windows_utils` | `api-or-cli-helper` | `manual-review` | `low` | 1 | 35 | api-doc, funcs:3 | src/stackops/scripts/python/helpers/helpers_network/ssh/ssh_debug_windows_utils.py |  |
| `stackops.scripts.python.helpers.helpers_network.ssh.ssh_deploy_key_remote` | `api-or-cli-helper` | `manual-review` | `low` | 1 | 312 | api-doc, funcs:6 | src/stackops/scripts/python/helpers/helpers_network/ssh/ssh_deploy_key_remote.py |  |
| `stackops.scripts.python.helpers.helpers_network.wifi_conn` | `api-or-cli-helper` | `manual-review` | `low` | 1 | 176 | api-doc, classes:1, funcs:10 | src/stackops/scripts/python/helpers/helpers_network/wifi_conn.py |  |
| `stackops.scripts.python.helpers.helpers_network.wifi_conn_platforms.common` | `api-or-cli-helper` | `manual-review` | `low` | 5 | 40 | api-doc, classes:1, funcs:3 | src/stackops/scripts/python/helpers/helpers_network/wifi_conn_platforms/common.py |  |
| `stackops.scripts.python.helpers.helpers_network.wifi_conn_platforms.darwin` | `api-or-cli-helper` | `manual-review` | `low` | 0 | 103 | api-doc, funcs:8 | src/stackops/scripts/python/helpers/helpers_network/wifi_conn_platforms/darwin.py |  |
| `stackops.scripts.python.helpers.helpers_network.wifi_conn_platforms.linux` | `api-or-cli-helper` | `manual-review` | `low` | 0 | 264 | api-doc, classes:1, funcs:15 | src/stackops/scripts/python/helpers/helpers_network/wifi_conn_platforms/linux.py |  |
| `stackops.scripts.python.helpers.helpers_network.wifi_conn_platforms.unsupported` | `api-or-cli-helper` | `manual-review` | `low` | 0 | 47 | api-doc, funcs:7 | src/stackops/scripts/python/helpers/helpers_network/wifi_conn_platforms/unsupported.py |  |
| `stackops.scripts.python.helpers.helpers_network.wifi_conn_platforms.windows` | `api-or-cli-helper` | `manual-review` | `low` | 0 | 148 | api-doc, funcs:6 | src/stackops/scripts/python/helpers/helpers_network/wifi_conn_platforms/windows.py |  |
| `stackops.scripts.python.helpers.helpers_preview` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/scripts/python/helpers/helpers_preview/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_preview.pomodoro` | `cli-helper` | `cli-helper` | `medium` | 0 | 56 | - | src/stackops/scripts/python/helpers/helpers_preview/pomodoro.py |  |
| `stackops.scripts.python.helpers.helpers_preview.preview_impl` | `cli-helper` | `cli-helper` | `medium` | 1 | 328 | funcs:5 | src/stackops/scripts/python/helpers/helpers_preview/preview_impl.py |  |
| `stackops.scripts.python.helpers.helpers_preview.preview_read` | `cli-helper` | `cli-helper` | `medium` | 1 | 40 | funcs:2 | src/stackops/scripts/python/helpers/helpers_preview/preview_read.py |  |
| `stackops.scripts.python.helpers.helpers_preview.scheduler` | `cli-helper` | `cli-helper` | `medium` | 0 | 70 | - | src/stackops/scripts/python/helpers/helpers_preview/scheduler.py |  |
| `stackops.scripts.python.helpers.helpers_preview.start_slidev` | `cli` | `cli-module` | `high` | 0 | 126 | typer, cli-registration, main, __main__, funcs:4 | src/stackops/scripts/python/helpers/helpers_preview/start_slidev.py |  |
| `stackops.scripts.python.helpers.helpers_preview.viewer` | `cli-helper` | `cli-helper` | `medium` | 0 | 55 | - | src/stackops/scripts/python/helpers/helpers_preview/viewer.py |  |
| `stackops.scripts.python.helpers.helpers_preview.viewer_template` | `cli-helper` | `cli-helper` | `medium` | 0 | 138 | - | src/stackops/scripts/python/helpers/helpers_preview/viewer_template.py |  |
| `stackops.scripts.python.helpers.helpers_repos.action` | `cli-helper` | `cli-helper` | `medium` | 1 | 218 | funcs:2 | src/stackops/scripts/python/helpers/helpers_repos/action.py |  |
| `stackops.scripts.python.helpers.helpers_repos.action_helper` | `cli-helper` | `cli-helper` | `medium` | 1 | 151 | classes:3, funcs:1 | src/stackops/scripts/python/helpers/helpers_repos/action_helper.py |  |
| `stackops.scripts.python.helpers.helpers_repos.clone` | `cli-helper` | `cli-helper` | `medium` | 1 | 121 | funcs:6 | src/stackops/scripts/python/helpers/helpers_repos/clone.py |  |
| `stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync` | `cli` | `cli-module` | `high` | 1 | 460 | typer, main, classes:1, funcs:15 | src/stackops/scripts/python/helpers/helpers_repos/cloud_repo_sync.py |  |
| `stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_conflicts` | `cli-helper` | `cli-helper` | `medium` | 1 | 92 | funcs:5 | src/stackops/scripts/python/helpers/helpers_repos/cloud_repo_sync_conflicts.py |  |
| `stackops.scripts.python.helpers.helpers_repos.grource` | `cli` | `cli-module` | `high` | 1 | 342 | typer, typer-app, cli-registration, __main__, funcs:6 | src/stackops/scripts/python/helpers/helpers_repos/grource.py |  |
| `stackops.scripts.python.helpers.helpers_repos.record` | `cli` | `cli-module` | `high` | 1 | 345 | typer, funcs:12 | src/stackops/scripts/python/helpers/helpers_repos/record.py |  |
| `stackops.scripts.python.helpers.helpers_repos.repo_analyzer_1` | `cli-helper` | `cli-helper` | `medium` | 1 | 158 | funcs:5 | src/stackops/scripts/python/helpers/helpers_repos/repo_analyzer_1.py |  |
| `stackops.scripts.python.helpers.helpers_repos.repo_analyzer_2` | `cli-helper` | `cli-helper` | `medium` | 1 | 313 | classes:2, funcs:2 | src/stackops/scripts/python/helpers/helpers_repos/repo_analyzer_2.py |  |
| `stackops.scripts.python.helpers.helpers_repos.spec_store` | `cli-helper` | `cli-helper` | `medium` | 2 | 120 | classes:2, funcs:10 | src/stackops/scripts/python/helpers/helpers_repos/spec_store.py |  |
| `stackops.scripts.python.helpers.helpers_repos.sync` | `cli-helper` | `cli-helper` | `medium` | 1 | 94 | funcs:4 | src/stackops/scripts/python/helpers/helpers_repos/sync.py |  |
| `stackops.scripts.python.helpers.helpers_repos.update` | `cli-helper` | `cli-helper` | `medium` | 3 | 261 | classes:1, funcs:4 | src/stackops/scripts/python/helpers/helpers_repos/update.py |  |
| `stackops.scripts.python.helpers.helpers_search.ast_search` | `cli-helper` | `cli-helper` | `medium` | 1 | 139 | classes:1, funcs:9 | src/stackops/scripts/python/helpers/helpers_search/ast_search.py |  |
| `stackops.scripts.python.helpers.helpers_search.qr_code` | `cli-helper` | `cli-helper` | `medium` | 0 | 169 | funcs:3 | src/stackops/scripts/python/helpers/helpers_search/qr_code.py |  |
| `stackops.scripts.python.helpers.helpers_search.repo_rag` | `cli-helper` | `cli-helper` | `medium` | 0 | 326 | - | src/stackops/scripts/python/helpers/helpers_search/repo_rag.py |  |
| `stackops.scripts.python.helpers.helpers_search.script_help` | `cli-helper` | `cli-helper` | `medium` | 2 | 71 | funcs:1 | src/stackops/scripts/python/helpers/helpers_search/script_help.py |  |
| `stackops.scripts.python.helpers.helpers_search.semantic_search` | `cli-helper` | `cli-helper` | `medium` | 0 | 26 | - | src/stackops/scripts/python/helpers/helpers_search/semantic_search.py |  |
| `stackops.scripts.python.helpers.helpers_seek` | `package` | `package-marker` | `high` | 0 | 4 | - | src/stackops/scripts/python/helpers/helpers_seek/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_seek.scripts_linux` | `package` | `package-marker` | `high` | 1 | 3 | - | src/stackops/scripts/python/helpers/helpers_seek/scripts_linux/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_seek.scripts_macos` | `package` | `package-marker` | `high` | 1 | 2 | - | src/stackops/scripts/python/helpers/helpers_seek/scripts_macos/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_seek.scripts_windows` | `package` | `package-marker` | `high` | 1 | 2 | - | src/stackops/scripts/python/helpers/helpers_seek/scripts_windows/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_seek.seek_impl` | `cli-helper` | `cli-helper` | `medium` | 1 | 466 | funcs:18 | src/stackops/scripts/python/helpers/helpers_seek/seek_impl.py |  |
| `stackops.scripts.python.helpers.helpers_sessions` | `package` | `package-marker` | `high` | 1 | 0 | - | src/stackops/scripts/python/helpers/helpers_sessions/__init__.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._herdr_backend` | `cli-helper` | `cli-helper` | `medium` | 2 | 447 | funcs:25 | src/stackops/scripts/python/helpers/helpers_sessions/_herdr_backend.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._tmux_backend` | `cli-helper` | `cli-helper` | `medium` | 3 | 208 | funcs:7 | src/stackops/scripts/python/helpers/helpers_sessions/_tmux_backend.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._tmux_backend_options` | `cli-helper` | `cli-helper` | `medium` | 1 | 144 | funcs:7 | src/stackops/scripts/python/helpers/helpers_sessions/_tmux_backend_options.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._tmux_backend_preview` | `cli-helper` | `cli-helper` | `medium` | 3 | 205 | funcs:9 | src/stackops/scripts/python/helpers/helpers_sessions/_tmux_backend_preview.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._tmux_backend_processes` | `cli-helper` | `cli-helper` | `medium` | 3 | 136 | funcs:7 | src/stackops/scripts/python/helpers/helpers_sessions/_tmux_backend_processes.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._zellij_backend` | `cli-helper` | `cli-helper` | `medium` | 2 | 278 | funcs:10 | src/stackops/scripts/python/helpers/helpers_sessions/_zellij_backend.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._zellij_backend_focus` | `cli-helper` | `cli-helper` | `medium` | 1 | 146 | funcs:7 | src/stackops/scripts/python/helpers/helpers_sessions/_zellij_backend_focus.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._zellij_backend_layout` | `cli-helper` | `cli-helper` | `medium` | 1 | 118 | classes:2, funcs:4 | src/stackops/scripts/python/helpers/helpers_sessions/_zellij_backend_layout.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._zellij_backend_metadata` | `cli-helper` | `cli-helper` | `medium` | 2 | 161 | funcs:10 | src/stackops/scripts/python/helpers/helpers_sessions/_zellij_backend_metadata.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._zellij_backend_options` | `cli-helper` | `cli-helper` | `medium` | 1 | 257 | funcs:7 | src/stackops/scripts/python/helpers/helpers_sessions/_zellij_backend_options.py |  |
| `stackops.scripts.python.helpers.helpers_sessions._zellij_backend_preview` | `cli-helper` | `cli-helper` | `medium` | 1 | 82 | funcs:5 | src/stackops/scripts/python/helpers/helpers_sessions/_zellij_backend_preview.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.attach_impl` | `cli-helper` | `cli-helper` | `medium` | 5 | 131 | funcs:9 | src/stackops/scripts/python/helpers/helpers_sessions/attach_impl.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.kill_impl` | `cli-helper` | `cli-helper` | `medium` | 1 | 24 | funcs:1 | src/stackops/scripts/python/helpers/helpers_sessions/kill_impl.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.session_trace_tmux` | `cli-helper` | `cli-helper` | `medium` | 2 | 219 | classes:2, funcs:6 | src/stackops/scripts/python/helpers/helpers_sessions/session_trace_tmux.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.session_trace_zellij` | `cli-helper` | `cli-helper` | `medium` | 1 | 16 | funcs:1 | src/stackops/scripts/python/helpers/helpers_sessions/session_trace_zellij.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_aoe_impl` | `cli-helper` | `cli-helper` | `medium` | 1 | 279 | classes:2, funcs:12 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_aoe_impl.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_cli_common` | `cli` | `cli-module` | `high` | 2 | 198 | typer, funcs:6 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_cli_common.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_cli_run` | `cli` | `cli-module` | `high` | 1 | 86 | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_cli_run.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_cli_run_all` | `cli` | `cli-module` | `high` | 1 | 72 | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_cli_run_all.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_cli_run_aoe` | `cli` | `cli-module` | `high` | 1 | 176 | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_cli_run_aoe.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_dynamic` | `cli-helper` | `cli-helper` | `medium` | 1 | 262 | funcs:7 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_dynamic.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_dynamic_display` | `cli-helper` | `cli-helper` | `medium` | 3 | 189 | classes:3, funcs:11 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_dynamic_display.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_dynamic_tmux` | `cli-helper` | `cli-helper` | `medium` | 0 | 98 | funcs:9 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_dynamic_tmux.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_dynamic_zellij` | `cli-helper` | `cli-helper` | `medium` | 0 | 80 | funcs:6 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_dynamic_zellij.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_impl` | `cli-helper` | `cli-helper` | `medium` | 4 | 226 | __main__, funcs:5 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_impl.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_layout_source` | `cli` | `cli-module` | `high` | 2 | 229 | typer, classes:1, funcs:8 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_layout_source.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_multiprocess` | `cli` | `cli-module` | `high` | 1 | 62 | typer, funcs:1 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_multiprocess.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_test_layouts` | `cli-helper` | `cli-helper` | `medium` | 1 | 164 | classes:1, funcs:5 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_test_layouts.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.sessions_trace` | `cli` | `cli-module` | `high` | 1 | 330 | typer, __all__, funcs:14 | src/stackops/scripts/python/helpers/helpers_sessions/sessions_trace.py |  |
| `stackops.scripts.python.helpers.helpers_sessions.utils` | `cli-helper` | `cli-helper` | `medium` | 1 | 101 | funcs:2 | src/stackops/scripts/python/helpers/helpers_sessions/utils.py |  |
| `stackops.scripts.python.helpers.helpers_utils.download` | `cli` | `cli-module` | `high` | 3 | 151 | typer, __main__, funcs:1 | src/stackops/scripts/python/helpers/helpers_utils/download.py |  |
| `stackops.scripts.python.helpers.helpers_utils.file_utils_app` | `cli` | `cli-module` | `high` | 2 | 291 | typer, typer-app, cli-registration, get_app, funcs:8 | src/stackops/scripts/python/helpers/helpers_utils/file_utils_app.py |  |
| `stackops.scripts.python.helpers.helpers_utils.machine_utils_app` | `cli` | `cli-module` | `high` | 1 | 140 | typer, typer-app, cli-registration, get_app, funcs:6 | src/stackops/scripts/python/helpers/helpers_utils/machine_utils_app.py |  |
| `stackops.scripts.python.helpers.helpers_utils.path_reference_validation` | `cli-helper` | `cli-helper` | `medium` | 1 | 310 | classes:4, funcs:14 | src/stackops/scripts/python/helpers/helpers_utils/path_reference_validation.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pdf` | `cli` | `cli-module` | `high` | 1 | 98 | typer, funcs:2 | src/stackops/scripts/python/helpers/helpers_utils/pdf.py |  |
| `stackops.scripts.python.helpers.helpers_utils.pyproject_utils_app` | `cli` | `cli-module` | `high` | 1 | 421 | typer, typer-app, cli-registration, get_app, funcs:12 | src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_app.py |  |
| `stackops.scripts.python.helpers.helpers_utils.python` | `cli` | `cli-module` | `high` | 5 | 326 | typer, __main__, classes:1, funcs:12 | src/stackops/scripts/python/helpers/helpers_utils/python.py |  |
| `stackops.scripts.python.helpers.helpers_utils.read_db_cli_tui` | `cli-helper` | `cli-helper` | `medium` | 1 | 38 | funcs:1 | src/stackops/scripts/python/helpers/helpers_utils/read_db_cli_tui.py |  |
| `stackops.scripts.python.helpers.helpers_utils.read_db_cli_tui_backend` | `cli` | `cli-module` | `high` | 4 | 381 | typer, funcs:22 | src/stackops/scripts/python/helpers/helpers_utils/read_db_cli_tui_backend.py |  |
| `stackops.scripts.python.helpers.helpers_utils.scrape` | `cli` | `cli-module` | `high` | 2 | 89 | typer, funcs:3 | src/stackops/scripts/python/helpers/helpers_utils/scrape.py |  |
| `stackops.scripts.python.helpers.helpers_utils.specs` | `cli-helper` | `cli-helper` | `medium` | 1 | 313 | main, __main__, funcs:8 | src/stackops/scripts/python/helpers/helpers_utils/specs.py |  |
| `stackops.scripts.python.helpers.helpers_utils.surya` | `cli-helper` | `cli-helper` | `medium` | 2 | 100 | funcs:3 | src/stackops/scripts/python/helpers/helpers_utils/surya.py |  |
| `stackops.scripts.python.helpers.helpers_utils.test_runtime` | `cli` | `cli-module` | `high` | 0 | 181 | typer, typer-app, get_app, classes:1, funcs:11 | src/stackops/scripts/python/helpers/helpers_utils/test_runtime.py |  |
| `stackops.scripts.python.helpers.helpers_utils.type_fix` | `cli` | `cli-module` | `high` | 0 | 71 | typer, typer-app, get_app, funcs:5 | src/stackops/scripts/python/helpers/helpers_utils/type_fix.py |  |
| `stackops.scripts.python.preview` | `cli` | `cli-entrypoint` | `high` | 1 | 105 | entry:preview, typer, cli-registration, main, __main__, funcs:6 | src/stackops/scripts/python/preview.py |  |
| `stackops.scripts.python.seek` | `cli` | `cli-entrypoint` | `high` | 1 | 74 | entry:seek, typer, typer-app, cli-registration, get_app, main, funcs:4 | src/stackops/scripts/python/seek.py |  |
| `stackops.scripts.python.stackops_entry` | `cli` | `cli-entrypoint` | `high` | 0 | 152 | entry:stackops, typer, typer-app, cli-registration, get_app, main, __main__, funcs:11 | src/stackops/scripts/python/stackops_entry.py |  |
| `stackops.scripts.python.terminal` | `cli` | `cli-entrypoint` | `high` | 4 | 521 | entry:terminal, typer, typer-app, cli-registration, get_app, main, __main__, funcs:14 | src/stackops/scripts/python/terminal.py |  |
| `stackops.scripts.python.utils` | `cli` | `cli-entrypoint` | `high` | 1 | 60 | entry:utils, typer, typer-app, cli-registration, get_app, main, __main__, funcs:3 | src/stackops/scripts/python/utils.py |  |
| `stackops.scripts.setup.linux` | `package` | `package-marker` | `high` | 1 | 5 | - | src/stackops/scripts/setup/linux/__init__.py |  |
| `stackops.scripts.setup.macos` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/scripts/setup/macos/__init__.py |  |
| `stackops.scripts.setup.windows` | `package` | `package-marker` | `high` | 1 | 5 | - | src/stackops/scripts/setup/windows/__init__.py |  |
| `stackops.scripts.windows` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/scripts/windows/__init__.py |  |
| `stackops.secrets` | `package` | `package-marker` | `medium` | 6 | 7 | - | src/stackops/secrets/__init__.py | Was `secrets.py`; now a package with submodules: assets, loader, models, paths, readers, search. |
| `stackops.settings` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/settings/__init__.py |  |
| `stackops.settings.atuin` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/settings/atuin/__init__.py |  |
| `stackops.settings.atuin.themes` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/settings/atuin/themes/__init__.py |  |
| `stackops.settings.broot` | `package` | `package-marker` | `high` | 0 | 4 | - | src/stackops/settings/broot/__init__.py |  |
| `stackops.settings.glow` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/settings/glow/__init__.py |  |
| `stackops.settings.gromit-mpx` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/settings/gromit-mpx/__init__.py |  |
| `stackops.settings.helix` | `package` | `package-marker` | `high` | 0 | 4 | - | src/stackops/settings/helix/__init__.py |  |
| `stackops.settings.keras` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/settings/keras/__init__.py |  |
| `stackops.settings.keyboard.espanso.config` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/settings/keyboard/espanso/config/__init__.py |  |
| `stackops.settings.keyboard.espanso.match` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/settings/keyboard/espanso/match/__init__.py |  |
| `stackops.settings.keyboard.kanata` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/settings/keyboard/kanata/__init__.py |  |
| `stackops.settings.lf.linux` | `package` | `package-marker` | `high` | 0 | 4 | - | src/stackops/settings/lf/linux/__init__.py |  |
| `stackops.settings.lf.linux.autocall` | `package` | `package-marker` | `high` | 0 | 8 | - | src/stackops/settings/lf/linux/autocall/__init__.py |  |
| `stackops.settings.lf.linux.exe` | `package` | `package-marker` | `high` | 0 | 6 | - | src/stackops/settings/lf/linux/exe/__init__.py |  |
| `stackops.settings.lf.windows` | `package` | `package-marker` | `high` | 0 | 12 | - | src/stackops/settings/lf/windows/__init__.py |  |
| `stackops.settings.lf.windows.autocall` | `package` | `package-marker` | `high` | 0 | 8 | - | src/stackops/settings/lf/windows/autocall/__init__.py |  |
| `stackops.settings.linters` | `package` | `package-marker` | `high` | 0 | 3 | - | src/stackops/settings/linters/__init__.py |  |
| `stackops.settings.lvim.linux` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/settings/lvim/linux/__init__.py |  |
| `stackops.settings.lvim.windows` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/settings/lvim/windows/__init__.py |  |
| `stackops.settings.lvim.windows.archive` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/settings/lvim/windows/archive/__init__.py |  |
| `stackops.settings.lvim.windows.lua.user` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/settings/lvim/windows/lua/user/__init__.py |  |
| `stackops.settings.marimo` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/settings/marimo/__init__.py |  |
| `stackops.settings.marimo.snippets.globalize` | `asset` | `config-asset` | `high` | 0 | 34 | __main__, funcs:3 | src/stackops/settings/marimo/snippets/globalize.py |  |
| `stackops.settings.mprocs.windows` | `package` | `package-marker` | `high` | 0 | 3 | - | src/stackops/settings/mprocs/windows/__init__.py |  |
| `stackops.settings.ollama` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/settings/ollama/__init__.py |  |
| `stackops.settings.pistol` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/settings/pistol/__init__.py |  |
| `stackops.settings.presenterm` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/settings/presenterm/__init__.py |  |
| `stackops.settings.psmux` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/settings/psmux/__init__.py |  |
| `stackops.settings.pudb` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/settings/pudb/__init__.py |  |
| `stackops.settings.rofi` | `package` | `package-marker` | `high` | 0 | 3 | - | src/stackops/settings/rofi/__init__.py |  |
| `stackops.settings.shells.alacritty` | `package` | `package-marker` | `high` | 0 | 3 | - | src/stackops/settings/shells/alacritty/__init__.py |  |
| `stackops.settings.shells.bash` | `package` | `package-marker` | `high` | 3 | 2 | - | src/stackops/settings/shells/bash/__init__.py |  |
| `stackops.settings.shells.ghostty` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/settings/shells/ghostty/__init__.py |  |
| `stackops.settings.shells.ipy.profiles.default` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/settings/shells/ipy/profiles/default/__init__.py |  |
| `stackops.settings.shells.ipy.profiles.default.startup` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/settings/shells/ipy/profiles/default/startup/__init__.py |  |
| `stackops.settings.shells.ipy.profiles.default.startup.playext` | `asset` | `config-asset` | `high` | 0 | 85 | - | src/stackops/settings/shells/ipy/profiles/default/startup/playext.py |  |
| `stackops.settings.shells.kitty` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/settings/shells/kitty/__init__.py |  |
| `stackops.settings.shells.nushell` | `package` | `package-marker` | `high` | 1 | 4 | - | src/stackops/settings/shells/nushell/__init__.py |  |
| `stackops.settings.shells.pwsh` | `package` | `package-marker` | `high` | 3 | 3 | - | src/stackops/settings/shells/pwsh/__init__.py |  |
| `stackops.settings.shells.starship` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/settings/shells/starship/__init__.py |  |
| `stackops.settings.shells.vtm` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/settings/shells/vtm/__init__.py |  |
| `stackops.settings.shells.wezterm` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/settings/shells/wezterm/__init__.py |  |
| `stackops.settings.shells.wt` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/settings/shells/wt/__init__.py |  |
| `stackops.settings.shells.zsh` | `package` | `package-marker` | `high` | 2 | 2 | - | src/stackops/settings/shells/zsh/__init__.py |  |
| `stackops.settings.streamlit` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/settings/streamlit/__init__.py |  |
| `stackops.settings.svim.linux` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/settings/svim/linux/__init__.py |  |
| `stackops.settings.svim.windows` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/settings/svim/windows/__init__.py |  |
| `stackops.settings.television.cable_unix` | `package` | `package-marker` | `high` | 0 | 54 | - | src/stackops/settings/television/cable_unix/__init__.py |  |
| `stackops.settings.television.cable_windows` | `package` | `package-marker` | `high` | 0 | 15 | - | src/stackops/settings/television/cable_windows/__init__.py |  |
| `stackops.settings.tere` | `package` | `package-marker` | `high` | 0 | 3 | - | src/stackops/settings/tere/__init__.py |  |
| `stackops.settings.tmux` | `package` | `package-marker` | `high` | 1 | 2 | - | src/stackops/settings/tmux/__init__.py |  |
| `stackops.settings.tv` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/settings/tv/__init__.py |  |
| `stackops.settings.tv.themes` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/settings/tv/themes/__init__.py |  |
| `stackops.settings.wt` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/settings/wt/__init__.py |  |
| `stackops.settings.wt.set_wt_settings` | `asset` | `config-asset` | `high` | 1 | 129 | main, __main__, funcs:3 | src/stackops/settings/wt/set_wt_settings.py |  |
| `stackops.settings.yazi` | `package` | `package-marker` | `high` | 0 | 9 | - | src/stackops/settings/yazi/__init__.py |  |
| `stackops.settings.yazi.scripts` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/settings/yazi/scripts/__init__.py |  |
| `stackops.settings.yazi.scripts.compress_selected` | `script-asset` | `script-asset` | `medium` | 0 | 70 | main, __main__, funcs:6 | src/stackops/settings/yazi/scripts/compress_selected.py |  |
| `stackops.settings.yazi.scripts.copy_file_content` | `script-asset` | `script-asset` | `medium` | 0 | 83 | main, __main__, funcs:4 | src/stackops/settings/yazi/scripts/copy_file_content.py |  |
| `stackops.settings.yazi.scripts.fullscreen_preview` | `script-asset` | `script-asset` | `medium` | 1 | 349 | main, __main__, funcs:25 | src/stackops/settings/yazi/scripts/fullscreen_preview.py |  |
| `stackops.settings.yazi.scripts.interactive_view` | `script-asset` | `script-asset` | `medium` | 1 | 127 | main, __main__, funcs:9 | src/stackops/settings/yazi/scripts/interactive_view.py |  |
| `stackops.settings.yazi.scripts.open_db_readonly` | `script-asset` | `script-asset` | `medium` | 0 | 77 | main, __main__, funcs:7 | src/stackops/settings/yazi/scripts/open_db_readonly.py |  |
| `stackops.settings.yazi.scripts.open_default_app` | `script-asset` | `script-asset` | `medium` | 0 | 291 | main, __main__, classes:1, funcs:16 | src/stackops/settings/yazi/scripts/open_default_app.py |  |
| `stackops.settings.yazi.scripts.serve_browser_file` | `script-asset` | `script-asset` | `medium` | 0 | 252 | main, __main__, classes:1, funcs:12 | src/stackops/settings/yazi/scripts/serve_browser_file.py |  |
| `stackops.settings.yazi.shell` | `package` | `package-marker` | `high` | 0 | 3 | - | src/stackops/settings/yazi/shell/__init__.py |  |
| `stackops.settings.zed` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/settings/zed/__init__.py |  |
| `stackops.settings.zellij` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/settings/zellij/__init__.py |  |
| `stackops.settings.zellij.commands` | `package` | `package-marker` | `high` | 0 | 3 | - | src/stackops/settings/zellij/commands/__init__.py |  |
| `stackops.settings.zellij.layouts` | `package` | `package-marker` | `high` | 1 | 6 | - | src/stackops/settings/zellij/layouts/__init__.py |  |
| `stackops.utils` | `package` | `package-marker` | `high` | 3 | 0 | api-doc | src/stackops/utils/__init__.py |  |
| `stackops.utils.accessories` | `api` | `api-cli-bridge` | `medium` | 48 | 137 | api-doc, __main__, funcs:8 | src/stackops/utils/accessories.py |  |
| `stackops.utils.ai` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/utils/ai/__init__.py |  |
| `stackops.utils.cli_utils` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/utils/cli_utils/__init__.py |  |
| `stackops.utils.cli_utils.hierarchy` | `cli-helper` | `cli-helper` | `medium` | 0 | 1398 | - | src/stackops/utils/cli_utils/hierarchy.py |  |
| `stackops.utils.cli_utils.hierarchy_types` | `cli-helper` | `cli-helper` | `medium` | 1 | 1660 | - | src/stackops/utils/cli_utils/hierarchy_types.py |  |
| `stackops.utils.cloud.onedrive` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/utils/cloud/onedrive/__init__.py |  |
| `stackops.utils.cloud.onedrive.auth` | `api` | `python-api-candidate` | `medium` | 2 | 290 | funcs:15 | src/stackops/utils/cloud/onedrive/auth.py |  |
| `stackops.utils.cloud.onedrive.file_ops` | `api` | `python-api-candidate` | `medium` | 0 | 167 | funcs:5 | src/stackops/utils/cloud/onedrive/file_ops.py |  |
| `stackops.utils.cloud.onedrive.setup_oauth` | `api-or-script` | `manual-review` | `medium` | 0 | 61 | main, __main__, funcs:1 | src/stackops/utils/cloud/onedrive/setup_oauth.py |  |
| `stackops.utils.cloud.defaults` | `api` | `python-api` | `high` | 4 | 32 | api-doc, classes:1, funcs:1 | src/stackops/utils/cloud/defaults.py | Was `utils.cloud_defaults`; moved under `cloud/`. |
| `stackops.utils.code` | `api` | `python-api` | `high` | 46 | 232 | api-doc, funcs:11 | src/stackops/utils/code.py |  |
| `stackops.utils.cloud.encryption` | `api` | `python-api-candidate` | `medium` | 4 | 15 | funcs:1 | src/stackops/utils/cloud/encryption.py | Was `utils.encryption`; moved under `cloud/`. |
| `stackops.utils.files.art` | `package` | `package-marker` | `high` | 0 | 5 | - | src/stackops/utils/files/art/__init__.py |  |
| `stackops.utils.files.ascii_art` | `api-or-script` | `manual-review` | `medium` | 1 | 118 | __main__, classes:3, funcs:4 | src/stackops/utils/files/ascii_art.py |  |
| `stackops.utils.files.dbms` | `api-or-script` | `manual-review` | `medium` | 1 | 300 | __main__, classes:1, funcs:3 | src/stackops/utils/files/dbms.py |  |
| `stackops.utils.files.f` | `api` | `python-api-candidate` | `medium` | 0 | 26 | classes:1, funcs:1 | src/stackops/utils/files/f.py |  |
| `stackops.utils.files.headers` | `api` | `python-api-candidate` | `medium` | 1 | 70 | funcs:2 | src/stackops/utils/files/headers.py |  |
| `stackops.utils.files.notebook` | `api` | `python-api-candidate` | `medium` | 0 | 49 | funcs:1 | src/stackops/utils/files/notebook.py |  |
| `stackops.utils.files.ouch` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/utils/files/ouch/__init__.py |  |
| `stackops.utils.files.ouch.decompress` | `api` | `python-api-candidate` | `medium` | 1 | 46 | funcs:1 | src/stackops/utils/files/ouch/decompress.py |  |
| `stackops.utils.files.read` | `api-or-script` | `manual-review` | `medium` | 15 | 149 | __main__, funcs:16 | src/stackops/utils/files/read.py |  |
| `stackops.utils.installer_utils` | `package` | `package-marker` | `high` | 5 | 2 | api-doc | src/stackops/utils/installer_utils/__init__.py |  |
| `stackops.utils.installer_utils.github_release_bulk` | `api` | `python-api` | `high` | 2 | 144 | api-doc, classes:3, funcs:6 | src/stackops/utils/installer_utils/github_release_bulk.py |  |
| `stackops.utils.installer_utils.github_release_scraper` | `api` | `python-api` | `high` | 1 | 100 | api-doc, funcs:5 | src/stackops/utils/installer_utils/github_release_scraper.py |  |
| `stackops.utils.installer_utils.install_from_url` | `api` | `python-api` | `high` | 1 | 260 | api-doc, classes:1, funcs:7 | src/stackops/utils/installer_utils/install_from_url.py |  |
| `stackops.utils.installer_utils.install_request_logic` | `api` | `python-api` | `high` | 1 | 87 | api-doc, classes:2, funcs:5 | src/stackops/utils/installer_utils/install_request_logic.py |  |
| `stackops.utils.installer_utils.installer_class` | `api` | `python-api` | `high` | 14 | 393 | api-doc, classes:1 | src/stackops/utils/installer_utils/installer_class.py |  |
| `stackops.utils.installer_utils.installer_cli` | `api` | `api-cli-bridge` | `medium` | 16 | 261 | api-doc, typer, classes:1, funcs:8 | src/stackops/utils/installer_utils/installer_cli.py |  |
| `stackops.utils.installer_utils.installer_explore` | `api` | `api-cli-bridge` | `medium` | 1 | 253 | api-doc, typer, classes:3, funcs:10 | src/stackops/utils/installer_utils/installer_explore.py |  |
| `stackops.utils.installer_utils.installer_helper` | `api` | `python-api` | `high` | 3 | 176 | api-doc, funcs:6 | src/stackops/utils/installer_utils/installer_helper.py |  |
| `stackops.utils.installer_utils.installer_locator_utils` | `api` | `python-api` | `high` | 15 | 378 | api-doc, funcs:13 | src/stackops/utils/installer_utils/installer_locator_utils.py |  |
| `stackops.utils.installer_utils.installer_offline` | `api` | `api-cli-bridge` | `medium` | 0 | 72 | api-doc, __main__, funcs:1 | src/stackops/utils/installer_utils/installer_offline.py |  |
| `stackops.utils.installer_utils.installer_offline_constants` | `api` | `python-api` | `high` | 0 | 73 | api-doc, funcs:2 | src/stackops/utils/installer_utils/installer_offline_constants.py |  |
| `stackops.utils.installer_utils.installer_offline_models` | `api` | `python-api` | `high` | 6 | 41 | api-doc, classes:4 | src/stackops/utils/installer_utils/installer_offline_models.py |  |
| `stackops.utils.installer_utils.installer_offline_publish` | `api` | `python-api` | `high` | 1 | 102 | api-doc, funcs:6 | src/stackops/utils/installer_utils/installer_offline_publish.py |  |
| `stackops.utils.installer_utils.installer_offline_render` | `api` | `python-api` | `high` | 1 | 69 | api-doc, funcs:3 | src/stackops/utils/installer_utils/installer_offline_render.py |  |
| `stackops.utils.installer_utils.installer_offline_scripts` | `api` | `python-api` | `high` | 1 | 143 | api-doc, funcs:1 | src/stackops/utils/installer_utils/installer_offline_scripts.py |  |
| `stackops.utils.installer_utils.installer_offline_steps` | `api` | `python-api` | `high` | 1 | 46 | api-doc, funcs:3 | src/stackops/utils/installer_utils/installer_offline_steps.py |  |
| `stackops.utils.installer_utils.installer_offline_uv` | `api` | `python-api` | `high` | 1 | 110 | api-doc, funcs:6 | src/stackops/utils/installer_utils/installer_offline_uv.py |  |
| `stackops.utils.installer_utils.installer_runner` | `api` | `python-api` | `high` | 5 | 199 | api-doc, funcs:6 | src/stackops/utils/installer_utils/installer_runner.py |  |
| `stackops.utils.installer_utils.installer_summary` | `api` | `python-api` | `high` | 3 | 124 | api-doc, funcs:8 | src/stackops/utils/installer_utils/installer_summary.py |  |
| `stackops.utils.io` | `api` | `python-api` | `high` | 20 | 374 | api-doc, classes:1, funcs:24 | src/stackops/utils/io.py |  |
| `stackops.utils.meta` | `api` | `api-cli-bridge` | `medium` | 12 | 259 | api-doc, __main__, funcs:2 | src/stackops/utils/meta.py |  |
| `stackops.utils.options_utils.options` | `api` | `python-api` | `high` | 19 | 325 | api-doc, funcs:8 | src/stackops/utils/options_utils/options.py | Was `utils.options`; moved under `options_utils/`. |
| `stackops.utils.options_utils` | `package` | `package-marker` | `high` | 0 | 0 | - | src/stackops/utils/options_utils/__init__.py |  |
| `stackops.utils.options_utils.options_tv_linux` | `api-or-script` | `manual-review` | `medium` | 1 | 215 | __main__, funcs:7 | src/stackops/utils/options_utils/options_tv_linux.py |  |
| `stackops.utils.options_utils.options_tv_windows` | `api-or-script` | `manual-review` | `medium` | 1 | 101 | __main__, funcs:5 | src/stackops/utils/options_utils/options_tv_windows.py |  |
| `stackops.utils.options_utils.textual_options_form` | `api` | `python-api-candidate` | `medium` | 1 | 339 | classes:5, funcs:12 | src/stackops/utils/options_utils/textual_options_form.py |  |
| `stackops.utils.options_utils.textual_options_form_types` | `api-or-script` | `manual-review` | `medium` | 2 | 108 | __main__, classes:2, funcs:2 | src/stackops/utils/options_utils/textual_options_form_types.py |  |
| `stackops.utils.options_utils.tv_options` | `api` | `api-cli-bridge` | `medium` | 17 | 44 | api-doc, __main__, funcs:3 | src/stackops/utils/options_utils/tv_options.py |  |
| `stackops.utils.path_core` | `api` | `python-api` | `high` | 26 | 393 | api-doc, __all__, funcs:20 | src/stackops/utils/path_core.py |  |
| `stackops.utils.path_reference` | `api` | `python-api` | `high` | 36 | 20 | api-doc, funcs:3 | src/stackops/utils/path_reference.py |  |
| `stackops.utils.cloud.rclone` | `api` | `python-api-candidate` | `medium` | 2 | 177 | classes:1, funcs:10 | src/stackops/utils/cloud/rclone.py | Was `utils.rclone`; moved under `cloud/`. |
| `stackops.utils.cloud.rclone_wrapper` | `api` | `python-api-candidate` | `medium` | 5 | 166 | funcs:8 | src/stackops/utils/cloud/rclone_wrapper.py | Was `utils.rclone_wrapper`; moved under `cloud/`. |
| `stackops.cluster.scheduler` | `api` | `python-api` | `high` | 6 | 268 | api-doc, classes:4, funcs:2 | src/stackops/cluster/scheduler.py | Was `utils.scheduler`; moved to `cluster/`. |
| `stackops.utils.schemas` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/utils/schemas/__init__.py |  |
| `stackops.utils.schemas.agents` | `package` | `package-marker` | `high` | 1 | 3 | - | src/stackops/utils/schemas/agents/__init__.py |  |
| `stackops.utils.schemas.config` | `package` | `package-marker` | `high` | 1 | 15 | __all__ | src/stackops/utils/schemas/config/__init__.py |  |
| `stackops.utils.schemas.config.config_types` | `api` | `python-api-candidate` | `medium` | 3 | 17 | - | src/stackops/utils/schemas/config/config_types.py |  |
| `stackops.utils.schemas.fire_agents.fire_agents_input` | `api` | `python-api-candidate` | `medium` | 0 | 64 | classes:6 | src/stackops/utils/schemas/fire_agents/fire_agents_input.py |  |
| `stackops.utils.schemas.installer` | `package` | `package-marker` | `high` | 3 | 3 | api-doc | src/stackops/utils/schemas/installer/__init__.py |  |
| `stackops.utils.schemas.installer.installer_types` | `api` | `python-api` | `high` | 33 | 144 | api-doc, classes:6, funcs:2 | src/stackops/utils/schemas/installer/installer_types.py |  |
| `stackops.utils.schemas.layouts` | `package` | `package-marker` | `high` | 1 | 3 | - | src/stackops/utils/schemas/layouts/__init__.py |  |
| `stackops.utils.schemas.layouts.layout_types` | `api` | `python-api` | `high` | 43 | 71 | api-doc, classes:3, funcs:2 | src/stackops/utils/schemas/layouts/layout_types.py |  |
| `stackops.utils.schemas.mapper` | `package` | `package-marker` | `high` | 3 | 5 | - | src/stackops/utils/schemas/mapper/__init__.py |  |
| `stackops.utils.schemas.repos` | `package` | `package-marker` | `high` | 0 | 2 | - | src/stackops/utils/schemas/repos/__init__.py |  |
| `stackops.utils.schemas.repos.repos_types` | `api` | `python-api-candidate` | `medium` | 3 | 26 | classes:4 | src/stackops/utils/schemas/repos/repos_types.py |  |
| `stackops.utils.source_of_truth` | `api` | `api-cli-bridge` | `medium` | 55 | 208 | api-doc, __main__, funcs:11 | src/stackops/utils/source_of_truth.py |  |
| `stackops.utils.ssh_utils.ssh` | `api` | `api-cli-bridge` | `medium` | 8 | 469 | api-doc, __main__, classes:1 | src/stackops/utils/ssh_utils/ssh.py | Was `utils.ssh`; moved under `ssh_utils/`. |
| `stackops.utils.ssh_utils.abc` | `api` | `python-api-candidate` | `medium` | 8 | 6 | - | src/stackops/utils/ssh_utils/abc.py |  |
| `stackops.utils.ssh_utils.wsl` | `api-or-script` | `manual-review` | `medium` | 3 | 173 | __main__, funcs:7 | src/stackops/utils/ssh_utils/wsl.py |  |
| `stackops.utils.ssh_utils.wsl_helper` | `api` | `python-api-candidate` | `medium` | 1 | 218 | funcs:15 | src/stackops/utils/ssh_utils/wsl_helper.py |  |
| `stackops.utils.schemas.yaml_schema` | `api` | `python-api-candidate` | `medium` | 3 | 31 | funcs:3 | src/stackops/utils/schemas/yaml_schema.py | Was `utils.yaml_schema`; moved under `schemas/`. |

## Next Manual Pass

1. Resolve every `api-or-*` row in the manual queue to `api`, `cli-helper`, or `script-asset`.
2. Promote only modules with stable function/class contracts to `api`; keep command glue and interactive workflows as `cli` or `cli-helper`.
3. After the table is corrected, add a source marker such as `__stackops_module_intent__ = "api"` near the top of each non-asset module.
4. Optionally keep this report as the source of truth for asset/config packages where a code marker would add noise.

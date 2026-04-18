# StackOps Source Map

Use this map to jump from a direct CLI command path to the file that registers it and where behavior is implemented.

## Direct App Modules

- `devops ...`
  - Group registration: `src/stackops/scripts/python/devops.py`
  - Nested apps:
    - `repos` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_repos.py`
    - `config` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_config.py`
    - `data` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_data.py`
    - `self` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_self.py`
    - `network` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_nw.py`

- `cloud ...`
  - Group registration: `src/stackops/scripts/python/cloud.py`
  - Helper implementations:
    - `sync` -> `helpers/helpers_cloud/cloud_sync.py`
    - `copy` -> `helpers/helpers_cloud/cloud_copy.py`
    - `mount` -> `helpers/helpers_cloud/cloud_mount.py`
    - `ftpx` -> `src/stackops/scripts/python/ftpx.py` -> `helpers/helpers_network/ftpx_impl.py`

- `terminal ...`
  - Group registration: `src/stackops/scripts/python/terminal.py`
  - `run` -> `src/stackops/scripts/python/helpers/helpers_sessions/sessions_cli_run.py`
  - `run-all` -> `src/stackops/scripts/python/helpers/helpers_sessions/sessions_cli_run_all.py`
  - `run-aoe` -> `src/stackops/scripts/python/helpers/helpers_sessions/sessions_cli_run_aoe.py`
  - Heavy logic in `helpers/helpers_sessions/*`

- `agents ...`
  - Group registration: `src/stackops/scripts/python/agents.py`
  - Heavy logic in `helpers/helpers_agents/*` and `scripts/python/ai/utils/*`

- `utils ...`
  - Group registration: `src/stackops/scripts/python/utils.py`
  - Nested apps:
    - `machine` -> `src/stackops/scripts/python/helpers/helpers_utils/machine_utils_app.py`
    - `pyproject` -> `src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_app.py`
    - `file` -> `src/stackops/scripts/python/helpers/helpers_utils/file_utils_app.py`
  - `utils pyproject type-fix` implementation: `src/stackops/scripts/python/helpers/helpers_utils/type_fix.py`
  - Implementations spread across `helpers/helpers_utils/*`, `stackops/utils/*`, and `stackops/type_hinting/*`

- `fire ...`
  - Registration and CLI surface: `src/stackops/scripts/python/fire_jobs.py`
  - Core helpers: `helpers/helpers_fire_command/fire_jobs_args_helper.py`, `helpers/helpers_fire_command/fire_jobs_impl.py`

- `croshell ...`
  - Registration and CLI surface: `src/stackops/scripts/python/croshell.py`
  - Helper backend routing: `helpers/helpers_croshell/croshell_impl.py`

- `seek ...`
  - Registration and CLI surface: `src/stackops/scripts/python/seek.py`
  - Helper implementation: `src/stackops/scripts/python/helpers/helpers_seek/seek_impl.py`

- `msearch ...`
  - Registration and CLI surface: `src/stackops/scripts/python/msearch.py`
  - Helper implementation: `helpers/helpers_msearch/msearch_impl.py`

## Nested Group Apps

- `devops network ssh ...`
  - Registration: `src/stackops/scripts/python/helpers/helpers_devops/cli_ssh.py`

- `devops self explore ...`
  - Registration: `src/stackops/scripts/python/graph/visualize/cli_graph_app.py`

- `devops self ai ...`
  - Registration: `src/stackops/scripts/python/helpers/helpers_devops/cli_self_ai/app.py`
  - `update-installer` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_self_ai/update_installer.py`
  - `update-test` -> `src/stackops/scripts/python/helpers/helpers_devops/cli_self_ai/update_test.py`

- `devops self security ...`
  - Registration: `src/stackops/jobs/installer/checks/security_cli.py`

## Debugging and Validation Workflow

1. Confirm command registration path in the appropriate `get_app()` file.
2. Trace imported implementation module from the command function body.
3. Validate help surface locally:
   - `UV_CACHE_DIR=/tmp/uv-cache uv run devops --help`
   - `UV_CACHE_DIR=/tmp/uv-cache uv run devops repos --help`
4. If adding/changing command names, update:
   - Typer registration(s)
   - callable signature/help text
   - any wrappers or docs that reference old paths

# Remote Execution and Networking

The remote layer packages a callable or script into job artifacts, writes the shell and Python wrappers needed to execute it elsewhere, transfers those artifacts, launches the job, and syncs status and results back to the local machine.

It also includes lower-level SSH and networking helpers that are reused outside the job runner.

---

## Remote workflow in one view

```mermaid
graph LR
    A[RemoteStackOpsConfig] --> B[RemoteMachine]
    B --> C[JobParams]
    B --> D[FileManager]
    B --> E[render_execution_script]
    B --> F[transfer_sftp / transfer_cloud]
    F --> G[fire()]
    G --> H[check_job_status()]
    H --> I[download_results()]

    J[distribute.Cluster] --> B
```

---

## Core modules

| Module | Responsibility |
| --- | --- |
| `stackops.cluster.remote.models` | Dataclasses and aliases such as `RemoteStackOpsConfig`, `WorkloadParams`, `JobStatus`, and `ExecutionTimings` |
| `stackops.cluster.remote.job_params` | Converts a callable or script path into import and execution metadata |
| `stackops.cluster.remote.file_manager` | Defines the job-root layout, status files, and resource-lock bookkeeping |
| `stackops.cluster.remote.remote_machine` | High-level orchestration for generating, submitting, firing, checking, and downloading jobs |
| `stackops.cluster.remote.data_transfer` | SFTP and cloud-transfer helpers used by `RemoteMachine.submit()` |
| `stackops.cluster.remote.execution_script` | Template renderer for the generated Python wrapper |
| `stackops.cluster.remote.distribute` | Multi-host distribution utilities built around `RemoteMachine` |
| `stackops.utils.ssh` | SSH transport, remote Python execution, remote shell execution, and file copy helpers |
| `stackops.scripts.python.helpers.helpers_network.address` | Public-IP lookup and local IPv4 selection |
| `stackops.scripts.python.helpers.helpers_network.address_switch` | Public-IP rotation flow based on `warp-cli` |

---

## `RemoteStackOpsConfig`

`RemoteStackOpsConfig` is the typed job description consumed by `RemoteMachine`.

### Important fields

| Field | Purpose |
| --- | --- |
| `job_id` | Stable identifier used in job directories and status files |
| `base_dir` | Root directory for generated job artifacts |
| `description` | Free-form description copied into job metadata |
| `ssh_host` | SSH config alias or `user@host[:port]` target |
| `copy_repo`, `update_repo`, `install_repo` | Repo setup policy before the generated Python wrapper runs |
| `data` | Extra files or directories to transfer alongside the job |
| `transfer_method` | `sftp` or `cloud` |
| `cloud_name` | Required when `transfer_method="cloud"` |
| `notify_upon_completion`, `to_email`, `email_config_name` | Email notification controls |
| `launch_method` | `remotely` or `cloud_manager` |
| `interactive` | Runs the generated Python wrapper with `python -i` instead of `python` |
| `wrap_in_try_except` | Wraps the generated execution line in a try/except block |
| `parallelize`, `workload_params` | Split a callable into `ProcessPoolExecutor` work units |
| `lock_resources`, `max_simultaneous_jobs` | File-manager locking policy for the target machine |

Important current validation rules:

- `cloud_name` must be set for cloud transfers
- enabling notifications auto-fills `to_email` and `email_config_name` from defaults when they were not passed explicitly

---

## `JobParams`

`JobParams` is the normalized execution payload used by the generated Python wrapper.

### Source forms

- `JobParams.from_script(path)` for script files
- `JobParams.from_callable(func)` for importable functions and bound methods

Current constraints:

- callables defined in `__main__` are rejected
- `<run_path>` callables are rewritten from their `__file__`
- `get_execution_line()` emits different code for plain calls, workload-aware calls, and `parallelize=True` splits

---

## `RemoteMachine`

`RemoteMachine` accepts one of three inputs:

- a script path
- a function
- a bound method

### Typical usage

```python
from stackops.cluster.remote.models import RemoteStackOpsConfig
from stackops.cluster.remote.remote_machine import RemoteMachine

config = RemoteStackOpsConfig(
    job_id="nightly-train",
    ssh_host="gpu-box",
    base_dir="~/tmp_results/remote_machines/jobs",
    transfer_method="sftp",
    notify_upon_completion=False,
)

job = RemoteMachine(
    func="src/my_project/jobs/train.py",
    config=config,
    func_kwargs={"epochs": 10},
    data=["data/input.csv"],
)

job.run(run=True, show_scripts=False)
```

### Main methods

| Method | Purpose |
| --- | --- |
| `generate_scripts()` | Writes `job_params.json`, the generated Python wrapper, the shell launcher, kwargs JSON, and config JSON |
| `show_scripts()` | Prints the generated shell and Python sources with Rich |
| `submit()` | Transfers the job root with SFTP or prepends cloud-download commands to the shell launcher |
| `fire(run)` | Launches the generated shell script locally or through SSH |
| `run(run, show_scripts)` | Calls generate -> optional show -> submit -> fire |
| `check_job_status()` | Syncs remote logs when needed and resolves the results directory once the job finishes |
| `download_results(target)` | Downloads the resolved results path |
| `delete_remote_results()` | Deletes the remote results directory |
| `submit_to_cloud()` | Expands one cloud-managed job into multiple `RemoteMachine` instances with split workloads |

Current behavior worth knowing:

- the `run` flag accepted by `fire()` and `run()` is currently not used to suppress launch; those methods still fire the job
- direct `RemoteMachine(...)` construction initializes `FileManager` with `remote_machine_type="Linux"`, so the default generated launcher is the Unix shell variant

---

## Generated file layout

`FileManager` gives each job a stable directory shape under `{base_dir}/queued/{job_id}/`:

```text
{base_dir}/queued/{job_id}/
├── data/
│   ├── file_manager.json
│   ├── func_kwargs.json
│   ├── job_params.json
│   ├── remote_machine.json
│   └── remote_machine_config.json
├── python/
│   └── cluster_wrap.py
├── shell/
│   └── cluster_script.sh
└── logs/
    ├── status.txt
    ├── pid.txt
    ├── start_time.txt
    ├── end_time.txt
    ├── error_message.txt
    └── results_folder_path.txt
```

`FileManager` also owns the queue, running, and history JSON files under `~/tmp_results/remote_machines/file_manager/`.

---

## Resource locking and status

When `lock_resources=True`, `FileManager.secure_resources()` uses shared JSON files to enforce `max_simultaneous_jobs`.

The current behavior is:

- waiting jobs are added to `queued_jobs.json`
- active jobs are tracked in `running_jobs.json`
- completed jobs append timing data to `history_jobs.json`
- blocked jobs sleep in 10-minute intervals while waiting for a slot

`get_job_status()` reads `logs/status.txt`, verifies the recorded PID with `psutil`, and marks a supposedly running job as failed if its process is gone or no longer matches the job id.

---

## Cluster distribution

`stackops.cluster.remote.distribute.Cluster` is the multi-host wrapper around `RemoteMachine`.

It:

- opens SSH connections to all requested hosts
- samples remote CPU and RAM
- computes workload splits with `MachineLoadCalculator`
- creates one `RemoteMachine` per host
- submits and fires those remote jobs

This is the path to use when the same callable should be partitioned across several machines instead of sent to just one host.

---

## SSH helper

`stackops.utils.ssh.SSH` is the lower-level transport used by the remote layer.

`SSH.from_config_file(host)` first tries `~/.ssh/config`; if no matching entry exists, it falls back to parsing `user@host[:port]` syntax. The class opens:

- a Paramiko SSH client
- an SFTP channel when possible
- a cached view of local and remote machine specs

Representative operations include:

- `run_shell_cmd_on_remote(...)`
- `run_py_remotely(...)`
- `copy_from_here(...)`
- `copy_to_here(...)`
- `send_ssh_key()`
- `restart_computer()`

---

## Networking helpers

### `helpers_network.address`

- `get_public_ip_address()` installs `ipinfo` if needed, then shells out to `ipinfo myip --json`
- `get_all_ipv4_addresses()` returns `(interface, ip)` tuples for every local IPv4 address
- `select_lan_ipv4(prefer_vpn)` scores active interfaces and prefers physical RFC1918 LAN addresses

### `helpers_network.address_switch`

`switch_public_ip_address(max_trials, wait_seconds, target_ip_addresses)` installs `warp-cli` if needed, deletes the current WARP registration, registers a new one, reconnects, and repeatedly checks the public IP until it changes or matches a requested target list.

---

## See also

- [Sessions](sessions.md) for the backends that host launched work
- [Layouts](layouts.md) for the tab and layout schema used by terminal-oriented flows
- [CLI Terminal Reference](../../cli/terminal.md) for the end-user command layer

---

## API reference

## Remote models

::: stackops.cluster.remote.models
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Job parameters

::: stackops.cluster.remote.job_params
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## File manager

::: stackops.cluster.remote.file_manager
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Remote machine

::: stackops.cluster.remote.remote_machine
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Cluster distributor

::: stackops.cluster.remote.distribute
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## SSH helper

::: stackops.utils.ssh
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Address helpers

::: stackops.scripts.python.helpers.helpers_network.address
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Address switching

::: stackops.scripts.python.helpers.helpers_network.address_switch
    options:
      show_root_heading: true
      show_source: false
      members_order: source

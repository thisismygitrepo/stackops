# Remote Execution and Networking

The remote-execution layer packages a Python function or script, generates the shell and Python artifacts required to run it elsewhere, transfers those artifacts, fires the job on a target machine, and provides helpers for checking status and downloading results.

It also includes lower-level SSH and networking utilities that show up in remote or multi-machine workflows.

---

## Remote workflow in one view

```mermaid
graph LR
    A[RemoteMachineConfig] --> B[RemoteMachine]
    B --> C[JobParams]
    B --> D[FileManager]
    B --> E[generate_scripts()]
    E --> F[submit()]
    F --> G[SSH / transfer]
    G --> H[fire()]
    H --> I[check_job_status()]
    I --> J[download_results()]
```

---

## Core modules

| Module | Responsibility |
| --- | --- |
| `machineconfig.cluster.remote.models` | Dataclasses and typed aliases for job status, workload splits, transfer mode, and remote-machine config |
| `machineconfig.cluster.remote.job_params` | Normalizes a callable or script path into importable execution metadata |
| `machineconfig.cluster.remote.file_manager` | Defines the on-disk job layout, lock files, logs, and helper paths |
| `machineconfig.cluster.remote.remote_machine` | High-level orchestration object for generating, submitting, firing, and collecting jobs |
| `machineconfig.utils.ssh` | SSH transport, remote command execution, SFTP, and remote machine inspection |
| `machineconfig.scripts.python.helpers.helpers_network.address` | Public IP lookup, local IPv4 enumeration, best-LAN-address selection |
| `machineconfig.scripts.python.helpers.helpers_network.address_switch` | Public IP rotation flow built around `warp-cli` |

---

## `RemoteMachineConfig`

`RemoteMachineConfig` is the central description of how a job should run.

### Important fields

| Field | Purpose |
| --- | --- |
| `job_id` | Stable identifier for the job folder and log files |
| `base_dir` | Root directory for generated job artifacts |
| `ssh_host` | SSH config alias or hostname for the target machine |
| `transfer_method` | `sftp` or `cloud` |
| `cloud_name` | Required when `transfer_method="cloud"` |
| `copy_repo`, `update_repo`, `install_repo` | Control repo setup on the target |
| `notify_upon_completion`, `to_email`, `email_config_name` | Completion-notification settings |
| `parallelize` and `workload_params` | Split callable execution into multiple worker chunks |
| `lock_resources`, `max_simultaneous_jobs` | Concurrency control for the target machine |

`WorkloadParams` complements this by describing how a large workload should be sliced into job ranges.

---

## `RemoteMachine`

`RemoteMachine` accepts either:

- a script path
- an importable callable
- a bound method

and turns that into a runnable remote job.

### Typical usage

```python
from machineconfig.cluster.remote.models import RemoteMachineConfig
from machineconfig.cluster.remote.remote_machine import RemoteMachine

config = RemoteMachineConfig(
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
| `generate_scripts()` | Write the job's shell script, Python wrapper, kwargs JSON, and metadata JSON |
| `show_scripts()` | Display the generated shell and Python source |
| `submit()` | Transfer artifacts to the target using the configured transfer method |
| `fire(run)` | Launch the generated command locally or remotely |
| `run(run, show_scripts)` | End-to-end wrapper over generate -> submit -> fire |
| `check_job_status()` | Sync logs back, inspect status markers, and discover the results folder |
| `download_results(target)` | Retrieve results once the job is complete |
| `delete_remote_results()` | Remove remote output after collection |

!!! note
    If you pass a callable, it must come from an importable module. The current `JobParams.from_callable()` rejects functions defined as `__main__`.

---

## File layout and locking

`FileManager` gives the remote-job system a stable directory shape. A generated job typically looks like this:

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
    ├── start_time.txt
    ├── end_time.txt
    └── results_folder_path.txt
```

It also manages:

- queue and running-job tracking JSON files
- resource locking for machines with limited concurrency
- history files for completed jobs

---

## SSH helper

`machineconfig.utils.ssh.SSH` is the lower-level transport used by remote jobs and other operational flows.

It can:

- resolve hosts through `~/.ssh/config`
- open an SSH connection with Paramiko
- open an SFTP channel when available
- run remote commands
- display local and remote machine specs side-by-side

A common entrypoint is:

```python
from machineconfig.utils.ssh import SSH

ssh = SSH.from_config_file(host="gpu-box")
```

---

## Networking helper entrypoints

Some remote workflows need address discovery rather than full job submission.

### `helpers_network.address`

Useful functions include:

- `get_public_ip_address()`
- `get_all_ipv4_addresses()`
- `select_lan_ipv4(prefer_vpn)`

### `helpers_network.address_switch`

`switch_public_ip_address(max_trials, wait_seconds, target_ip_addresses)` automates a public-IP rotation flow using `warp-cli` and repeated `ipinfo` checks.

These modules live under `scripts/python/helpers` because they are also exposed through CLI flows, but they are still useful as library entrypoints.

---

## See also

- [Sessions](sessions.md) for the backend managers that actually host launched jobs
- [Layouts](layouts.md) for the typed tab and layout schema used by session-oriented flows
- [CLI Sessions Reference](../../cli/sessions.md) for the user-facing command layer

---

## API reference

## Remote models

::: machineconfig.cluster.remote.models
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Job parameters

::: machineconfig.cluster.remote.job_params
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## File manager

::: machineconfig.cluster.remote.file_manager
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Remote machine

::: machineconfig.cluster.remote.remote_machine
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## SSH helper

::: machineconfig.utils.ssh
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Address helpers

::: machineconfig.scripts.python.helpers.helpers_network.address
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Address switching

::: machineconfig.scripts.python.helpers.helpers_network.address_switch
    options:
      show_root_heading: true
      show_source: false
      members_order: source

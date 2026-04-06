# Sessions

The session-manager layer takes a `LayoutConfig` and turns it into running terminal sessions. Different backends implement the same general workflow with platform-specific mechanics.

This part of the API is where `machineconfig` becomes a terminal-orchestration tool.

---

## Supported backends

| Manager | Module path | Platform | Notes |
| --- | --- | --- | --- |
| `ZellijLocalManager` | `machineconfig.cluster.sessions_managers.zellij.zellij_local_manager` | Linux/macOS | Starts local zellij sessions, polls for appearance, and monitors tabs |
| `ZellijRemoteManager` | `machineconfig.cluster.sessions_managers.zellij.zellij_remote_manager` | Linux/macOS + remote | Remote zellij-oriented orchestration |
| `TmuxLocalManager` | `machineconfig.cluster.sessions_managers.tmux.tmux_local_manager` | Any tmux-capable host | Local tmux sessions and status reporting |
| `WTLocalManager` | `machineconfig.cluster.sessions_managers.windows_terminal.wt_local_manager` | Windows | Local Windows Terminal orchestration |
| `WTRemoteManager` | `machineconfig.cluster.sessions_managers.windows_terminal.wt_remote_manager` | Windows + remote | Remote Windows Terminal workflows |

---

## Common lifecycle

Most manager classes follow the same shape:

1. Accept one or more `LayoutConfig` objects.
2. Build backend-specific layout or script files.
3. Resolve session-name conflicts.
4. Start sessions.
5. Attach, inspect, monitor, or stop sessions later.

That shared lifecycle is why the same layout builder APIs can feed different session backends.

---

## Session conflict policies

`machineconfig.cluster.sessions_managers.session_conflict` defines the conflict strategy used by zellij and tmux flows.

### Available policies

| Policy | Meaning |
| --- | --- |
| `error` | Fail immediately if a requested session name already exists or duplicates another requested name |
| `restart` | Reuse the original name and restart the existing session |
| `rename` | Keep the original request but create a suffixed session name such as `name_1` |

This is especially helpful when generated layouts are launched repeatedly from automation code.

---

## Backend-specific behavior

### Zellij

`ZellijLocalManager`:

- prefixes session names with `LocalJobMgr`
- starts sessions non-blockingly
- polls `zellij list-sessions` to verify that sessions appeared
- provides session and command summaries over time

Its start method currently expects:

```python
results = manager.start_all_sessions(
    on_conflict="rename",
    poll_seconds=10,
    poll_interval=0.5,
)
```

### tmux

`TmuxLocalManager` is a good fit when you want explicit shell-script generation and simple attach/status flows:

```python
from machineconfig.cluster.sessions_managers.tmux.tmux_local_manager import TmuxLocalManager

manager = TmuxLocalManager(
    session_layouts=[layout],
    session_name_prefix="ops",
)

manager.start_all_sessions(on_conflict="rename")
print(manager.attach_to_session(None))
report = manager.check_all_sessions_status()
```

### Windows Terminal

`WTLocalManager` manages a collection of Windows Terminal sessions and supports:

- generated PowerShell launch scripts
- status inspection
- attach commands such as `wt -w <session_name>`
- monitoring and persistence helpers under `wt_utils`

Unlike the tmux and zellij managers, `WTLocalManager.start_all_sessions()` currently does not take an `on_conflict` policy directly.

---

## Monitoring and reporting helpers

Under the backend-specific utility packages you will find:

- process monitors
- session health checks
- reporting helpers
- persistence helpers for saved Windows Terminal session state

Representative modules include:

- `machineconfig.cluster.sessions_managers.zellij.zellij_utils.process_monitor`
- `machineconfig.cluster.sessions_managers.zellij.zellij_utils.status_reporter`
- `machineconfig.cluster.sessions_managers.windows_terminal.wt_utils.status_reporting`
- `machineconfig.cluster.sessions_managers.windows_terminal.wt_utils.manager_persistence`

---

## See also

- [Layouts](layouts.md) for `LayoutConfig`, layout serialization, and tab generation
- [Remote execution and networking](remote.md) for remote-job flows that hand work off to these session backends
- [CLI Terminal Reference](../../cli/terminal.md) for the user-facing command layer

---

## Conflict-planning reference

::: machineconfig.cluster.sessions_managers.session_conflict
    options:
      show_root_heading: true
      show_source: false
      members_order: source
